"""Products routes."""
from flask import Blueprint, request, jsonify, render_template
import re
import logging
import database
from services import ollama_service, content_service, research_service
from services import duplicate_service, seo_service, internal_link_service
from config import Config

bp = Blueprint("products", __name__)
log = logging.getLogger(__name__)

def _slugify(text: str) -> str:
    t = re.sub(r'[^a-z0-9\s-]', '', (text or "").lower())
    t = re.sub(r'[\s_]+', '-', t)
    return t.strip('-')


def _generate_content_for(pid: int) -> dict:
    """
    Core generation logic — returns plain dict {ok, seo_score?, error?}.
    No Flask context. Used by both single and batch endpoints.
    """
    p = database.get_product(pid)
    if not p:
        return {"ok": False, "error": "Product not found"}

    database.update_product(pid, status="GENERATING")

    try:
        # Research (optional)
        research_text = ""
        if getattr(Config, "RESEARCH_ENABLED", False):
            try:
                research = research_service.research_product(p["name"])
                research_text = research.get("text", "")
            except Exception as e:
                log.warning(f"Research skipped for {p['name']}: {e}")

        # Product content
        prod = content_service.generate_product_content(p["name"], research_text)
        if not prod:
            database.update_product(pid, status="FAILED", error="Product generation failed")
            return {"ok": False, "error": "Product generation failed"}

        # Blog content
        blog = content_service.generate_blog_content(p["name"], research_text)
        if not blog:
            blog = {
                "content_html": "", "word_count": 0, "title": f"{p['name']} Guide",
                "excerpt": "", "seo_title": "", "meta_description": "",
                "focus_keyword": p["name"].lower(), "secondary_keywords": ""
            }

        # SEO validation
        seo = seo_service.validate(
            prod.get("content_html", ""),
            prod.get("seo_title", ""),
            prod.get("meta_description", ""),
            prod.get("focus_keyword", ""),
            p["slug"],
            prod.get("word_count", 0)
        )

        database.update_product(
            pid,
            status="READY",
            product_title=prod.get("title", ""),
            product_content=prod.get("content_html", ""),
            product_excerpt=prod.get("excerpt", ""),
            product_word_count=prod.get("word_count", 0),
            blog_title=blog.get("title", ""),
            blog_content=blog.get("content_html", ""),
            blog_excerpt=blog.get("excerpt", ""),
            blog_slug=p["slug"] + "-guide",
            blog_word_count=blog.get("word_count", 0),
            seo_title=prod.get("seo_title", ""),
            meta_description=prod.get("meta_description", ""),
            focus_keyword=prod.get("focus_keyword", ""),
            secondary_keywords=prod.get("secondary_keywords", ""),
            seo_score=seo["score"],
            error="",
        )
        return {"ok": True, "seo_score": seo["score"]}

    except Exception as e:
        log.exception(f"Generate failed for {pid}")
        database.update_product(pid, status="FAILED", error=str(e)[:200])
        return {"ok": False, "error": str(e)[:200]}


@bp.route("/products")
def page():
    return render_template("products.html", active="products")


@bp.route("/api/products", methods=["GET"])
def list_products():
    return jsonify(database.get_all_products())


@bp.route("/api/products/add", methods=["POST"])
def add_products():
    data = request.get_json(force=True) or {}
    raw = (data.get("names") or "").strip()
    if not raw:
        return jsonify({"ok": False, "error": "No names provided"}), 400

    names = [n.strip() for n in re.split(r'[,\n]+', raw) if n.strip()]
    seen = set()
    unique = []
    for n in names:
        key = n.lower()
        if key not in seen:
            seen.add(key)
            unique.append(n)

    added = 0
    for i, name in enumerate(unique):
        slug = _slugify(name)
        if not slug:
            continue
        sku = f"KHS-{i+1:04d}"
        pid = database.insert_product(name, slug, sku)
        if pid:
            added += 1

    return jsonify({
        "ok": True,
        "detected": len(names),
        "unique": len(unique),
        "added": added
    })


@bp.route("/api/products/clear", methods=["POST"])
def clear():
    database.clear_products()
    return jsonify({"ok": True})


@bp.route("/api/products/ollama-test")
def ollama_test():
    return jsonify(ollama_service.check_connection())


@bp.route("/api/products/generate/<int:pid>", methods=["POST"])
def generate_one(pid):
    result = _generate_content_for(pid)
    status = 200 if result.get("ok") else 500
    return jsonify(result), status


@bp.route("/api/products/generate-batch", methods=["POST"])
def generate_batch():
    """Generate next N pending products."""
    data = request.get_json(force=True) or {}
    limit = int(data.get("limit", Config.BATCH_SIZE))

    pending = database.get_all_products("PENDING")
    if not pending:
        return jsonify({"ok": True, "processed": 0, "message": "No pending products"})

    if Config.TEST_MODE:
        limit = min(limit, Config.TEST_PRODUCTS)

    processed = 0
    failed = 0
    for p in pending[:limit]:
        r = _generate_content_for(p["id"])
        if r.get("ok"):
            processed += 1
        else:
            failed += 1
    return jsonify({"ok": True, "processed": processed, "failed": failed})


@bp.route("/api/products/dedup-check", methods=["POST"])
def dedup_check():
    products = database.get_all_products()
    items = [{"id": p["id"], "product_content": p.get("product_content") or ""}
             for p in products if p.get("product_content")]
    results = duplicate_service.check_duplicates(items, "product_content")
    for r in results:
        database.update_product(r["id"], duplicate_score=r["max_similarity"])
    return jsonify({"ok": True, "checked": len(results)})


@bp.route("/api/products/build-links", methods=["POST"])
def build_links():
    products = database.get_all_products()
    url_map = internal_link_service.build_url_map(products, Config.WP_BASE_URL)
    count = 0
    for p in products:
        if not p.get("product_content"):
            continue
        new_content = internal_link_service.inject_internal_links(
            p["product_content"], p["id"], products, url_map, Config.WP_BASE_URL
        )
        if new_content != p["product_content"]:
            database.update_product(p["id"], product_content=new_content)
            count += 1
    return jsonify({"ok": True, "updated": count})