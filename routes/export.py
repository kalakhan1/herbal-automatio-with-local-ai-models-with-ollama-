from flask import Blueprint, render_template, jsonify, send_file, abort
from pathlib import Path
import database
from services import csv_service
from config import Config

bp = Blueprint("export", __name__)

@bp.route("/export")
def page():
    return render_template("export.html", active="export")

@bp.route("/api/export/products-without-images", methods=["POST"])
def exp_p_without():
    products = database.get_all_products()
    path = csv_service.export_products(products, "products_without_images.csv", False)
    return jsonify({"ok": True, "path": str(path), "count": len(products)})

@bp.route("/api/export/products-with-images", methods=["POST"])
def exp_p_with():
    products = database.get_all_products()
    path = csv_service.export_products(products, "products_with_images.csv", True)
    return jsonify({"ok": True, "path": str(path), "count": len(products)})

@bp.route("/api/export/blogs-without-images", methods=["POST"])
def exp_b_without():
    products = database.get_all_products()
    path = csv_service.export_blogs(products, "blogs_without_images.csv", False)
    return jsonify({"ok": True, "path": str(path)})

@bp.route("/api/export/blogs-with-images", methods=["POST"])
def exp_b_with():
    products = database.get_all_products()
    path = csv_service.export_blogs(products, "blogs_with_images.csv", True)
    return jsonify({"ok": True, "path": str(path)})

@bp.route("/api/export/manifest", methods=["POST"])
def exp_manifest():
    products = database.get_all_products()
    path = csv_service.export_image_manifest(products)
    return jsonify({"ok": True, "path": str(path)})

@bp.route("/download/<path:filename>")
def download(filename):
    safe = Path(filename).name
    f = Config.OUTPUT_DIR / safe
    if not f.exists():
        abort(404)
    return send_file(str(f), as_attachment=True, download_name=safe)