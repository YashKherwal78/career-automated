import re
import unicodedata

def preprocess_jd(text: str) -> str:
    """Preprocesses a job description text, normalizing formatting while preserving structure."""
    if not text:
        return ""
    
    # Convert HTML line break tags to actual newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?(p|div|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Normalize Unicode formatting
    text = unicodedata.normalize('NFKC', text)
    
    # Replace non-breaking spaces or tabs with regular spaces
    text = text.replace('\xa0', ' ').replace('\t', ' ')
    
    # Reduce multiple spaces but keep single spaces
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Normalize empty lines (max 2 consecutive newlines)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()
