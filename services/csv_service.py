"""CSV generation for WooCommerce products and WordPress blogs."""
import csv
import logging
from pathlib import Path
from typing import List, Dict
from config import Config

log = logging.getLogger(__name__)

PRODUCT_COLUMNS = [
    "ID", "Type", "SKU", "Name", "Published", "Visibility in catalog",
    "Short description", "Description", "In stock?", "Stock status",
    "Regular price", "Categories", "Tags", "Images", "Position",
    "Attribute 1 name", "Attribute 1 value(s)",
    "Slug",
    "Meta: rank_math_focus_keyword",
    "Meta: rank_math_title",
    "Meta: rank_math_description",
]

BLOG_COLUMNS = [
    "post_title", "post_name", "post_content", "post_excerpt",
    "post_status", "post_type", "post_author",
    "post_category", "post_tags",
    "Images",
    "Meta: rank_math_focus_keyword",
    "Meta: rank_math_title",
    "Meta: rank_math_description",
]

def export_products(products: List[Dict], filename: str, include_images: bool = False) -> Path:
    out = Config.OUTPUT_DIR / filename
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRODUCT_COLUMNS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for p in products:
            w.writerow({
                "ID": p["id"],
                "Type": "simple",
                "SKU": p.get("sku", ""),
                "Name": p.get("product_title") or p.get("name", ""),
                "Published": 1,
                "Visibility in catalog": "visible",
                "Short description": p.get("product_excerpt", ""),
                "Description": p.get("product_content", ""),
                "In stock?": 1,
                "Stock status": "instock",
                "Regular price": "",
                "Categories": "Herbal Products",
                "Tags": "herbal, pakistan",
                "Images": p.get("product_image", "") if include_images else "",
                "Position": p["id"],
                "Attribute 1 name": "",
                "Attribute 1 value(s)": "",
                "Slug": p.get("slug", ""),
                "Meta: rank_math_focus_keyword": p.get("focus_keyword", ""),
                "Meta: rank_math_title": p.get("seo_title", ""),
                "Meta: rank_math_description": p.get("meta_description", ""),
            })
    log.info(f"Exported {len(products)} products to {out}")
    return out

def export_blogs(products: List[Dict], filename: str, include_images: bool = False) -> Path:
    out = Config.OUTPUT_DIR / filename
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BLOG_COLUMNS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for p in products:
            if not p.get("blog_content"):
                continue
            w.writerow({
                "post_title": p.get("blog_title") or f"{p.get('name')} Guide",
                "post_name": p.get("blog_slug") or (p.get("slug", "") + "-guide"),
                "post_content": p.get("blog_content", ""),
                "post_excerpt": p.get("blog_excerpt", ""),
                "post_status": "draft",
                "post_type": "post",
                "post_author": 1,
                "post_category": "Herbal Guides",
                "post_tags": "herbal, unani, pakistan",
                "Images": p.get("blog_image", "") if include_images else "",
                "Meta: rank_math_focus_keyword": p.get("focus_keyword", ""),
                "Meta: rank_math_title": p.get("seo_title", ""),
                "Meta: rank_math_description": p.get("meta_description", ""),
            })
    log.info(f"Exported blogs for {len(products)} products to {out}")
    return out

def export_image_manifest(products: List[Dict], filename: str = "image_manifest.csv") -> Path:
    out = Config.OUTPUT_DIR / filename
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["name", "type", "filename", "alt", "status"])
        for p in products:
            slug = p.get("slug", "")
            w.writerow([p.get("name", ""), "product",
                        f"{slug}-product.webp" if slug else "",
                        f"{p.get('name')} product image",
                        "assigned" if p.get("product_image") else "missing"])
            w.writerow([p.get("name", ""), "blog",
                        f"{slug}-blog.webp" if slug else "",
                        f"{p.get('blog_title')} image",
                        "assigned" if p.get("blog_image") else "missing"])
    return out