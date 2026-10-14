"""Ollama local LLM integration."""
import json
import logging
import re
import requests
from typing import Optional, Dict, Any
from config import Config

log = logging.getLogger(__name__)


def check_connection() -> Dict[str, Any]:
    """Test Ollama connection."""
    try:
        r = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=10)
        if r.status_code != 200:
            return {"ok": False, "message": f"HTTP {r.status_code}", "models": []}
        data = r.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        return {"ok": True, "message": "Connected", "models": models}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "message": "Ollama not running. Start with: ollama serve", "models": []}
    except requests.exceptions.Timeout:
        return {"ok": False, "message": "Ollama timeout", "models": []}
    except Exception as e:
        return {"ok": False, "message": str(e)[:150], "models": []}


def generate(prompt: str, system: str = "", temperature: float = 0.7,
             max_tokens: int = 2000) -> Optional[str]:
    """
    Call Ollama generate. max_tokens limits output length for speed.
    Default 2000 tokens ≈ 1400-1500 words — enough for 800+ word articles.
    """
    payload = {
        "model": Config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": 4096,        # context window — keeps memory low
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }
    }
    if system:
        payload["system"] = system

    try:
        r = requests.post(
            f"{Config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=Config.OLLAMA_TIMEOUT
        )
        if r.status_code != 200:
            log.error(f"Ollama HTTP {r.status_code}: {r.text[:200]}")
            return None
        data = r.json()
        return (data.get("response") or "").strip()
    except requests.exceptions.Timeout:
        log.error(f"Ollama timeout after {Config.OLLAMA_TIMEOUT}s — "
                  f"try reducing num_predict or using smaller model")
        return None
    except requests.exceptions.ConnectionError:
        log.error("Ollama connection failed. Is it running?")
        return None
    except Exception as e:
        log.error(f"Ollama error: {e}")
        return None


def generate_json(prompt: str, system: str = "") -> Optional[Dict]:
    """Ask Ollama for JSON response and parse it."""
    sys_msg = system or "Return valid JSON only. No explanation, no markdown."
    raw = generate(prompt, sys_msg, temperature=0.4, max_tokens=2000)
    if not raw:
        return None
    # Direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Extract from code block
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Find first { ... last }
    s, e = raw.find('{'), raw.rfind('}')
    if s >= 0 and e > s:
        try:
            return json.loads(raw[s:e+1])
        except Exception:
            pass
    return None