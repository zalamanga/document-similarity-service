import os
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

class Settings:
    DB_HOST: str = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT: int = int(os.getenv('DB_PORT', '3306'))
    DB_USER: str = os.getenv('DB_USER', 'demo_user')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    DB_NAME: str = os.getenv('DB_NAME', 'similarity_demo')
    GOOGLE_API_KEY: str | None = os.getenv('GOOGLE_API_KEY', '')
    SEARCH_ENGINE_ID: str | None = os.getenv('SEARCH_ENGINE_ID', '')
    DOWNLOAD_TIMEOUT: int = int(os.getenv('PDF_DOWNLOAD_TIMEOUT', '60'))
    MAX_SEARCH_RESULTS: int = int(os.getenv('MAX_SEARCH_RESULTS', '5'))
    MAX_CRAWL_PER_CHUNK: int = int(os.getenv('MAX_CRAWL_PER_CHUNK', '3'))
    SIMILARITY_THRESHOLD: float = float(os.getenv('SIMILARITY_THRESHOLD', '0.2'))
    PDF_BASE_PATH: str = os.getenv('PDF_BASE_PATH', '')

@lru_cache()
def get_settings() -> Settings:
    return Settings()
