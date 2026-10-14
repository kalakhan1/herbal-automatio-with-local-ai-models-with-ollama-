"""Image Manager routes."""
import logging
from flask import Blueprint, render_template, request, jsonify, send_file, abort
from pathlib import Path
from config import Config
from services import image_service
import database

bp = Blueprint("images", __name__)
log = logging.getLogger(__name__)

PAGE_SIZE = 20

@bp.route("/images")
def page():
    return render_template("images.html", active="images")

@bp.route("/api/images/list")
def list_images():
    page_num = max(1, int(request.args.get("page", 1)))
    status = request.args.get("status", "all")  # all | missing | assigned
    products = database.get_all_products()

    # Build flat list: each product has 2 slots
    slots = []
    for p in products:
        slots.append({
            "id": p["id"],
            "name": p["name"],
            "slug": p["slug"],
            "kind": "product",
            "image": p.get("product_image"),
            "alt": p.get("product_image_alt"),
        })
        slots.append({
            "id": p["id"],
            "name": p["name"],
            "slug": p["slug"],
            "kind": "blog",
            "image": p.get("blog_image"),
            "alt": p.get("blog_image_alt"),
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
    page_items = slots[start:end]

    return jsonify({
        "page": page_num,
        "total_pages": total_pages,
        "total_slots": total,
        "page_size": PAGE_SIZE,
        "items": page_items,
    })

@bp.route("/api/images/stats")
def stats():
    products = database.get_all_products()
    total = len(products) * 2
    p_img = sum(1 for p in products if p.get("product_image"))
    b_img = sum(1 for p in products if p.get("blog_image"))
    return jsonify({
        "total_slots": total,
        "assigned": p_img + b_img,
        "missing": total - (p_img + b_img),
        "product_assigned": p_img,
        "blog_assigned": b_img,
        "products_total": len(products),
    })

@bp.route("/api/images/upload/<int:pid>/<kind>", methods=["POST"])
def upload(pid, kind):
    if kind not in ("product", "blog"):
        return jsonify({"ok": False, "error": "Invalid kind"}), 400
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "error": "Empty filename"}), 400

    p = database.get_product(pid)
    if not p:
        return jsonify({"ok": False, "error": "Product not found"}), 404

    target_dir = Config.PRODUCT_IMG_DIR if kind == "product" else Config.BLOG_IMG_DIR
    file_bytes = f.read()

    result = image_service.process_upload(
        file_bytes, f.filename, p["name"], p["slug"], kind, target_dir
    )
    if not result.get("ok"):
        return jsonify(result), 400

    # Update DB
    if kind == "product":
        database.update_product(
            pid,
            product_image=result["filename"],
            product_image_alt=result["alt"],
        )
    else:
        database.update_product(
            pid,
            blog_image=result["filename"],
            blog_image_alt=result["alt"],
        )

    return jsonify({"ok": True, **result})

@bp.route("/api/images/remove/<int:pid>/<kind>", methods=["POST"])
def remove(pid, kind):
    if kind not in ("product", "blog"):
        return jsonify({"ok": False, "error": "Invalid kind"}), 400
    p = database.get_product(pid)
    if not p:
        return jsonify({"ok": False, "error": "Not found"}), 404

    filename = p.get("product_image") if kind == "product" else p.get("blog_image")
    if filename:
        image_service.delete_image(filename, kind)

    if kind == "product":
        database.update_product(pid, product_image="", product_image_alt="")
    else:
        database.update_product(pid, blog_image="", blog_image_alt="")

    return jsonify({"ok": True})

@bp.route("/api/images/preview/<int:pid>/<kind>")
def preview(pid, kind):
    p = database.get_product(pid)
    if not p:
        abort(404)
    filename = p.get("product_image") if kind == "product" else p.get("blog_image")
    if not filename:
        abort(404)
    target_dir = Config.PRODUCT_IMG_DIR if kind == "product" else Config.BLOG_IMG_DIR
    pth = target_dir / filename
    if not pth.exists():
        abort(404)
    return send_file(str(pth), mimetype="image/webp")

@bp.route("/api/images/search-term/<int:pid>/<kind>")
def search_term(pid, kind):
    """Return suggested search term for image search."""
    p = database.get_product(pid)
    if not p:
        return jsonify({"ok": False, "error": "Not found"}), 404
    name = p["name"]
    if kind == "product":
        term = f"{name} product"
    else:
        term = f"{name} benefits uses"
    return jsonify({"ok": True, "term": term})

@bp.route("/api/images/manifest", methods=["POST"])
def manifest():
    from services import csv_service
    products = database.get_all_products()
    path = csv_service.export_image_manifest(products)
    return jsonify({"ok": True, "path": str(path)})

@bp.route("/api/images/zip", methods=["POST"])
def create_zip():
    from services import zip_service
    products = database.get_all_products()
    result = zip_service.create_media_zip(products)
    if result.get("ok"):
        filename = Path(result["path"]).name
        result["download_url"] = f"/download/{filename}"
    return jsonify(result)