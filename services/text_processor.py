"""
Pure-Python NLP text processor. No AI model required.
Uses NLTK for tokenization + WordNet synonyms, scikit-learn for TF-IDF.
"""
import logging
import random
import re
from typing import List, Dict, Optional, Tuple

try:
    import nltk
    from nltk.corpus import stopwords, wordnet
    from nltk.tokenize import sent_tokenize, word_tokenize
    NLTK_OK = True
except ImportError:
    NLTK_OK = False

try:
    import textstat
    TEXTSTAT_OK = True
except ImportError:
    TEXTSTAT_OK = False

log = logging.getLogger(__name__)

# Download NLTK data on first import
if NLTK_OK:
    for pkg in ["punkt", "punkt_tab", "stopwords", "wordnet", "averaged_perceptron_tagger"]:
        try:
            nltk.data.find(f"tokenizers/{pkg}")
        except LookupError:
            try:
                nltk.download(pkg, quiet=True)
            except Exception:
                pass


# ============================================================
# CLEANING
# ============================================================
def strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_input(raw: str) -> str:
    """Normalize user-pasted raw content."""
    if not raw:
        return ""
    t = raw.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r'\n{3,}', '\n\n', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    return t.strip()


# ============================================================
# SENTENCE SPLITTING
# ============================================================
def split_sentences(text: str) -> List[str]:
    text = strip_html(text)
    if not text:
        return []
    if NLTK_OK:
        try:
            sents = sent_tokenize(text)
        except Exception:
            sents = re.split(r'(?<=[.!?])\s+', text)
    else:
        sents = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sents if len(s.strip()) > 20]


def split_paragraphs(text: str) -> List[str]:
    text = clean_input(text)
    if not text:
        return []
    parts = re.split(r'\n\s*\n', text)
    return [p.strip() for p in parts if p.strip()]


def word_count(text: str) -> int:
    return len(strip_html(text).split())


# ============================================================
# EXTRACTIVE SUMMARIZATION
# ============================================================
def score_sentences(sentences: List[str]) -> List[Tuple[str, float]]:
    """Score sentences by term frequency (Luhn-style)."""
    if not sentences:
        return []
    stop = set(stopwords.words("english")) if NLTK_OK else {
        "the","a","an","and","or","but","is","are","was","were","to","of","in","for"
    }
    # Term frequency across all sentences
    freq: Dict[str, int] = {}
    for s in sentences:
        words = re.findall(r'\w+', s.lower())
        for w in words:
            if w in stop or len(w) < 4:
                continue
            freq[w] = freq.get(w, 0) + 1

    scored = []
    for s in sentences:
        words = re.findall(r'\w+', s.lower())
        total = 0
        cnt = 0
        for w in words:
            if w in stop or len(w) < 4:
                continue
            total += freq.get(w, 0)
            cnt += 1
        score = total / max(cnt, 1)
        # Boost longer sentences
        score *= (1 + min(len(words), 30) / 30)
        scored.append((s, score))
    return scored


def summarize_extractive(text: str, top_n: int = 20) -> List[str]:
    sents = split_sentences(text)
    if len(sents) <= top_n:
        return sents
    scored = score_sentences(sents)
    top = sorted(scored, key=lambda x: -x[1])[:top_n]
    # Preserve original order
    top_sents = set(s for s, _ in top)
    return [s for s in sents if s in top_sents]


# ============================================================
# SYNONYM SUBSTITUTION (WordNet)
# ============================================================
_SYN_REPLACEMENTS = {
    "important": ["significant", "notable", "key", "essential"],
    "benefit": ["advantage", "value", "gain", "help"],
    "use": ["application", "usage", "utilize"],
    "herbal": ["natural", "plant-based", "botanical"],
    "traditional": ["classic", "conventional", "customary"],
    "effective": ["useful", "helpful", "beneficial"],
    "natural": ["organic", "pure", "unrefined"],
    "product": ["item", "preparation", "formulation"],
    "quality": ["standard", "grade", "caliber"],
    "good": ["excellent", "positive", "favorable"],
    "many": ["several", "numerous", "multiple"],
    "help": ["assist", "support", "aid"],
    "also": ["additionally", "furthermore", "moreover"],
    "very": ["highly", "extremely", "particularly"],
    "make": ["create", "produce", "prepare"],
    "people": ["individuals", "persons", "users"],
}


def replace_synonyms(sentence: str, prob: float = 0.25,
                     seed: Optional[int] = None) -> str:
    """Replace some words with synonyms. Keeps meaning intact."""
    rng = random.Random(seed)
    tokens = re.findall(r'\b[\w-]+\b|[^\w\s]+|\s+', sentence)
    result = []
    for tok in tokens:
        low = tok.lower()
        if low in _SYN_REPLACEMENTS and rng.random() < prob:
            choice = rng.choice(_SYN_REPLACEMENTS[low])
            # Match case
            if tok[0].isupper():
                choice = choice.capitalize()
            result.append(choice)
        else:
            result.append(tok)
    return "".join(result)


# ============================================================
# TRANSITIONS / SENTENCE STARTERS
# ============================================================
TRANSITIONS = [
    "", "", "", "",  # keep original 80% of time
    "Additionally, ",
    "Moreover, ",
    "In addition, ",
    "Furthermore, ",
    "Besides this, ",
    "Interestingly, ",
    "Notably, ",
    "Importantly, ",
]


def add_transition(sentence: str, rng: random.Random) -> str:
    t = rng.choice(TRANSITIONS)
    if not t:
        return sentence
    # Avoid double transitions
    if sentence.lower().startswith(("additionally", "moreover", "furthermore",
                                    "in addition", "besides", "interestingly",
                                    "notably", "importantly")):
        return sentence
    return t + sentence[0].lower() + sentence[1:] if sentence else sentence


# ============================================================
# KEYWORD EXTRACTION (TF-IDF-ish)
# ============================================================
def extract_keywords(text: str, n: int = 12) -> List[str]:
    text_low = strip_html(text).lower()
    words = re.findall(r'\b[a-z][a-z\-]{3,}\b', text_low)
    stop = set(stopwords.words("english")) if NLTK_OK else {"the","this","that","with"}
    freq: Dict[str, int] = {}
    for w in words:
        if w in stop:
            continue
        freq[w] = freq.get(w, 0) + 1
    # Bigrams
    bigrams: Dict[str, int] = {}
    tokens = [w for w in words if w not in stop]
    for i in range(len(tokens) - 1):
        bg = f"{tokens[i]} {tokens[i+1]}"
        bigrams[bg] = bigrams.get(bg, 0) + 1
    top_single = sorted(freq.items(), key=lambda x: -x[1])[:n]
    top_bi = sorted(bigrams.items(), key=lambda x: -x[1])[:max(3, n // 2)]
    result = [k for k, v in top_bi if v >= 2] + [k for k, v in top_single if k not in " ".join([x[0] for x in top_bi])]
    return result[:n]


# ============================================================
# FAQ EXTRACTION
# ============================================================
def generate_faqs(topic: str, keywords: List[str], count: int = 5) -> List[Dict]:
    """Generate templated FAQs based on topic + keywords."""
    name = topic.title()
    pool = [
        (f"What is {name}?", f"{name} is a herbal product available from trusted Pakistani sources. It has been used in traditional practice for generations."),
        (f"Is {name} safe for daily use?", f"As with any herbal product, use moderately and follow the label. Consult a qualified professional if you are pregnant, nursing or taking medication."),
        (f"What are the traditional uses of {name}?", f"Traditional Pakistani households have used {name} for various everyday purposes. Individual uses vary — always read the manufacturer's guidance."),
        (f"Where can I buy {name} in Pakistan?", f"You can order {name} online from our store with delivery across Pakistan."),
        (f"Can {name} be combined with other herbal products?", f"Many people do combine herbal products. Review related items from the same category and consult a practitioner if unsure."),
        (f"How should I store {name}?", f"Keep it cool, dry, away from direct sunlight. Close the container tightly after use."),
        (f"Is {name} a medicine?", f"No. {name} is a herbal product, not a medicine, and it is not intended to diagnose, treat, cure or prevent any disease."),
        (f"What are the key ingredients?", f"Ingredient details are printed on the product label. Please read it carefully before use."),
    ]
    return [{"q": q, "a": a} for q, a in pool[:count]]


# ============================================================
# HTML BUILDER
# ============================================================
def build_article_html(title: str, sections: List[Dict], faqs: List[Dict],
                       conclusion: str = "") -> str:
    """
    sections = [{"heading": "What is X", "paragraphs": ["...", "..."]}, ...]
    """
    parts = [f"<h1>{_esc(title)}</h1>"]
    for s in sections:
        if s.get("heading"):
            parts.append(f"<h2>{_esc(s['heading'])}</h2>")
        for p in s.get("paragraphs", []):
            if p.strip():
                parts.append(f"<p>{_esc(p)}</p>")
    if faqs:
        parts.append("<h2>Frequently Asked Questions</h2>")
        for f in faqs:
            parts.append(f"<h3>{_esc(f['q'])}</h3>")
            parts.append(f"<p>{_esc(f['a'])}</p>")
    if conclusion:
        parts.append("<h2>Conclusion</h2>")
        parts.append(f"<p>{_esc(conclusion)}</p>")
    return "\n".join(parts)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================
# READABILITY
# ============================================================
def readability_score(html: str) -> Dict:
    text = strip_html(html)
    if not text or not TEXTSTAT_OK:
        return {"flesch": 0, "grade": 0}
    try:
        return {
            "flesch": round(textstat.flesch_reading_ease(text), 1),
            "grade": round(textstat.flesch_kincaid_grade(text), 1),
        }
    except Exception:
        return {"flesch": 0, "grade": 0}