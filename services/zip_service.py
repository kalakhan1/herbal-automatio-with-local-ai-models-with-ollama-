"""ZIP export for media files."""
import logging
import zipfile
from pathlib import Path
from typing import List, Dict
from config import Config

log = logging.getLogger(__name__)

def create_media_zip(products: List[Dict],
                     output_name: str = "herbal_media.zip") -> Dict:
    """
    Create ZIP containing all product + blog images.
    Returns {ok, path, file_count, size_bytes}
    """
    out_path = Config.OUTPUT_DIR / output_name
    files_added = 0
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in products:
                # Product image
                if p.get("product_image"):
                    src = Config.PRODUCT_IMG_DIR / p["product_image"]
                    if src.exists():
                        z.write(src, f"products/{p['product_image']}")
                        files_added += 1
                # Blog image
                if p.get("blog_image"):
                    src = Config.BLOG_IMG_DIR / p["blog_image"]
                    if src.exists():
                        z.write(src, f"blogs/{p['blog_image']}")
                        files_added += 1

        size = out_path.stat().st_size
        log.info(f"Created ZIP: {out_path} ({files_added} files, {size} bytes)")
        return {"ok": True, "path": str(out_path),
                "file_count": files_added, "size_bytes": size}
    except Exception as e:
        log.exception("ZIP creation failed")
        return {"ok": False, "error": str(e), "path": ""}


def create_csv_zip(products: List[Dict],
                   output_name: str = "herbal_csv_backup.zip") -> Dict:
    """ZIP of all CSVs in output folder."""
    out_path = Config.OUTPUT_DIR / output_name
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            count = 0
            for csv_file in Config.OUTPUT_DIR.glob("*.csv"):
                if csv_file.name == output_name:
                    continue
                z.write(csv_file, csv_file.name)
                count += 1
        return {"ok": True, "path": str(out_path), "file_count": count}
    except Exception as e:
        return {"ok": False, "error": str(e)}