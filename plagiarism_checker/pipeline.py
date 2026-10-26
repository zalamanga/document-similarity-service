import logging
import json
import os
import tempfile
from statistics import mean
from typing import Dict, Any, List
from pathlib import Path
from urllib.parse import urlparse
import requests
import pdfplumber


from .config import get_settings
from .text_utils import chunk_by_period, normalize_text
from .search_pipeline import SimilarityMatcher
from .db import mark_job_completed, mark_job_failed

logger = logging.getLogger(__name__)


settings = get_settings()

def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"}


def download_pdf(source: str, timeout: int = 60) -> tuple[str, bool]:
    if _is_http_url(source):
        response = requests.get(source, timeout=timeout)
        response.raise_for_status()
        fd, path_handle = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(response.content)
        return path_handle, True

    base_path = Path(settings.PDF_BASE_PATH).expanduser() if settings.PDF_BASE_PATH else None
    candidate = Path(source)
    if not candidate.is_absolute():
        if not base_path:
            raise ValueError("PDF_BASE_PATH is not configured; cannot resolve relative PDF file path")
        candidate = base_path / candidate
    candidate = candidate.expanduser().resolve()

    if base_path:
        base_root = base_path.resolve()
        if base_root not in candidate.parents and candidate != base_root:
            raise ValueError("Resolved PDF path is outside of configured PDF_BASE_PATH")

    if not candidate.is_file():
        raise FileNotFoundError(f"PDF file not found: {candidate}")

    return str(candidate), False


def extract_text(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        pages_text = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages_text)

def build_report(job_id: int, book_id: int, market_id: int, file_name: str,
                 chunk_reports: List[Dict[str, Any]], overall_score: float) -> str:
    summary = {
        "job_id": job_id,
        "book_id": book_id,
        "market_id": market_id,
        "file_name": file_name,
        "total_chunks": len(chunk_reports),
        "avg_similarity": round(overall_score, 4),
        "high_risk_chunks": sum(1 for item in chunk_reports if item["best_similarity"] >= 0.6),
        "medium_risk_chunks": sum(1 for item in chunk_reports if 0.3 <= item["best_similarity"] < 0.6),
    }
    detailed = []
    for index, item in enumerate(chunk_reports, start=1):
        detailed.append(
            {
                "chunk_number": index,
                "chunk_text": item["chunk"],
                "normalized_chunk": item["normalized_chunk"],
                "best_similarity": item["best_similarity"],
                "sources": item["matches"],
            }
        )
    payload = {"summary": summary, "chunks": detailed}
    return json.dumps(payload, ensure_ascii=False)

# Webhook function removed - Laravel now queries database directly


def run_plagiarism_job(job_id: int, book_id: int, market_id: int, file_name: str):
    matcher = SimilarityMatcher()
    pdf_path = None
    cleanup_required = False
    try:
        pdf_path, cleanup_required = download_pdf(file_name, timeout=settings.DOWNLOAD_TIMEOUT)
        raw_text = extract_text(pdf_path)
        chunks = chunk_by_period(raw_text)

        if not chunks:
            mark_job_completed(job_id, 0.0, build_report(job_id, book_id, market_id, file_name, [], 0.0))
            return

        reports = []
        for chunk in chunks:
            normalized = normalize_text(chunk)
            match_info = matcher.match_chunk(normalized, chunk)
            reports.append(match_info)

        best_scores = [item["best_similarity"] for item in reports]
        overall = mean(best_scores) if best_scores else 0.0
        report_json = build_report(job_id, book_id, market_id, file_name, reports, overall)
        mark_job_completed(job_id, overall, report_json)
        # Webhook removed - Laravel queries database directly
        logger.info(f"Plagiarism job {job_id} completed successfully. Laravel will query database directly.")

    except Exception as exc:
        logger.exception("Plagiarism job %s failed", job_id)
        mark_job_failed(job_id, f"error: {exc}")
        # Webhook removed - Laravel queries database directly  
        logger.info(f"Plagiarism job {job_id} failed. Laravel will query database directly.")
    finally:
        if cleanup_required and pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
