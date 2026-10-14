"""WordPress REST API integration."""
import logging
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests
from requests.auth import HTTPBasicAuth
from config import Config

log = logging.getLogger(__name__)

class WPError(Exception):
    pass

def _auth() -> Optional[HTTPBasicAuth]:
    if not (Config.WP_BASE_URL and Config.WP_USERNAME and Config.WP_APP_PASSWORD):
        return None
    return HTTPBasicAuth(Config.WP_USERNAME, Config.WP_APP_PASSWORD)

def test_connection() -> Dict:
    """Test WordPress connection."""
    if not Config.WP_BASE_URL:
        return {"ok": False, "message": "WP_BASE_URL not configured"}
    auth = _auth()
    if not auth:
        return {"ok": False, "message": "WP credentials not set"}
    try:
        r = requests.get(
            f"{Config.WP_BASE_URL}/wp-json/wp/v2/users/me",
            auth=auth, timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            return {"ok": True, "message": f"Connected as {data.get('name', 'user')}",
                    "user": data.get("name", "")}
        if r.status_code == 401:
            return {"ok": False, "message": "Authentication failed (check credentials)"}
        return {"ok": False, "message": f"HTTP {r.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "message": "Cannot reach WordPress"}
    except Exception as e:
        return {"ok": False, "message": str(e)[:200]}

def upload_media(file_path: Path, alt_text: str = "",
                 title: str = "", description: str = "",
                 filename_override: Optional[str] = None) -> Tuple[bool, Dict]:
    """Upload a media file. Returns (success, {id, url} or {error})."""
    auth = _auth()
    if not auth:
        return False, {"error": "WP not configured"}

    if not file_path.exists():
        return False, {"error": f"File not found: {file_path}"}

    url = f"{Config.WP_BASE_URL}/wp-json/wp/v2/media"
    filename = filename_override or file_path.name
    mime = mimetypes.guess_type(filename)[0] or "image/webp"

    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime)}
            data = {
                "title": title or filename,
                "alt_text": alt_text,
                "caption": "",
                "description": description,
                "status": "publish",
            }
            r = requests.post(url, auth=auth, files=files, data=data, timeout=90)
        if r.status_code in (200, 201):
            j = r.json()
            return True, {"id": j.get("id"), "url": j.get("source_url", "")}
        return False, {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return False, {"error": str(e)[:200]}

def create_blog_draft(title: str, content: str, excerpt: str = "",
                      slug: str = "", featured_media: Optional[int] = None,
                      meta: Optional[Dict] = None) -> Tuple[bool, Dict]:
    """Create a blog post as DRAFT. Returns (success, {id, url} or {error})."""
    auth = _auth()
    if not auth:
        return False, {"error": "WP not configured"}

    url = f"{Config.WP_BASE_URL}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "content": content,
        "excerpt": excerpt,
        "slug": slug,
        "status": "draft",
    }
    if featured_media:
        payload["featured_media"] = featured_media
    if meta:
        payload["meta"] = meta

    try:
        r = requests.post(url, auth=auth, json=payload, timeout=60)
        if r.status_code in (200, 201):
            j = r.json()
            return True, {"id": j.get("id"), "url": j.get("link", "")}
        return False, {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return False, {"error": str(e)[:200]}

def update_blog_post(post_id: int, **fields) -> Tuple[bool, Dict]:
    """Update existing post."""
    auth = _auth()
    if not auth:
        return False, {"error": "WP not configured"}
    url = f"{Config.WP_BASE_URL}/wp-json/wp/v2/posts/{post_id}"
    try:
        r = requests.post(url, auth=auth, json=fields, timeout=60)
        if r.status_code == 200:
            return True, {"id": post_id, "url": r.json().get("link", "")}
        return False, {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return False, {"error": str(e)[:200]}

def find_post_by_slug(slug: str) -> Optional[Dict]:
    """Check if a post with this slug exists."""
    auth = _auth()
    if not auth:
        return None
    url = f"{Config.WP_BASE_URL}/wp-json/wp/v2/posts?slug={slug}&status=any"
    try:
        r = requests.get(url, auth=auth, timeout=20)
        if r.status_code == 200:
            arr = r.json()
            if arr:
                return arr[0]
    except Exception:
        pass
    return None