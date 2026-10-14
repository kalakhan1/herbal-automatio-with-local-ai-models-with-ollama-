"""Internal SEO validator (Rank Math-style checks)."""
import re
import logging
from typing import Dict, List

log = logging.getLogger(__name__)

def _strip_html(html: str) -> str:
    return re.sub(r'<[^>]+>', ' ', html or '')

def validate(content: str, seo_title: str, meta_desc: str, focus_kw: str,
             slug: str, word_count: int = 0) -> Dict:
    """
    Returns dict with checks (list of {name, passed, hint}) and score.
    """
    checks: List[Dict] = []
    text_lower = _strip_html(content).lower()
    kw = (focus_kw or "").lower().strip()

    # 1. Word count
    wc = word_count or len(text_lower.split())
    checks.append({
        "name": "Content length ≥ 800 words",
        "passed": wc >= 800,
        "hint": f"Current: {wc} words"
    })

    # 2. Focus keyword in title
    checks.append({
        "name": "Focus keyword in SEO title",
        "passed": bool(kw) and kw in (seo_title or "").lower(),
        "hint": f"Keyword: '{focus_kw}'"
    })

    # 3. Focus keyword in slug
    slug_l = (slug or "").lower().replace("-", " ")
    checks.append({
        "name": "Focus keyword in URL slug",
        "passed": bool(kw) and all(w in slug_l for w in kw.split()),
        "hint": f"Slug: {slug}"
    })

    # 4. Focus keyword in first paragraph
    first_para = _strip_html(content)[:400].lower()
    checks.append({
        "name": "Focus keyword in introduction",
        "passed": bool(kw) and kw in first_para,
        "hint": "Should appear in first 100 words"
    })

    # 5. Keyword density (not > 2.5%)
    if text_lower and kw:
        occurrences = text_lower.count(kw)
        density = occurrences / max(len(text_lower.split()), 1) * 100
        checks.append({
            "name": "Keyword density below 2.5%",
            "passed": density < 2.5,
            "hint": f"Current: {density:.2f}%"
        })

    # 6. SEO title length
    tlen = len(seo_title or "")
    checks.append({
        "name": "SEO title length 30–60 chars",
        "passed": 30 <= tlen <= 60,
        "hint": f"Current: {tlen} chars"
    })

    # 7. Meta description length
    mlen = len(meta_desc or "")
    checks.append({
        "name": "Meta description 120–160 chars",
        "passed": 120 <= mlen <= 160,
        "hint": f"Current: {mlen} chars"
    })

    # 8. H1/H2 structure
    h2_count = content.count("<h2")
    checks.append({
        "name": "Has at least 2 H2 headings",
        "passed": h2_count >= 2,
        "hint": f"Found {h2_count}"
    })

    # 9. Internal links
    link_count = content.count('<a href="/')
    checks.append({
        "name": "At least 1 internal link",
        "passed": link_count >= 1,
        "hint": f"Found {link_count}"
    })

    # 10. FAQ presence
    has_faq = "faq" in text_lower or "frequently asked" in text_lower
    checks.append({
        "name": "Has FAQ section",
        "passed": has_faq,
        "hint": "Look for 'FAQ' or 'Frequently Asked'"
    })

    # 11. Image ALT
    has_alt = 'alt="' in content and 'alt=""' not in content
    checks.append({
        "name": "Images have ALT text",
        "passed": has_alt,
        "hint": "Every <img> needs alt attribute"
    })

    # 12. Readability (avg sentence length)
    sentences = re.split(r'[.!?]+', _strip_html(content))
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    avg_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    checks.append({
        "name": "Average sentence < 25 words",
        "passed": avg_len < 25,
        "hint": f"Average: {avg_len:.1f} words"
    })

    passed = sum(1 for c in checks if c["passed"])
    score = int(passed / len(checks) * 100)

    return {"checks": checks, "score": score, "passed": passed, "total": len(checks)}