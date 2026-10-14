"""Post image manager — reuses image_service with kind='post'."""
import logging
from flask import Blueprint, render_template, request, jsonify, send_file, abort
from pathlib import Path
from config import Config
from services import image_service
import database

bp = Blueprint("post_images", __name__)
log = logging.getLogger(__name__)

PAGE_SIZE = 20


@bp.route("/post-images")
def page():
    return render_template("post_images.html", active="post_images")


@bp.route("/api/post-images/list")
def list_images():
    page_num = max(1, int(request.args.get("page", 1)))
    status = request.args.get("status", "all")
    posts = database.get_all_posts()

    slots = []
    for p in posts:
        slots.append({
            "id": p["id"],
            "title": p["title"],
            "slug": p["slug"],
            "image": p.get("image"),
            "alt": p.get("image_alt"),
        })

    if status == "missing":
        slots = [s for s in slots if not s["image"]]
    elif status == "assigned":
        slots = [s for s in slots if s["image"]]

    total = len(slots)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page_num = min(page_num, total_pages)
    start = (page_num - 1) * PAGE_SIZE
    end = start + PAGE_SIZE

    return jsonify({
        "page": page_num,
        "total_pages": total_pages,
        "total_slots": total,
        "items": slots[start:end],
    })


@bp.route("/api/post-images/stats")
def stats():
    posts = database.get_all_posts()
    total = len(posts)
    assigned = sum(1 for p in posts if p.get("image"))
    return jsonify({
        "total_slots": total,
        "assigned": assigned,
        "missing": total - assigned,
    })


@bp.route("/api/post-images/upload/<int:pid>", methods=["POST"])
def upload(pid):
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "error": "Empty filename"}), 400

    p = database.get_post(pid)
    if not p:
        return jsonify({"ok": False, "error": "Post not found"}), 404

    result = image_service.process_upload(
        f.read(), f.filename, p["title"], p["slug"], "blog", Config.BLOG_IMG_DIR
    )
    if not result.get("ok"):
        return jsonify(result), 400

    database.update_post(pid, image=result["filename"], image_alt=result["alt"])
    return jsonify({"ok": True, **result})


@bp.route("/api/post-images/remove/<int:pid>", methods=["POST"])
def remove(pid):
    p = database.get_post(pid)
    if not p:
        return jsonify({"ok": False, "error": "Not found"}), 404
    if p.get("image"):
        image_service.delete_image(p["image"], "blog")
    database.update_post(pid, image="", image_alt="")
    return jsonify({"ok": True})


@bp.route("/api/post-images/preview/<int:pid>")
def preview(pid):
    p = database.get_post(pid)
    if not p:
        abort(404)
    fname = p.get("image")
    if not fname:
        abort(404)
    pth = Config.BLOG_IMG_DIR / fname
    if not pth.exists():
        abort(404)
    return send_file(str(pth), mimetype="image/webp")


@bp.route("/api/post-images/search-term/<int:pid>")
def search_term(pid):
    p = database.get_post(pid)
    if not p:
        return jsonify({"ok": False, "error": "Not found"}), 404
    term = f"{p['title']} blog illustration"
    return jsonify({"ok": True, "term": term})