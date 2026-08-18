from src.system.logger import setup_logger
logger = setup_logger('rag')
import os
import re
from src.config.config import Config
from rank_bm25 import BM25Okapi

# Reuses the same local ONNX embedding model already running in production
# for job/candidate vector matching (src/discovery/embeddings.py) instead of
# pulling in a second model -- one less thing to load, and it means profile
# chunks and job/candidate embeddings live in a comparable space if this
# ever needs to be compared against those (it doesn't today, but no reason
# to fragment on embedding choice for no benefit).
from src.discovery.embeddings import embed_batch, embed_text

# Terms worth treating as graph nodes: multi-word or distinctive enough that
# a plain BM25/embedding match can miss them buried in a long chunk, but
# common enough across the master profile's "Stack:" / "Skills Emphasis:" /
# "Best Roles:" / "Best Companies:" lines that linking chunks who share one
# recovers real multi-hop connections (e.g. a "Docker" question should pull
# every project chunk that lists Docker in its stack, not just whichever one
# BM25 happens to rank first).
_ENTITY_LINE_PREFIXES = (
    "Stack:", "Skills Emphasis:", "Best Roles:", "Best Companies:",
    "Strongest Technical Skills", "Strongest Product Skills",
)


# Stripped from BM25 tokens (both corpus and query) -- without this, a
# question phrased as "What did you build at OrangeLabs?" scores chunks
# that happen to repeat "what"/"did"/"you"/"at" higher than the chunk
# containing the one actually distinctive, correct token ("orangelabs"),
# because BM25 has no built-in notion that those words carry no signal.
# Confirmed via scripts/rag_eval.py: this was silently sending the
# OrangeLabs question's top match to an unrelated chunk before this fix.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "what", "when", "where", "who", "whom", "why", "how", "which",
    "did", "do", "does", "doing", "you", "your", "yours", "i", "me", "my",
    "at", "on", "in", "to", "of", "for", "with", "and", "or", "but", "so",
    "this", "that", "these", "those", "it", "its", "as", "if", "than",
    "have", "has", "had", "can", "could", "would", "should", "will",
}


def _tokenize(text: str) -> list[str]:
    """Word-boundary tokenization instead of a naive .split() -- a naive
    split leaves punctuation glued to the last word of a sentence, so a
    question ending "...at OrangeLabs?" tokenizes to "orangelabs?" which
    never matches the corpus's clean "orangelabs" token. Also drops common
    stopwords (see _STOPWORDS) so they don't dilute BM25's score with noise."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS]


def _cosine(a, b) -> float:
    import numpy as np
    va, vb = np.array(a), np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


class RAGClient:
    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.chunks = []
        self.tokenized_corpus = []
        self.bm25 = None
        self.chunk_embeddings = []
        # entity (lowercase) -> set of chunk indices that mention it.
        # Built once from the same source markdown as the chunks -- this is
        # a real, source-grounded graph, not an LLM-hallucinated one, since
        # every edge is a literal substring match against text that also
        # backs a retrievable chunk. See _build_entity_graph.
        self.entity_to_chunks: dict[str, set[int]] = {}
        self._explicit_entities: set[str] = None

        if user_id:
            # Every real call site used to construct RAGClient() with no
            # user context at all -- meaning question_engine.py answered
            # every applicant's essay questions (e.g. "tell me about a
            # challenging project") from the product owner's own hardcoded
            # yash_master_profile.md, submitted as first-person narrative
            # under whichever user's name was actually applying. Same class
            # of bug as ProfileManager's hardcoded identity, but for
            # narrative content instead of contact fields -- and arguably
            # worse, since it's fabricated first-person claims sent to a
            # real employer under the wrong person's name.
            self._load_and_chunk_from_profile_data(user_id)
            self._build_entity_graph_from_skills()
        else:
            # Legacy path -- unchanged, still backs any call site not yet
            # passing a user_id (there shouldn't be any live ones left; see
            # the factory function get_rag_client() below for the
            # cached/per-user entry point every real call site now uses).
            self._load_and_chunk_from_master()
            self._build_entity_graph()

        self._embed_chunks()

    def _load_and_chunk_from_profile_data(self, user_id: str):
        """Builds the retrievable corpus from the real, current
        user_career_profiles.profile_data for this specific user -- same
        source and extraction shape src/referrals/hr_referral_pitch.py's
        _load_profile_facts already reads for outreach emails, so a
        candidate's real achievements ground both systems consistently."""
        try:
            from src.api.db import get_connection
            import json as _json
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT profile_data FROM public.user_career_profiles WHERE user_id = %s LIMIT 1",
                    (user_id,),
                )
                row = cursor.fetchone()
            if not row:
                logger.info(f"RAGClient: no profile_data for user_id={user_id} -- empty corpus.")
                return
            profile_data = row["profile_data"] if hasattr(row, "keys") else row[0]
            if not profile_data:
                return
            profile = _json.loads(profile_data) if isinstance(profile_data, str) else profile_data
        except Exception as e:
            logger.warning(f"RAGClient: profile_data load failed for user_id={user_id}: {e}")
            return

        self._profile = profile

        for exp in (profile.get("experience") or []):
            role = exp.get("role") or exp.get("title") or ""
            company = exp.get("company") or ""
            header = f"### Experience: {role} at {company}".strip()
            bullets = [b for b in (exp.get("bullet_points") or []) if b]
            bullets += [a for a in (exp.get("achievements") or []) if a]
            if bullets:
                self._add_chunk("internship", header + "\n" + "\n".join(f"- {b}" for b in bullets))

        for proj in (profile.get("projects") or []):
            name = proj.get("name") or ""
            header = f"### Project: {name}".strip()
            body_parts = []
            if proj.get("description"):
                body_parts.append(proj["description"])
            body_parts += [b for b in (proj.get("bullet_points") or []) if b]
            skills_used = proj.get("skills_demonstrated") or []
            if skills_used:
                body_parts.append("Stack: " + ", ".join(skills_used))
            if body_parts:
                self._add_chunk("project", header + "\n" + "\n".join(f"- {b}" for b in body_parts))

        summary = profile.get("summary")
        if summary:
            self._add_chunk("skill", "### Summary\n" + summary)

        skills = profile.get("skills") or {}
        skill_lines = [
            f"{cat.replace('_', ' ').title()}: " + ", ".join(items)
            for cat, items in skills.items()
            if isinstance(items, list) and items
        ]
        if skill_lines:
            self._add_chunk("skill", "### Skills\n" + "\n".join(skill_lines))

        achievements = [a for a in (profile.get("achievements") or []) if isinstance(a, str) and a]
        if achievements:
            self._add_chunk("behavioral", "### Achievements\n" + "\n".join(f"- {a}" for a in achievements))

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            logger.info(f"RAGClient: Initialised with {len(self.chunks)} chunks from real profile_data (user_id={user_id}).")

    def _build_entity_graph_from_skills(self):
        """Same purpose as _build_entity_graph (multi-hop recall: a query
        mentioning one skill surfaces every chunk that mentions it, not just
        whichever chunk BM25/embedding ranked highest alone) -- but sourced
        from profile_data.skills' clean, structured lists instead of regex
        over markdown formatting conventions that only exist in the one
        static file. Structured source, so this is if anything more
        reliable than the markdown-regex version, not a reduced substitute."""
        profile = getattr(self, "_profile", None)
        if not profile or not self.chunks:
            return
        skills = profile.get("skills") or {}
        entities: set[str] = set()
        for items in skills.values():
            if isinstance(items, list):
                for term in items:
                    if isinstance(term, str) and 2 <= len(term) <= 40:
                        entities.add(term)

        for entity in entities:
            entity_lower = entity.lower()
            if len(entity_lower) < 3:
                continue
            matches = {
                idx for idx, chunk in enumerate(self.chunks)
                if entity_lower in chunk["text"].lower()
            }
            if matches:
                self.entity_to_chunks[entity_lower] = matches

        logger.info(f"RAGClient: Built entity graph with {len(self.entity_to_chunks)} linked terms (from profile_data.skills).")

    def _extract_between(self, text, start, end):
        try:
            return text.split(start)[1].split(end)[0]
        except Exception:
            return ""

    def _load_and_chunk_from_master(self):
        """Dynamically generates chunks from yash_master_profile.md."""
        master_path = str(Config.DATA_DIR / "context" / "yash_master_profile.md")
        if not os.path.exists(master_path):
            logger.info(f"RAGClient Warning: {master_path} not found.")
            return

        with open(master_path, "r", encoding="utf-8") as f:
            content = f.read()
        self._raw_content = content

        # 1. Internships
        exp_section = self._extract_between(content, "## SECTION 3: EXPERIENCE INTELLIGENCE", "## SECTION 4")
        if exp_section:
            for exp in exp_section.split("### Experience ")[1:]:
                text = "### Experience " + exp.strip().split("---")[0].strip()
                self._add_chunk("internship", text)

        # 2. Projects
        proj_section = self._extract_between(content, "## SECTION 4: PROJECT INTELLIGENCE", "## SECTION 5")
        if proj_section:
            for proj in proj_section.split("### Project ")[1:]:
                text = "### Project " + proj.strip().split("---")[0].strip()
                self._add_chunk("project", text)

        # 3. Skills & Behavioral from Profile
        skills_section = self._extract_between(content, "## SECTION 5: PERSONAL PROFILE", "## SECTION 6")
        if skills_section:
            for block in skills_section.split("### ")[1:]:
                clean_block = block.strip().split("---")[0].strip()
                if "Strengths" in clean_block or "Skills" in clean_block:
                    self._add_chunk("skill", "### " + clean_block)
                if "Ownership" in clean_block or "Working Style" in clean_block:
                    self._add_chunk("behavioral", "### " + clean_block)

        # 4. Behavioral Stories from Interview Intel
        interview_section = self._extract_between(content, "## SECTION 8: INTERVIEW INTELLIGENCE", "## SECTION 9")
        if interview_section:
            for story in interview_section.split("**On ")[1:]:
                clean_story = story.strip().split("---")[0].strip()
                self._add_chunk("behavioral", "**On " + clean_story)

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            logger.info(f"RAGClient: Initialised with {len(self.chunks)} chunks from Master Profile.")

    def _add_chunk(self, chunk_type: str, text: str):
        self.chunks.append({
            "type": chunk_type,
            "text": text
        })
        self.tokenized_corpus.append(_tokenize(text))

    def _build_entity_graph(self):
        """Links chunks that share a named skill/technology/company, so a
        query mentioning one surfaces every chunk that mentions it -- not
        just whichever single chunk BM25/embedding similarity ranked
        highest. Entities are extracted deterministically from the same
        "Stack:" / "Skills Emphasis:" / etc. lines already present in the
        source markdown, so every graph edge traces back to literal text
        (no LLM extraction step, no hallucination risk in the graph itself)."""
        if not getattr(self, "_raw_content", None):
            return

        entities: set[str] = set()
        for line in self._raw_content.splitlines():
            stripped = line.strip().lstrip("*").rstrip("*").strip()
            # Markdown-bolds these lines ("**Stack:** ...") -- match against
            # the de-bolded text so the prefix check actually fires.
            plain = re.sub(r"\*\*", "", line.strip())
            if any(plain.startswith(p) for p in _ENTITY_LINE_PREFIXES):
                # "Stack: React Native, LLM APIs (Gemini Flash), FastAPI"
                after_colon = plain.split(":", 1)[1] if ":" in plain else plain
                for term in re.split(r",|\band\b", after_colon):
                    term = re.sub(r"\(.*?\)", "", term).strip(" .*-")
                    if 2 <= len(term) <= 40:
                        entities.add(term)
            elif stripped.startswith(("- **", "1. **", "2. **", "3. **", "4. **", "5. **", "6. **")):
                # Bulleted skill lines like "- LangGraph-based multi-agent system design"
                bolded = re.findall(r"\*\*(.+?)\*\*", stripped)
                for term in bolded:
                    if 2 <= len(term) <= 40:
                        entities.add(term.strip(" .*-"))

        for entity in entities:
            entity_lower = entity.lower()
            if len(entity_lower) < 3:
                continue
            matches = {
                idx for idx, chunk in enumerate(self.chunks)
                if entity_lower in chunk["text"].lower()
            }
            if len(matches) >= 1:
                self.entity_to_chunks[entity_lower] = matches

        logger.info(f"RAGClient: Built entity graph with {len(self.entity_to_chunks)} linked terms.")

    def _embed_chunks(self):
        """Computes an embedding per chunk once at init (cheap: local ONNX
        model, ~50 short chunks, one batch call) so retrieve() can do
        semantic similarity on top of BM25 instead of keyword-match alone --
        the same "hybrid dense+sparse" approach this candidate's own project
        writeups (Semantic Document Search, CareerAutomated) describe, which
        the original implementation didn't actually do despite claiming to."""
        if not self.chunks:
            return
        try:
            texts = [c["text"] for c in self.chunks]
            self.chunk_embeddings = embed_batch(texts)
        except Exception as e:
            logger.info(f"RAGClient: embedding chunks failed ({e}); falling back to BM25-only retrieval.")
            self.chunk_embeddings = []

    def find_unknown_entities(self, query: str) -> list[str]:
        """Named tech/tool-looking terms in the query that never appear
        anywhere in the source profile -- a literal-substring "confirmed
        gap" signal, distinct from low retrieval confidence. This matters
        because embedding similarity can score an unrelated chunk highly
        just off generic phrase overlap (e.g. a question about "Kubernetes"
        still surfacing a "production"/"deployment" chunk with decent
        cosine similarity, even though the term never appears anywhere in
        the profile) -- confidence alone won't reliably catch that, but a
        literal absence check will. Callers should treat a hit here as
        grounds for a direct, deterministic "no experience with X" answer
        rather than either a REVIEW_REQUIRED or an LLM call that might
        fabricate one."""
        if not getattr(self, "_raw_content", None):
            return []
        candidates = re.findall(r"\b[A-Z][A-Za-z0-9+.#]{2,}\b", query)
        stop = {
            "I", "The", "My", "This", "It", "In", "At", "A", "An", "Yes", "No",
            "Have", "You", "What", "Do", "Does", "Why", "How", "Are", "Is", "Can",
            "Please", "Describe", "Tell", "Explain",
        }
        content_lower = self._raw_content.lower()
        return [t for t in dict.fromkeys(candidates) if t not in stop and t.lower() not in content_lower]

    def _graph_linked_indices(self, query: str) -> set[int]:
        query_lower = query.lower()
        linked: set[int] = set()
        for entity, chunk_idxs in self.entity_to_chunks.items():
            if entity in query_lower:
                linked |= chunk_idxs
        return linked

    # Standard default per the Reciprocal Rank Fusion literature (Cormack
    # et al. 2009; the value pgvector/hybrid-search production guides also
    # converge on) -- large enough that rank 1 vs rank 2 in one retriever
    # doesn't swing the fused score wildly, small enough that top ranks
    # still dominate. Not re-derived here since 60 is the well-established
    # default, not a free parameter worth hand-tuning on a 20-chunk corpus.
    _RRF_K = 60

    def retrieve(self, query: str, top_k_initial: int = 8, top_k_final: int = 3) -> list[dict]:
        """
        Hybrid retrieval via Reciprocal Rank Fusion (RRF) over two ranked
        lists -- BM25 (sparse/keyword) and embedding cosine similarity
        (dense/semantic) -- rather than a hand-tuned weighted sum of raw
        scores. RRF fuses by *rank*, not raw score, which sidesteps the
        scale-mismatch problem that caused a real bug here before (BM25's
        raw score is unbounded and corpus-size-dependent; cosine similarity
        is bounded [-1,1] -- averaging them directly over- or under-weights
        one arbitrarily depending on corpus size). This is the standard
        approach in production hybrid-search systems (see e.g. Elasticsearch
        and pgvector hybrid-search reference implementations), not a
        custom scheme invented for this corpus.

        Graph-linked chunks (see _build_entity_graph) are unioned into the
        candidate pool AND treated as a third ranked list (all tied at rank
        1) so an entity match can surface a chunk that neither BM25 nor the
        embedding ranked highly alone -- multi-hop recall without a heavier
        graph-RAG stack, which public guidance on this (see research notes
        in the commit this landed in) says isn't justified at this corpus
        size (~20 chunks, one source document) regardless.

        Each returned item includes "confidence" -- the fused RRF score,
        which callers should use directly for a low-confidence gate rather
        than either underlying signal alone.
        """
        if not self.chunks:
            return []

        query_tokens = _tokenize(query)

        bm25_scores = self.bm25.get_scores(query_tokens) if self.bm25 else [0.0] * len(self.chunks)

        query_embedding = None
        if self.chunk_embeddings:
            try:
                query_embedding = embed_text(query)
            except Exception as e:
                logger.info(f"RAGClient: query embedding failed ({e}); continuing BM25-only for this query.")

        graph_linked = self._graph_linked_indices(query)

        # Rank lists: BM25 over every chunk with nonzero score (a chunk
        # sharing zero tokens with the query shouldn't get RRF credit just
        # for existing); embeddings over every chunk if available.
        bm25_rank_list = [i for i in sorted(range(len(self.chunks)), key=lambda i: bm25_scores[i], reverse=True) if bm25_scores[i] > 0]
        bm25_rank_of = {idx: r for r, idx in enumerate(bm25_rank_list)}

        embed_rank_of: dict[int, int] = {}
        if query_embedding is not None and self.chunk_embeddings:
            sims = [(_cosine(query_embedding, vec), idx) for idx, vec in enumerate(self.chunk_embeddings)]
            sims.sort(key=lambda x: x[0], reverse=True)
            embed_rank_of = {idx: r for r, (_, idx) in enumerate(sims)}

        candidate_idxs = set(bm25_rank_list[:top_k_initial]) | set(embed_rank_of.keys() and list(embed_rank_of.keys())[:top_k_initial]) | graph_linked

        scored = []
        for idx in candidate_idxs:
            chunk_data = self.chunks[idx]
            rrf = 0.0
            if idx in bm25_rank_of:
                rrf += 1.0 / (self._RRF_K + bm25_rank_of[idx] + 1)
            if idx in embed_rank_of:
                rrf += 1.0 / (self._RRF_K + embed_rank_of[idx] + 1)
            if idx in graph_linked:
                rrf += 1.0 / (self._RRF_K + 1)  # treated as rank-1 in the graph "retriever"

            scored.append({
                "score": rrf,
                "confidence": rrf,
                "text": chunk_data["text"],
                "type": chunk_data["type"],
            })

        scored.sort(key=lambda x: x["confidence"], reverse=True)
        return scored[:top_k_final]


# ---------------------------------------------------------------------------
# Cached factory -- every real call site used to write `RAGClient()` fresh,
# which re-reads the source, re-chunks it, and (the expensive part) re-runs
# the local ONNX embedding model over every chunk, on every single call.
# Confirmed real waste, not hypothetical: a batch-apply run over N jobs
# constructs one RAGClient per job for question-answering, so a 20-job batch
# re-embedded the same ~10-30 chunks 20 times over for no reason -- the
# candidate's profile doesn't change mid-batch. Callers should use
# get_rag_client(user_id) instead of constructing RAGClient directly.
# ---------------------------------------------------------------------------
import time as _time
import threading as _threading

_RAG_CACHE: dict = {}
_RAG_CACHE_LOCK = _threading.Lock()
_RAG_CACHE_TTL_SECONDS = 600  # long enough to cover one batch-apply run's
# duration (jobs are dispatched with an 8s delay_seconds between each, per
# batch_apply.py -- a 20-job batch takes ~3min, well under this), short
# enough that a profile edited mid-session is picked up on the next request
# after it, not stale for the rest of the day.
_RAG_CACHE_MAX_ENTRIES = 200  # simple cap against unbounded growth; evicts
# the oldest entry rather than tracking real LRU order, since a client that
# just expired naturally is the common case anyway, not an edge case worth
# a heavier data structure for.


def get_rag_client(user_id: str = None) -> "RAGClient":
    """Cached, per-user RAGClient. Pass user_id for every real request --
    None only exists for the legacy static-file path (see RAGClient.__init__),
    which no live call site should still be using."""
    key = user_id or "__legacy__"
    now = _time.time()
    with _RAG_CACHE_LOCK:
        cached = _RAG_CACHE.get(key)
        if cached and (now - cached[0]) < _RAG_CACHE_TTL_SECONDS:
            return cached[1]

    client = RAGClient(user_id=user_id)

    with _RAG_CACHE_LOCK:
        if len(_RAG_CACHE) >= _RAG_CACHE_MAX_ENTRIES and key not in _RAG_CACHE:
            oldest_key = min(_RAG_CACHE, key=lambda k: _RAG_CACHE[k][0])
            _RAG_CACHE.pop(oldest_key, None)
        _RAG_CACHE[key] = (now, client)

    return client
