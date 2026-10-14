"""Internal linking between products and blogs."""
import logging
from typing import List, Dict

log = logging.getLogger(__name__)

def build_url_map(products: List[Dict], wp_base: str = "") -> Dict:
    """
    Build map of product_id -> {product_url, blog_url, product_title, blog_title}
    """
    base = (wp_base or "").rstrip("/")
    url_map = {}
    for p in products:
        pid = p["id"]
        slug = p.get("slug") or ""
        url_map[pid] = {
            "product_url": f"{base}/product/{slug}/" if slug else "",
            "blog_url": f"{base}/blog/{slug}-guide/" if slug else "",
            "product_title": p.get("product_title") or p.get("name"),
            "blog_title": p.get("blog_title") or f"{p.get('name')} Guide",
            "name": p.get("name", "")
        }
    return url_map

def related_products(pid: int, all_products: List[Dict], count: int = 3) -> List[Dict]:
    """Return 3 related products (simple: next N by id, wrap around)."""
    ids = [p["id"] for p in all_products]
    if pid not in ids:
        return []
    idx = ids.index(pid)
    related = []
    for offset in range(1, count + 1):
        rid = ids[(idx + offset) % len(ids)]
        if rid != pid:
            rp = next((x for x in all_products if x["id"] == rid), None)
            if rp:
                related.append(rp)
    return related

def inject_internal_links(content: str, current_id: int, all_products: List[Dict],
                          url_map: Dict, wp_base: str) -> str:
    """
    Append internal links section to content.
    """
    related = related_products(current_id, all_products, count=3)
    if not related:
        return content

    links_html = ['<h2>Related Products</h2>', '<ul>']
    for rp in related:
        info = url_map.get(rp["id"], {})
        url = info.get("product_url", "")
        title = info.get("product_title", rp.get("name", ""))
        blog_url = info.get("blog_url", "")
        if url:
            links_html.append(f'<li><a href="{url}">{title}</a></li>')
        if blog_url and info.get("blog_title"):
            links_html.append(
                f'<li><a href="{blog_url}">{info["blog_title"]}</a></li>'
            )
    links_html.append('</ul>')

    return content + "\n" + "\n".join(links_html)

def validate_links(content: str, url_map: Dict) -> Dict:
    """Check that all internal links exist in url_map."""
    import re
    urls = re.findall(r'href="([^"]+)"', content or "")
    valid_urls = set()
    for info in url_map.values():
        if info.get("product_url"): valid_urls.add(info["product_url"])
        if info.get("blog_url"): valid_urls.add(info["blog_url"])

    broken = []
    for u in urls:
        if u.startswith("/") or u.startswith("http"):
            # Only validate internal ones
            if u.startswith("/product/") or u.startswith("/blog/"):
                if not any(u in v or v in u for v in valid_urls):
                    broken.append(u)

    return {"total": len(urls), "broken": broken, "ok": len(broken) == 0}