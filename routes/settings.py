from flask import Blueprint, render_template, request, jsonify
import os
from config import Config, BASE_DIR
from services import ollama_service

bp = Blueprint("settings", __name__)

@bp.route("/settings")
def page():
    return render_template("settings.html", active="settings",
                           config=Config, base_dir=str(BASE_DIR))

@bp.route("/api/settings/test-ollama", methods=["POST"])
def test_ollama():
    return jsonify(ollama_service.check_connection())

@bp.route("/api/settings/save", methods=["POST"])
def save():
    data = request.get_json(force=True) or {}
    env_path = BASE_DIR / ".env"
    # Read existing
    existing = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    existing.update(data)
    # Write back
    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    return jsonify({"ok": True, "message": "Saved. Restart app to apply."})