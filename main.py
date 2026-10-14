"""Herbal Content Automation System — Main Flask app."""
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from config import Config
import database


def setup_logging():
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    app_handler = RotatingFileHandler(
        Config.LOGS_DIR / "app.log", maxBytes=5_000_000, backupCount=3,
        encoding="utf-8"
    )
    app_handler.setFormatter(fmt)
    root.addHandler(app_handler)

    err_handler = RotatingFileHandler(
        Config.LOGS_DIR / "errors.log", maxBytes=5_000_000, backupCount=3,
        encoding="utf-8"
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(fmt)
    root.addHandler(err_handler)


setup_logging()
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY

database.init_db()

# Register blueprints
from routes import dashboard, products, settings as settings_route, logs, export
from routes import images, wordpress
from routes import posts, post_images

app.register_blueprint(dashboard.bp)
app.register_blueprint(products.bp)
app.register_blueprint(settings_route.bp)
app.register_blueprint(logs.bp)
app.register_blueprint(export.bp)
app.register_blueprint(images.bp)
app.register_blueprint(wordpress.bp)
app.register_blueprint(posts.bp)
app.register_blueprint(post_images.bp)


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("Herbal Content Automation System — Phase 3")
    log.info(f"Open: http://127.0.0.1:{Config.FLASK_PORT}")
    log.info(f"AI provider: Ollama | model: {Config.OLLAMA_MODEL}")
    log.info(f"Test mode: {Config.TEST_MODE}")
    log.info("=" * 60)
    app.run(host="127.0.0.1", port=Config.FLASK_PORT, debug=False, threaded=True)
