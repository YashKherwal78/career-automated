import re
from typing import List, Dict, Any


def estimate_tokens(text: str) -> int:
    """Rough estimation of token count based on standard English word-to-token ratio (1.3 tokens/word)."""
    if not text:
        return 0
    words = len(text.split())
    return max(1, int(words * 1.3))


class Chunker:
    @staticmethod
    def chunk_plain_text(text: str, chunk_size: int = 600, overlap: int = 75) -> List[Dict[str, Any]]:
        """Split plain text into chunks based on paragraph breaks and token limits, with overlapping boundaries."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_idx = 0

        for para in paragraphs:
            para_tokens = estimate_tokens(para)
            if para_tokens > chunk_size:
                # If a single paragraph exceeds the chunk size, we must split it by sentences or lines
                if current_chunk:
                    chunks.append({
                        "content": "\n\n".join(current_chunk),
                        "chunk_index": chunk_idx,
                        "metadata": {"token_count": current_tokens}
                    })
                    chunk_idx += 1
                    current_chunk = []
                    current_tokens = 0
                
                # Split large paragraph by sentence boundaries
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sub_chunk = []
                sub_tokens = 0
                for sent in sentences:
                    sent_tokens = estimate_tokens(sent)
                    if sub_tokens + sent_tokens > chunk_size:
                        if sub_chunk:
                            chunks.append({
                                "content": " ".join(sub_chunk),
                                "chunk_index": chunk_idx,
                                "metadata": {"token_count": sub_tokens}
                            })
                            chunk_idx += 1
                        # Apply overlap by keeping last sentence(s) if possible
                        sub_chunk = [sent]
                        sub_tokens = sent_tokens
                    else:
                        sub_chunk.append(sent)
                        sub_tokens += sent_tokens
                if sub_chunk:
                    chunks.append({
                        "content": " ".join(sub_chunk),
                        "chunk_index": chunk_idx,
                        "metadata": {"token_count": sub_tokens}
                    })
                    chunk_idx += 1
            else:
                if current_tokens + para_tokens > chunk_size:
                    chunks.append({
                        "content": "\n\n".join(current_chunk),
                        "chunk_index": chunk_idx,
                        "metadata": {"token_count": current_tokens}
                    })
                    chunk_idx += 1
                    
                    # Support overlap by keeping the last paragraph if it fits within the overlap size
                    overlap_tokens = 0
                    overlap_chunk = []
                    for prev_para in reversed(current_chunk):
                        prev_tokens = estimate_tokens(prev_para)
                        if overlap_tokens + prev_tokens <= overlap:
                            overlap_chunk.insert(0, prev_para)
                            overlap_tokens += prev_tokens
                        else:
                            break
                    current_chunk = overlap_chunk
                    current_tokens = overlap_tokens

                current_chunk.append(para)
                current_tokens += para_tokens

        if current_chunk:
            chunks.append({
                "content": "\n\n".join(current_chunk),
                "chunk_index": chunk_idx,
                "metadata": {"token_count": current_tokens}
            })

        return chunks

    @staticmethod
    def chunk_markdown(text: str, chunk_size: int = 600, overlap: int = 75) -> List[Dict[str, Any]]:
        """Split markdown content by heading boundaries (#, ##, ###), fall back to plain text splits for large segments."""
        # Find headings or sections
        lines = text.split("\n")
        sections = []
        current_section = []
        current_header = "Intro"
        
        for line in lines:
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if header_match:
                if current_section:
                    sections.append((current_header, "\n".join(current_section)))
                    current_section = []
                current_header = header_match.group(2).strip()
            current_section.append(line)
        if current_section:
            sections.append((current_header, "\n".join(current_section)))

        chunks = []
        chunk_idx = 0
        for header, content in sections:
            sect_tokens = estimate_tokens(content)
            if sect_tokens <= chunk_size:
                chunks.append({
                    "content": content,
                    "chunk_index": chunk_idx,
                    "metadata": {"heading": header, "token_count": sect_tokens}
                })
                chunk_idx += 1
            else:
                # Sub-split large heading block
                sub_splits = Chunker.chunk_plain_text(content, chunk_size=chunk_size, overlap=overlap)
                for split in sub_splits:
                    split["chunk_index"] = chunk_idx
                    split["metadata"]["heading"] = header
                    chunks.append(split)
                    chunk_idx += 1
        return chunks


def chunk_document(text: str, strategy: str = "plain_text", chunk_size: int = 600, overlap: int = 75) -> List[Dict[str, Any]]:
    strategy = strategy.lower()
    if strategy == "markdown":
        return Chunker.chunk_markdown(text, chunk_size, overlap)
    else:
        return Chunker.chunk_plain_text(text, chunk_size, overlap)
