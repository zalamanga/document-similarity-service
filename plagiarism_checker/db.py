import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from .config import get_settings

settings = get_settings()

@contextmanager
def db_connection():
    conn = mysql.connector.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )
    try:
        yield conn
    finally:
        conn.close()

def ensure_table_exists():
    sql = """
    CREATE TABLE IF NOT EXISTS plagiarims_checker (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        book_id BIGINT UNSIGNED NOT NULL,
        market_id BIGINT UNSIGNED NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        status TINYINT NOT NULL DEFAULT 0,
        score DECIMAL(5,4) NULL,
        report LONGTEXT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP NULL DEFAULT NULL,
        PRIMARY KEY (id),
        KEY idx_book_id (book_id),
        KEY idx_market_id (market_id),
        KEY idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()

def insert_job(book_id: int, market_id: int, file_name: str) -> int:
    sql = """
        INSERT INTO plagiarims_checker (book_id, market_id, file_name, status, score, report, created_at)
        VALUES (%s, %s, %s, 0, NULL, NULL, NOW())
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (book_id, market_id, file_name))
        conn.commit()
        return cursor.lastrowid

def mark_job_completed(job_id: int, score: float, report_json: str):
    sql = """
        UPDATE plagiarims_checker
           SET status = 1,
               score = %s,
               report = %s,
               finished_at = %s
         WHERE id = %s
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (score, report_json, datetime.now(), job_id))
        conn.commit()

# if error status = 2
def mark_job_failed(job_id: int, error_message: str):
    sql = """
        UPDATE plagiarims_checker
           SET status = 2,
               score = 0,
               report = %s,
               finished_at = %s
         WHERE id = %s
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (error_message, datetime.now(), job_id))
        conn.commit()
