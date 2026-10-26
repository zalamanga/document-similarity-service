from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, field_validator
import logging

from .config import get_settings
from .db import ensure_table_exists, insert_job
from .pipeline import run_plagiarism_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Plagiarism Checker Service")
settings = get_settings()

class PlagiarismRequest(BaseModel):
    file_name: str = Field(..., min_length=1)
    book_id: int
    market_id: int

    @field_validator("file_name", mode="before")
    @classmethod
    def _clean_file_name(cls, value):
        if isinstance(value, str):
            value = value.strip()
        if not value:
            raise ValueError("file_name must not be empty")
        return value

@app.on_event("startup")
def startup_event():
    ensure_table_exists()
    if not settings.GOOGLE_API_KEY or not settings.SEARCH_ENGINE_ID:
        logger.warning("Google Search credentials missing; plagiarism checks will fail.")

@app.post("/check_plagiarism")
async def check_plagiarism(payload: PlagiarismRequest, background_tasks: BackgroundTasks):
    try:
        job_id = insert_job(payload.book_id, payload.market_id, str(payload.file_name))
    except Exception as exc:
        logger.exception("Failed inserting job")
        raise HTTPException(status_code=500, detail="Failed to schedule plagiarism job") from exc

    background_tasks.add_task(
        run_plagiarism_job,
        job_id,
        payload.book_id,
        payload.market_id,
        str(payload.file_name),
    )

    return {    #respon cepat laravel
        "status": "accepted",
        "message": "Plagiarism check is in progress",
        "market_id": payload.market_id,
        "book_id": payload.book_id,
        "job_id": job_id,   # job_id / plagiarism_id untuk tracking status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
