"""Blog posts routes — pure Python generation."""
import logging
import re
from flask import Blueprint, render_template, request, jsonify

import database
from services import post_service, text_processor
from config import Config

bp = Blueprint("posts", __name__)
log = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    t = re.sub(r'[^a-z0-9\s-]', '', (text or "").lower())
    t = re.sub(r'[\s_]+', '-', t)
    return t.strip('-')


@bp.route("/posts")
def page():
    return render_template("posts.html", active="posts")


@bp.route("/api/posts", methods=["GET"])
def list_posts():
    return jsonify(database.get_all_posts())


@bp.route("/api/posts/add", methods=["POST"])
def add_post():
    """Add a new post with title + raw content."""
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    raw = (data.get("content") or "").strip()

    if not title:
        return jsonify({"ok": False, "error": "Title required"}), 400
    if not raw or len(raw) < 100:
        return jsonify({"ok": False, "error": "Content must be at least 100 characters"}), 400

    slug = _slugify(title)
    if not slug:
        return jsonify({"ok": False, "error": "Invalid title"}), 400

    # Duplicate slug check
    if database.get_post_by_slug(slug):
        slug = f"{slug}-{int(__import__('time').time())}"

    pid = database.insert_post(title, slug, raw)
    if not pid:
        return jsonify({"ok": False, "error": "Could not save post"}), 500

    return jsonify({"ok": True, "id": pid, "slug": slug})


@bp.route("/api/posts/generate/<int:pid>", methods=["POST"])
def generate_post(pid):
    """Generate SEO content for a post from its raw material."""
    p = database.get_post(pid)
    if not p:
        return jsonify({"ok": False, "error": "Not found"}), 404

    database.update_post(pid, status="GENERATING")

    try:
        existing_posts = [x for x in database.get_all_posts() if x["id"] != pid]
        existing_products = database.get_all_products()
        result = post_service.generate_post(
            title_hint=p["title"],
            raw_content=p.get("source_content") or "",
            existing_posts=existing_posts,
            existing_products=existing_products,
        )
        if not result:
            database.update_post(pid, status="FAILED", error="Generation returned empty")
            return jsonify({"ok": False, "error": "Generation failed"}), 500

        database.update_post(
            pid,
            status="READY",
            content_html=result["content_html"],
            excerpt=result["excerpt"],
            seo_title=result["seo_title"],
            meta_description=result["meta_description"],
            focus_keyword=result["focus_keyword"],
            secondary_keywords=result["secondary_keywords"],
            word_count=result["word_count"],
            seo_score=result["seo_score"],
            error="",
        )
        return jsonify({"ok": True, "seo_score": result["seo_score"],
                        "word_count": result["word_count"]})
    except Exception as e:
        log.exception(f"Post generation failed {pid}")
        database.update_post(pid, status="FAILED", error=str(e)[:200])
        return jsonify({"ok": False, "error": str(e)[:200]}), 500


@bp.route("/api/posts/generate-all", methods=["POST"])
def generate_all():
    pending = database.get_all_posts("PENDING")
    if not pending:
        return jsonify({"ok": True, "processed": 0, "message": "No pending posts"})

    ok = 0
    failed = 0
    for p in pending:
        r = generate_post(p["id"])
        j = r[0].get_json() if isinstance(r, tuple) else r.get_json()
        if j.get("ok"):
            ok += 1
        else:
            failed += 1
    return jsonify({"ok": True, "processed": ok, "failed": failed})

@bp.route("/api/posts/delete/<int:pid>", methods=["POST"])
def delete_post(pid):
    database.delete_post(pid)
    return jsonify({"ok": True})


@bp.route("/api/posts/clear", methods=["POST"])
def clear():
    database.clear_posts()
    return jsonify({"ok": True})


@bp.route("/api/posts/dedup-check", methods=["POST"])
def dedup():
    from services import duplicate_service
    posts = database.get_all_posts()
    items = [{"id": p["id"], "product_content": p.get("content_html") or ""}
             for p in posts if p.get("content_html")]
    results = duplicate_service.check_duplicates(items, "product_content")
    for r in results:
        database.update_post(r["id"], duplicate_score=r["max_similarity"])
    return jsonify({"ok": True, "checked": len(results)})