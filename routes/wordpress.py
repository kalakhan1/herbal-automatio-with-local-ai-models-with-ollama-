"""WordPress integration routes."""
import logging
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify
from config import Config
from services import wordpress_service
import database

bp = Blueprint("wordpress", __name__)
log = logging.getLogger(__name__)

@bp.route("/wordpress")
def page():
    return render_template("wordpress.html", active="wordpress")

@bp.route("/api/wp/test", methods=["POST"])
def test_conn():
    return jsonify(wordpress_service.test_connection())

@bp.route("/api/wp/upload-images", methods=["POST"])
def upload_images():
    """Upload all assigned images to WordPress media library."""
    data = request.get_json(force=True) or {}
    limit = int(data.get("limit", 20))
    products = database.get_all_products()
    uploaded = 0
    failed = []

    for p in products[:limit]:
        # Product image
        if p.get("product_image"):
            fpath = Config.PRODUCT_IMG_DIR / p["product_image"]
            ok, res = wordpress_service.upload_media(
                fpath,
                alt_text=p.get("product_image_alt", ""),
                title=f"{p['name']} - Product",
                description=f"Product image for {p['name']}",
            )
            if ok:
                uploaded += 1
            else:
                failed.append({"id": p["id"], "kind": "product",
                               "error": res.get("error", "")[:100]})

        # Blog image
        if p.get("blog_image"):
            fpath = Config.BLOG_IMG_DIR / p["blog_image"]
            ok, res = wordpress_service.upload_media(
                fpath,
                alt_text=p.get("blog_image_alt", ""),
                title=f"{p['name']} - Guide",
                description=f"Guide image for {p['name']}",
            )
            if ok:
                uploaded += 1
            else:
                failed.append({"id": p["id"], "kind": "blog",
                               "error": res.get("error", "")[:100]})

    return jsonify({"ok": True, "uploaded": uploaded,
                    "failed_count": len(failed),
                    "failed": failed[:10]})

@bp.route("/api/wp/create-drafts", methods=["POST"])
def create_drafts():
    """Create blog drafts for products that have blog content."""
    data = request.get_json(force=True) or {}
    limit = int(data.get("limit", 5))
    dry_run = bool(data.get("dry_run", False))

    products = database.get_all_products()
    created = 0
    updated = 0
    failed = []
    previews = []

    for p in products:
        if not p.get("blog_content"):
            continue
        if created + updated >= limit:
            break

        slug = p.get("blog_slug") or (p.get("slug", "") + "-guide")
        title = p.get("blog_title") or f"{p['name']} Guide"

        if dry_run:
            previews.append({"id": p["id"], "title": title, "slug": slug,
                             "action": "would_create"})
            continue

        existing = wordpress_service.find_post_by_slug(slug)
        if existing:
            ok, res = wordpress_service.update_blog_post(
                existing["id"],
                title=title,
                content=p["blog_content"],
                excerpt=p.get("blog_excerpt", ""),
            )
            if ok:
                updated += 1
            else:
                failed.append({"id": p["id"], "error": res.get("error", "")[:100]})
        else:
            ok, res = wordpress_service.create_blog_draft(
                title=title,
                content=p["blog_content"],
                excerpt=p.get("blog_excerpt", ""),
                slug=slug,
            )
            if ok:
                created += 1
            else:
                failed.append({"id": p["id"], "error": res.get("error", "")[:100]})

    return jsonify({
        "ok": True,
        "created": created,
        "updated": updated,
        "failed_count": len(failed),
        "failed": failed[:10],
        "previews": previews[:10],
        "dry_run": dry_run,
    })