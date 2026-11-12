"""URL 规范化与同域判断。"""
import hashlib
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "spm",
}


def normalize_url(url: str) -> str:
    """规范化 URL：小写 scheme/host、去默认端口、去 fragment、
    排序查询参数、剔除跟踪参数、去末尾斜杠（根路径除外）。"""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "http").lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host
    if port and not (scheme == "http" and port == 80) and not (scheme == "https" and port == 443):
        netloc = f"{host}:{port}"
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
               if k.lower() not in TRACKING_PARAMS)
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def same_origin(url: str, base: str) -> bool:
    """同域判断：scheme 不强制，host(含端口) 必须一致。"""
    a, b = urlsplit(url), urlsplit(base)
    return (a.hostname or "").lower() == (b.hostname or "").lower() and _port(a) == _port(b)


def _port(parts):
    if parts.port:
        return parts.port
    return 443 if parts.scheme == "https" else 80


def resolve(base_url: str, href: str) -> str | None:
    """把页面里的 href 解析成规范化绝对 URL；非 http(s) 返回 None。"""
    href = (href or "").strip()
    if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
        return None
    abs_url = urljoin(base_url, href)
    if urlsplit(abs_url).scheme not in ("http", "https"):
        return None
    return normalize_url(abs_url)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
