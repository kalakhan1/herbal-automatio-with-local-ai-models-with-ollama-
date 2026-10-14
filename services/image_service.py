"""Image handling: WebP conversion, SEO metadata, storage."""
import logging
import re
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple
from PIL import Image
from config import Config

log = logging.getLogger(__name__)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
MAX_SIZE_MB = 15

def sanitize_filename(name: str) -> str:
    """Remove dangerous characters."""
    name = (name or "").strip()
    name = re.sub(r'[^\w\s\-\.]', '', name)
    name = re.sub(r'\s+', '-', name)
    return name.lower().strip('-.')

def detect_extension(filename: str) -> str:
    return Path(filename).suffix.lower()

def validate_file(filename: str, size_bytes: int) -> Tuple[bool, str]:
    ext = detect_extension(filename)
    if ext not in ALLOWED_EXT:
        return False, f"Unsupported format: {ext}"
    if size_bytes > MAX_SIZE_MB * 1024 * 1024:
        return False, f"File too large (max {MAX_SIZE_MB} MB)"
    return True, ""

def convert_to_webp(src_path: Path, dst_path: Path, quality: int = 88,
                    max_width: int = 1200) -> bool:
    """Convert any image to WebP. Preserves aspect ratio, resizes if too large."""
    try:
        img = Image.open(src_path)
        # Handle EXIF orientation
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convert mode
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        # Resize if too large
        w, h = img.size
        if w > max_width:
            ratio = max_width / w
            new_size = (max_width, int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Save
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst_path, "WEBP", quality=quality, method=6, optimize=True)
        log.info(f"Converted {src_path.name} → {dst_path.name}")
        return True
    except Exception as e:
        log.error(f"WebP conversion failed for {src_path}: {e}")
        return False

def generate_seo_metadata(product_name: str, slug: str, kind: str = "product") -> Dict:
    """Generate SEO filename + alt + title + description for an image."""
    base = sanitize_filename(f"{slug}-{kind}")
    if kind == "product":
        alt = f"{product_name} product image"
        title = product_name
        description = f"Product image of {product_name} available at our store"
    else:
        alt = f"{product_name} guide image"
        title = f"{product_name} Guide"
        description = f"Informational image for the {product_name} guide article"
    return {
        "filename": f"{base}.webp",
        "alt": alt,
        "title": title,
        "description": description,
    }

def process_upload(file_bytes: bytes, original_name: str,
                   product_name: str, slug: str, kind: str,
                   target_dir: Path) -> Dict:
    """
    Full pipeline: validate, save original, convert to WebP.
    Returns {ok, filename, alt, title, description, error}
    """
    ok, err = validate_file(original_name, len(file_bytes))
    if not ok:
        return {"ok": False, "error": err}

    # Save original for safety
    meta = generate_seo_metadata(product_name, slug, kind)
    original_path = target_dir / f"_{meta['filename'].rsplit('.', 1)[0]}{detect_extension(original_name)}"
    target_dir.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(file_bytes)

    # Convert
    dst = target_dir / meta["filename"]
    if not convert_to_webp(original_path, dst):
        return {"ok": False, "error": "WebP conversion failed"}

    return {
        "ok": True,
        "filename": meta["filename"],
        "alt": meta["alt"],
        "title": meta["title"],
        "description": meta["description"],
        "size_bytes": dst.stat().st_size,
    }

def delete_image(filename: str, kind: str = "product") -> bool:
    """Delete image from storage."""
    target_dir = Config.PRODUCT_IMG_DIR if kind == "product" else Config.BLOG_IMG_DIR
    p = target_dir / filename
    if p.exists():
        try:
            p.unlink()
            return True
        except Exception as e:
            log.error(f"Delete failed {p}: {e}")
    return False

def image_path(filename: str, kind: str = "product") -> Path:
    target_dir = Config.PRODUCT_IMG_DIR if kind == "product" else Config.BLOG_IMG_DIR
    return target_dir / filename