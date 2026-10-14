"""AI content generation for products and blogs."""
import logging
import re
from typing import Optional, Dict
from services import ollama_service
from config import Config

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an SEO content writer for a Pakistani herbal store. "
    "Write in simple English. NEVER invent medical claims, dosages, "
    "certifications, or fake reviews. If unsure, say 'consult a professional'. "
    "Content must be original, factual, and helpful. No keyword stuffing."
)

def _count_words(html: str) -> int:
    text = re.sub(r'<[^>]+>', ' ', html or '')
    return len(text.split())

def _ensure_word_count(content: str, min_words: int) -> str:
    """Pad content with a disclaimer section if below min."""
    if _count_words(content) >= min_words:
        return content
    extra = (
        "<h2>Important Information</h2>"
        "<p>This article is provided for general information only. "
        "Please consult a qualified healthcare professional before use. "
        "Individual results may vary. Always read the product label and "
        "follow the manufacturer's instructions.</p>"
        "<h2>Where to Buy</h2>"
        "<p>Available through trusted Pakistani herbal retailers. "
        "Contact the store directly for current stock and pricing.</p>"
    )
    return content + extra

def generate_product_content(name: str, research_text: str = "") -> Optional[Dict]:
    """Generate product page content. Returns dict or None."""
    research_section = ""
    if research_text:
        research_section = f"\n\nReference material (do not copy, use only for facts):\n{research_text[:3000]}\n"

    prompt = f"""Write a WooCommerce product page for: **{name}**

Requirements:
- Minimum {Config.MIN_WORD_COUNT} words
- HTML format using <h2>, <h3>, <p>, <ul>, <li>, <strong>
- Include sections: Introduction, What is {name}, Key Information, Uses, How to Use, Precautions, Storage, FAQs (3-5), Conclusion
- No medical claims ("cure", "treat", "prevent disease")
- No invented dosages
- Natural Pakistani context
- Return ONLY valid JSON

JSON schema:
{{
  "title": "{name} - Product Page",
  "content_html": "<h2>...</h2><p>...</p>...",
  "excerpt": "One sentence description",
  "seo_title": "Max 60 chars",
  "meta_description": "Max 155 chars",
  "focus_keyword": "main keyword lowercase",
  "secondary_keywords": "comma separated"
}}
{research_section}
Return JSON only."""

    result = ollama_service.generate_json(prompt, SYSTEM_PROMPT)
    if not result or not result.get("content_html"):
        return None

    result["content_html"] = _ensure_word_count(
        result["content_html"], Config.MIN_WORD_COUNT
    )
    result["word_count"] = _count_words(result["content_html"])
    return result

def generate_blog_content(name: str, research_text: str = "") -> Optional[Dict]:
    """Generate blog article for a product. Returns dict or None."""
    research_section = ""
    if research_text:
        research_section = f"\n\nReference material (do not copy):\n{research_text[:3000]}\n"

    prompt = f"""Write a blog article about: **{name}**

Requirements:
- Different from a product page - informational/educational tone
- Minimum {Config.MIN_WORD_COUNT} words
- HTML format: <h2>, <h3>, <p>, <ul>, <li>, <strong>
- Sections: Introduction, What is {name}, Traditional Uses, Benefits, How It's Used, Precautions, FAQs, Conclusion
- No medical claims
- No invented clinical evidence or dosages
- Pakistani herbal context
- Return ONLY valid JSON

JSON schema:
{{
  "title": "Blog title about {name}",
  "content_html": "<h2>...</h2><p>...</p>...",
  "excerpt": "One sentence",
  "seo_title": "Max 60 chars",
  "meta_description": "Max 155 chars",
  "focus_keyword": "main keyword",
  "secondary_keywords": "comma separated"
}}
{research_section}
Return JSON only."""

    result = ollama_service.generate_json(prompt, SYSTEM_PROMPT)
    if not result or not result.get("content_html"):
        return None

    result["content_html"] = _ensure_word_count(
        result["content_html"], Config.MIN_WORD_COUNT
    )
    result["word_count"] = _count_words(result["content_html"])
    return result