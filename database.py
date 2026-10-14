"""SQLite database with schema and helpers."""
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from config import Config

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    sku TEXT UNIQUE,
    status TEXT DEFAULT 'PENDING',
    product_title TEXT,
    product_content TEXT,
    product_excerpt TEXT,
    blog_title TEXT,
    blog_content TEXT,
    blog_excerpt TEXT,
    blog_slug TEXT,
    seo_title TEXT,
    meta_description TEXT,
    focus_keyword TEXT,
    secondary_keywords TEXT,
    product_image TEXT,
    blog_image TEXT,
    product_image_alt TEXT,
    blog_image_alt TEXT,
    product_word_count INTEGER DEFAULT 0,
    blog_word_count INTEGER DEFAULT 0,
    seo_score INTEGER DEFAULT 0,
    duplicate_score REAL DEFAULT 0,
    wp_post_id INTEGER,
    wp_product_url TEXT,
    error TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    source_content TEXT,
    content_html TEXT,
    excerpt TEXT,
    seo_title TEXT,
    meta_description TEXT,
    focus_keyword TEXT,
    secondary_keywords TEXT,
    word_count INTEGER DEFAULT 0,
    seo_score INTEGER DEFAULT 0,
    duplicate_score REAL DEFAULT 0,
    image TEXT,
    image_alt TEXT,
    wp_post_id INTEGER,
    status TEXT DEFAULT 'PENDING',
    error TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT,
    message TEXT,
    context TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug);
"""


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migrations for products
        existing = [r[1] for r in conn.execute("PRAGMA table_info(products)").fetchall()]
        migrations = {
            "product_image": "TEXT", "blog_image": "TEXT",
            "product_image_alt": "TEXT", "blog_image_alt": "TEXT",
            "wp_post_id": "INTEGER", "wp_product_url": "TEXT",
        }
        for col, typ in migrations.items():
            if col not in existing:
                try:
                    conn.execute(f"ALTER TABLE products ADD COLUMN {col} {typ}")
                except Exception as e:
                    log.warning(f"Migration failed {col}: {e}")
    log.info("Database initialized")


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(Config.DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


# ==================== PRODUCTS ====================
def insert_product(name: str, slug: str, sku: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO products (name, slug, sku, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'PENDING', ?, ?)",
            (name, slug, sku, now_iso(), now_iso())
        )
        return cur.lastrowid or 0


def get_product(pid: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        return dict(row) if row else None


def get_all_products(status: Optional[str] = None) -> List[Dict]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM products WHERE status = ? ORDER BY id", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def update_product(pid: int, **fields):
    if not fields:
        return
    fields["updated_at"] = now_iso()
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [pid]
    with get_conn() as conn:
        conn.execute(f"UPDATE products SET {cols} WHERE id = ?", vals)


def delete_product(pid: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (pid,))


def clear_products():
    with get_conn() as conn:
        conn.execute("DELETE FROM products")


def get_stats() -> Dict[str, Any]:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        stats = {"total": total}
        for status in ["PENDING", "GENERATING", "READY", "FAILED"]:
            stats[status.lower()] = conn.execute(
                "SELECT COUNT(*) FROM products WHERE status = ?", (status,)
            ).fetchone()[0]
        stats["with_product"] = conn.execute(
            "SELECT COUNT(*) FROM products WHERE product_content IS NOT NULL "
            "AND LENGTH(product_content) > 100"
        ).fetchone()[0]
        stats["with_blog"] = conn.execute(
            "SELECT COUNT(*) FROM products WHERE blog_content IS NOT NULL "
            "AND LENGTH(blog_content) > 100"
        ).fetchone()[0]
        stats["with_product_img"] = conn.execute(
            "SELECT COUNT(*) FROM products WHERE product_image IS NOT NULL AND product_image != ''"
        ).fetchone()[0]
        stats["with_blog_img"] = conn.execute(
            "SELECT COUNT(*) FROM products WHERE blog_image IS NOT NULL AND blog_image != ''"
        ).fetchone()[0]
        stats["seo_pass"] = conn.execute(
            "SELECT COUNT(*) FROM products WHERE seo_score >= 70"
        ).fetchone()[0]
        stats["seo_fail"] = conn.execute(
            "SELECT COUNT(*) FROM products WHERE seo_score > 0 AND seo_score < 70"
        ).fetchone()[0]
        stats["dup_fail"] = conn.execute(
            "SELECT COUNT(*) FROM products WHERE duplicate_score >= ?",
            (Config.SIMILARITY_THRESHOLD,)
        ).fetchone()[0]

        # Posts stats
        stats["posts_total"] = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        stats["posts_ready"] = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE status = 'READY'"
        ).fetchone()[0]
        stats["posts_with_image"] = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE image IS NOT NULL AND image != ''"
        ).fetchone()[0]
        return stats


# ==================== POSTS ====================
def insert_post(title: str, slug: str, source_content: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO posts (title, slug, source_content, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'PENDING', ?, ?)",
            (title, slug, source_content, now_iso(), now_iso())
        )
        return cur.lastrowid or 0


def get_post(pid: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
        return dict(row) if row else None


def get_post_by_slug(slug: str) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM posts WHERE slug = ?", (slug,)).fetchone()
        return dict(row) if row else None


def get_all_posts(status: Optional[str] = None) -> List[Dict]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM posts WHERE status = ? ORDER BY id", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM posts ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def update_post(pid: int, **fields):
    if not fields:
        return
    fields["updated_at"] = now_iso()
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [pid]
    with get_conn() as conn:
        conn.execute(f"UPDATE posts SET {cols} WHERE id = ?", vals)


def delete_post(pid: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM posts WHERE id = ?", (pid,))


def clear_posts():
    with get_conn() as conn:
        conn.execute("DELETE FROM posts")


# ==================== LOGS ====================
def add_log(level: str, message: str, context: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO logs (level, message, context, created_at) VALUES (?, ?, ?, ?)",
            (level, message, context, now_iso())
        )


def get_logs(limit: int = 200) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )


def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default