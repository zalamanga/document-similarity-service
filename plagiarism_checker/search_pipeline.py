import time
import logging
from typing import List, Dict
import requests
from bs4 import BeautifulSoup, FeatureNotFound
from bs4.builder import ParserRejectedMarkup
from googleapiclient.discovery import build

from .config import get_settings
from .text_utils import normalize_text, similarity_ratio

logger = logging.getLogger(__name__)
settings = get_settings()

class GoogleSearcher:
    def __init__(self):
        if not settings.GOOGLE_API_KEY or not settings.SEARCH_ENGINE_ID:
            raise RuntimeError("Google API credentials missing")
        self.service = build("customsearch", "v1", developerKey=settings.GOOGLE_API_KEY)
        self.last_search = 0.0

    def search(self, query: str, limit: int) -> List[str]:
        now = time.time()
        if now - self.last_search < 1.0:
            time.sleep(1.0 - (now - self.last_search))
        
        clean_query = query.strip()
        if not clean_query:
            return []
        
        # Safety check: jika sangat panjang, potong per kata (bukan karakter)
        if len(clean_query) > 500:  # Conservative limit
            words = clean_query.split()
            truncated_words = []
            char_count = 0
            for word in words:
                if char_count + len(word) + 1 <= 500:
                    truncated_words.append(word)
                    char_count += len(word) + 1
                else:
                    break
            clean_query = " ".join(truncated_words)
        
        if not clean_query:
            return []
        
        try:
            response = self.service.cse().list(
                q=clean_query,
                cx=settings.SEARCH_ENGINE_ID,
                num=min(limit, 10),
            ).execute()
        except Exception as e:
            logger.error(f"Google Search API error for query '{clean_query[:50]}...': {e}")
            return []
        self.last_search = time.time()
        items = response.get("items", [])
        return [item["link"] for item in items if "link" in item]

class WebCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0 Safari/537.36"
                )
            }
        )
        self.parsers = self._detect_parsers()

    def _detect_parsers(self) -> List[str]:
        candidates = ["html.parser", "lxml", "html5lib"]
        available: List[str] = []
        for parser in candidates:
            try:
                BeautifulSoup("<html></html>", parser)
            except FeatureNotFound:
                continue
            except Exception:
                continue
            else:
                if parser not in available:
                    available.append(parser)
        if not available:
            available.append("html.parser")
        return available

    def _extract_text(self, soup: BeautifulSoup) -> str:
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=["content", "main-content", "post-content", "entry-content"])
            or soup.find("div", id=["content", "main-content"])
            or soup.body
        )
        text = main.get_text(separator=" ") if main else soup.get_text(separator=" ")
        return " ".join(segment.strip() for segment in text.split() if segment.strip())

    def _decode_content(self, content: bytes, encoding: str | None) -> str:
        if encoding:
            try:
                return content.decode(encoding, errors="ignore")
            except (LookupError, ValueError):
                pass
        return content.decode("utf-8", errors="ignore")

    def _parse_with_fallback(self, content: bytes, encoding: str | None, max_length: int) -> str:
        last_error: Exception | None = None
        for parser in self.parsers:
            try:
                soup = BeautifulSoup(content, parser)
            except (ParserRejectedMarkup, AssertionError, ValueError) as exc:
                last_error = exc
                logger.debug("Parser %s rejected content: %s", parser, exc)
                continue
            except FeatureNotFound as exc:
                logger.debug("Parser %s is not available: %s", parser, exc)
                continue
            except Exception as exc:
                last_error = exc
                logger.debug("Parser %s raised error: %s", parser, exc)
                continue
            extracted = self._extract_text(soup)
            if extracted:
                return extracted[:max_length]
        if last_error:
            logger.warning("Falling back to raw decode after parser errors: %s", last_error)
        decoded = self._decode_content(content, encoding)
        return " ".join(segment.strip() for segment in decoded.split() if segment.strip())[:max_length]

    def fetch(self, url: str, max_length: int = 5000) -> str:
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Failed fetching %s: %s", url, exc)
            return ""

        text = self._parse_with_fallback(
            resp.content,
            resp.encoding or getattr(resp, "apparent_encoding", None),
            max_length,
        )
        if not text:
            logger.debug("Empty response body after parsing %s", url)
        return text

class SimilarityMatcher:
    def __init__(self):
        self.searcher = GoogleSearcher()
        self.crawler = WebCrawler()

    def _should_skip(self, url: str) -> bool:
        blocked_extensions = (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".rar")
        blocked_domains = ("youtube.com", "facebook.com", "twitter.com", "instagram.com")
        url_lower = url.lower()
        return url_lower.endswith(blocked_extensions) or any(domain in url_lower for domain in blocked_domains)

    def match_chunk(self, normalized_chunk: str, raw_chunk: str) -> Dict:
        try:
            urls = self.searcher.search(normalized_chunk, settings.MAX_SEARCH_RESULTS + 2)
        except Exception as e:
            logger.error(f"Search failed for chunk: {e}")
            # Return empty result instead of crashing
            return {
                "chunk": raw_chunk,
                "normalized_chunk": normalized_chunk,
                "best_similarity": 0.0,
                "matches": [],
            }
        
        matches: List[Dict] = []
        crawled = 0

        for url in urls:
            if crawled >= settings.MAX_CRAWL_PER_CHUNK:
                break
            if self._should_skip(url):
                continue
            content = self.crawler.fetch(url)
            if not content:
                continue
            crawled += 1

            normalized_content = normalize_text(content)
            similarity = similarity_ratio(normalized_chunk, normalized_content)
            if similarity >= settings.SIMILARITY_THRESHOLD:
                matches.append(
                    {
                        "url": url,
                        "similarity": round(similarity, 4),
                        "content_preview": content[:300] + ("..." if len(content) > 300 else ""),
                    }
                )

        matches.sort(key=lambda item: item["similarity"], reverse=True)
        best_similarity = matches[0]["similarity"] if matches else 0.0
        return {
            "chunk": raw_chunk,
            "normalized_chunk": normalized_chunk,
            "best_similarity": best_similarity,
            "matches": matches,
        }
