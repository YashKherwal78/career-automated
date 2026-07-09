from src.system.logger import setup_logger
logger = setup_logger('rag')
import os
from src.config.config import Config
from rank_bm25 import BM25Okapi

class RAGClient:
    def __init__(self):
        self.chunks = []
        self.tokenized_corpus = []
        self.bm25 = None
        
        self._load_and_chunk_from_master()
        
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
        # Simple whitespace tokenization + lowercasing
        self.tokenized_corpus.append(text.lower().split())

    def retrieve(self, query: str, top_k_initial: int = 5, top_k_final: int = 3) -> list[dict]:
        """
        Retrieves Top 5 chunks using BM25, then reranks, returning the Final Top chunks.
        Now includes chunk_type metadata.
        """
        if not self.bm25 or not self.chunks:
            return []
            
        query_tokens = query.lower().split()
        
        # 1. BM25 Retrieval (Top K)
        scores = self.bm25.get_scores(query_tokens)
        
        # Zip chunks with their indices and scores
        scored_chunks = list(enumerate(scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        top_initial = scored_chunks[:top_k_initial]
        
        # 2. Simple Keyword Reranker (boosts based on basic token presence)
        reranked = []
        for idx, base_score in top_initial:
            chunk_data = self.chunks[idx]
            chunk_text_lower = chunk_data["text"].lower()
            tag_boost = 0
            for token in query_tokens:
                clean_token = token.strip("?,.!\"'")
                if len(clean_token) > 3 and clean_token in chunk_text_lower:
                    tag_boost += 1.0
                    
            final_score = base_score + tag_boost
            reranked.append({
                "score": final_score, 
                "text": chunk_data["text"],
                "type": chunk_data["type"]
            })
            
        # Sort by final reranked score
        reranked.sort(key=lambda x: x["score"], reverse=True)
        
        # 3. Return Final Top K
        return reranked[:top_k_final]
