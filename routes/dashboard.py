from flask import Blueprint, jsonify, render_template
import database

bp = Blueprint("dashboard", __name__)

@bp.route("/")
def index():
    return render_template("dashboard.html", active="dashboard")

@bp.route("/api/stats")
def api_stats():
    return jsonify(database.get_stats())