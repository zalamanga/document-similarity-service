import re
from typing import List
import difflib

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def chunk_by_period(text: str, min_length: int = 20) -> List[str]:
    if not text:
        return []
    sentences = re.split(r"(?<=[.])\s+", text)
    chunks: List[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) >= min_length:
            if not sentence.endswith("."):
                sentence += "."
            chunks.append(sentence)
    return chunks

def similarity_ratio(text_a: str, text_b: str) -> float:
    if not text_a or not text_b:
        return 0.0
    norm_a = normalize_text(text_a)
    norm_b = normalize_text(text_b)
    if not norm_a or not norm_b:
        return 0.0
    matcher = difflib.SequenceMatcher(None, norm_a, norm_b)
    return matcher.ratio()
