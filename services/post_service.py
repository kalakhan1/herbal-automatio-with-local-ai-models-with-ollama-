"""
Blog post generator — pure Python, no AI.
Takes raw pasted content and produces SEO-optimized HTML.
"""
import hashlib
import logging
import random
import re
from typing import Dict, List, Optional

from services import text_processor as tp
from services import seo_service

log = logging.getLogger(__name__)

MIN_WORDS = 1200
TARGET_WORDS = 1400

# Section templates — order + heading style
SECTION_TEMPLATES = [
    "Introduction",
    "What is {topic}?",
    "Key Facts About {topic}",
    "Traditional Uses and Benefits",
    "How {topic} Is Typically Used",
    "Precautions and Important Information",
    "Buying {topic} in Pakistan",
    "Storage and Care",
]

TRANSITIONS = [
    "", "", "",
    "Additionally, ",
    "Moreover, ",
    "In addition, ",
    "Furthermore, ",
    "Interestingly, ",
    "Importantly, ",
    "Notably, ",
    "Besides this, ",
]


def _slugify(text: str, max_words: int = 8) -> str:
    t = re.sub(r'[^a-z0-9\s-]', '', (text or "").lower())
    t = re.sub(r'[\s_]+', '-', t)
    return '-'.join(t.strip('-').split('-')[:max_words])


def _make_seed(*parts) -> int:
    h = hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16)


# ============================================================
# CORE REFORMULATOR
# ============================================================
def _reformulate_sentence(sent: str, rng: random.Random) -> str:
    """One sentence → slightly different but readable version."""
    s = tp.replace_synonyms(sent, prob=0.22, seed=rng.randint(0, 2**31))
    # Add transition occasionally
    if rng.random() < 0.18:
        s = tp.add_transition(s, rng)
    # Merge tiny fragments
    if len(s.split()) < 6 and rng.random() < 0.4:
        s = "In simple terms, " + s[0].lower() + s[1:] if s else s
    return s


def _group_into_sections(sentences: List[str], topic: str,
                         keywords: List[str], rng: random.Random) -> List[Dict]:
    """
    Group sentences into logical sections with headings.
    Heuristic: distribute sentences roughly per template slot.
    """
    n = len(sentences)
    if n == 0:
        return []

    # Compute how many sentences per section (min 2, max 8)
    target_sections = min(len(SECTION_TEMPLATES), max(4, n // 3))
    per_section = max(2, n // target_sections)

    sections = []
    idx = 0
    for heading_tpl in SECTION_TEMPLATES[:target_sections]:
        if idx >= n:
            break
        chunk = sentences[idx:idx + per_section]
        idx += per_section

        # Reformulate each sentence
        paras = [_reformulate_sentence(s, rng) for s in chunk]

        # Paragraph grouping: 2-4 sentences per paragraph
        grouped = []
        buf = []
        for p in paras:
            buf.append(p)
            if len(buf) >= rng.randint(2, 4):
                grouped.append(" ".join(buf))
                buf = []
        if buf:
            grouped.append(" ".join(buf))

        heading = heading_tpl.format(topic=topic)
        sections.append({"heading": heading, "paragraphs": grouped})

    # Any leftover sentences
    if idx < n:
        leftover = [_reformulate_sentence(s, rng) for s in sentences[idx:]]
        sections.append({
            "heading": f"More on {topic}",
            "paragraphs": [" ".join(leftover[i:i+3]) for i in range(0, len(leftover), 3)]
        })

    return sections


def _ensure_word_count(sections: List[Dict], min_words: int, topic: str) -> List[Dict]:
    """Add padding sections if below minimum."""
    current = sum(len(p.split()) for s in sections for p in s.get("paragraphs", []))
    if current >= min_words:
        return sections

    fillers = [
        {
            "heading": f"Understanding {topic} Better",
            "paragraphs": [
                f"When exploring {topic}, it helps to understand the broader context of traditional herbal practice in Pakistan. Generations of households have kept similar products on hand, using them as part of everyday routines rather than as isolated items.",
                f"Individual experiences with {topic} vary, which is why reading the manufacturer's guidance is essential. The label provides the authoritative information on ingredients, quantity, and any precautions specific to the product.",
            ],
        },
        {
            "heading": f"Why {topic} Matters",
            "paragraphs": [
                f"Interest in {topic} reflects a wider movement toward traditional and plant-based options in Pakistan. Many buyers appreciate being able to compare products from the same category side by side, which is exactly what our store makes possible.",
                f"If you are new to herbal products, starting with one or two items from the same category — like {topic} — is a sensible approach. You can build your routine gradually as you learn what suits you.",
            ],
        },
        {
            "heading": "Choosing the Right Product",
            "paragraphs": [
                f"Look for clear category information, stable availability, and honest product descriptions. These three factors make it easier to compare and reorder the same {topic} when you need it.",
                f"Questions are welcome — reach out through the contact options listed on this page if you need further details about {topic} before ordering.",
            ],
        },
    ]

    for f in fillers:
        sections.append(f)
        current = sum(len(p.split()) for s in sections for p in s.get("paragraphs", []))
        if current >= min_words:
            break

    return sections


# ============================================================
# MAIN ENTRY
# ============================================================
def generate_post(title_hint: str, raw_content: str,
                  existing_posts: List[Dict] = None,
                  existing_products: List[Dict] = None) -> Optional[Dict]:
    """
    Generate SEO-optimized blog post from raw content.

    Args:
      title_hint: user's desired title
      raw_content: pasted raw material (any length)
      existing_posts: for dup-check against other posts
      existing_products: for cross-linking

    Returns dict with keys: title, slug, content_html, excerpt,
                             seo_title, meta_description, focus_keyword,
                             secondary_keywords, faqs, word_count, seo_score
    """
    title_hint = (title_hint or "").strip()
    raw = tp.clean_input(raw_content or "")

    if not raw:
        log.warning("generate_post: empty raw_content")
        return None

    # Derive topic from title (fall back to first few words)
    topic = title_hint or " ".join(raw.split()[:6])

    # Keywords
    keywords = tp.extract_keywords(raw, n=12)
    focus_kw = (keywords[0] if keywords else topic.lower())[:60]

    # Summarize: top sentences + padding
    sentences = tp.summarize_extractive(raw, top_n=max(30, TARGET_WORDS // 30))
    if len(sentences) < 12:
        sentences = tp.split_sentences(raw)

    rng = random.Random(_make_seed(title_hint, raw[:200]))

    # Build sections
    sections = _group_into_sections(sentences, topic, keywords, rng)
    sections = _ensure_word_count(sections, MIN_WORDS, topic)

    # FAQs
    faqs = tp.generate_faqs(topic, keywords, count=5)

    # Conclusion
    conclusion = (
        f"In summary, {topic} belongs to a rich tradition of herbal products "
        f"in Pakistan. Whether you are continuing a family routine or exploring "
        f"something new, this guide has covered the essentials. Always read "
        f"the manufacturer's guidance, store the product correctly, and consult "
        f"a qualified professional if you have any questions about suitability."
    )

    # Build HTML
    html = tp.build_article_html(title_hint or topic, sections, faqs, conclusion)

    # SEO fields
    seo_title = _make_seo_title(title_hint or topic, focus_kw)
    meta_desc = _make_meta(title_hint or topic, focus_kw)
    slug = _slugify(title_hint or topic)
    excerpt = _make_excerpt(topic, raw)

    # SEO validation
    seo = seo_service.validate(
        html, seo_title, meta_desc, focus_kw, slug, tp.word_count(html)
    )

    return {
        "title": title_hint or topic,
        "slug": slug,
        "content_html": html,
        "excerpt": excerpt,
        "seo_title": seo_title,
        "meta_description": meta_desc,
        "focus_keyword": focus_kw,
        "secondary_keywords": ", ".join(keywords[1:6]),
        "faqs": faqs,
        "word_count": tp.word_count(html),
        "seo_score": seo["score"],
        "seo_checks": seo["checks"],
        "readability": tp.readability_score(html),
    }


def _make_seo_title(topic: str, kw: str) -> str:
    t = f"{topic.title()} | Complete Guide & Uses"
    return t[:60]


def _make_meta(topic: str, kw: str) -> str:
    m = (f"Complete guide to {topic} in Pakistan. Learn about traditional uses, "
         f"precautions, storage, and where to buy online.")
    return m[:160]


def _make_excerpt(topic: str, raw: str) -> str:
    first = tp.split_sentences(raw)[:1]
    if first:
        return first[0][:200]
    return f"A complete guide to {topic}."[:200]