from flask import Blueprint, render_template, jsonify
import database

bp = Blueprint("logs", __name__)

@bp.route("/logs")
def page():
    return render_template("logs.html", active="logs")

@bp.route("/api/logs")
def api_logs():
    return jsonify(database.get_logs(200))