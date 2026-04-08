#!/usr/bin/env python3

import argparse
import base64
from datetime import datetime
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def run_osascript(lines):
    cmd = ["osascript"]
    for line in lines:
        cmd.extend(["-e", line])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "osascript failed")
    return result.stdout.rstrip("\n")


def safari_eval(js):
    return run_osascript([
        'tell application "Safari"',
        f"return do JavaScript {json.dumps(js)} in front document",
        "end tell",
    ])


def safari_get_title():
    return run_osascript([
        'tell application "Safari"',
        "return name of front document",
        "end tell",
    ])


def safe_stem(text):
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r'[\\\\/:*?\"<>|]+', "-", text)
    text = re.sub(r"-{2,}", "-", text).strip(" .-")
    return text or "未命名课程"


def capture_timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def image_candidates():
    js = """
(() => {
  try {
    const textOf = (node) => {
      if (!node) return "";
      const text = (node.innerText || node.textContent || "").replace(/\\s+/g, " ").trim();
      return text.slice(0, 240);
    };
    const nodes = [...document.images].map((img, index) => {
      const rect = img.getBoundingClientRect();
      const src = img.currentSrc || img.src || "";
      const parent = img.parentElement;
      const previous = parent?.previousElementSibling || img.previousElementSibling;
      const next = parent?.nextElementSibling || img.nextElementSibling;
      return {
        index,
        src,
        alt: (img.alt || "").trim(),
        width: Math.round(rect.width || 0),
        height: Math.round(rect.height || 0),
        naturalWidth: img.naturalWidth || 0,
        naturalHeight: img.naturalHeight || 0,
        area: Math.round((rect.width || 0) * (rect.height || 0)),
        top: Math.round(rect.top || 0),
        parentText: textOf(parent),
        previousText: textOf(previous),
        nextText: textOf(next),
      };
    });
    return JSON.stringify(nodes);
  } catch (e) {
    return JSON.stringify([{ error: String(e) }]);
  }
})()
""".strip()
    raw = safari_eval(js)
    data = json.loads(raw)
    if data and isinstance(data, list) and "error" in data[0]:
        raise RuntimeError(data[0]["error"])
    return data


def page_scroll_state():
    js = """
(() => JSON.stringify({
  top: Math.round(window.scrollY || document.documentElement.scrollTop || 0),
  height: Math.round(window.innerHeight || document.documentElement.clientHeight || 0),
  scrollHeight: Math.round(
    Math.max(
      document.body ? document.body.scrollHeight : 0,
      document.documentElement ? document.documentElement.scrollHeight : 0
    )
  )
}))()
""".strip()
    return json.loads(safari_eval(js))


def scroll_page_once(pixels):
    js = f"""
(() => {{
  const before = Math.round(window.scrollY || document.documentElement.scrollTop || 0);
  window.scrollTo(0, before + {int(pixels)});
  const after = Math.round(window.scrollY || document.documentElement.scrollTop || 0);
  return JSON.stringify({{ before, after }});
}})()
""".strip()
    return json.loads(safari_eval(js))


def collect_all_image_candidates(max_steps=80, pause_seconds=0.35):
    import time

    collected = {}

    def merge(items):
        for item in items:
            src = (item.get("src") or "").strip()
            if not src:
                continue
            existing = collected.get(src)
            if not existing or int(item.get("area") or 0) > int(existing.get("area") or 0):
                collected[src] = item

    state = page_scroll_state()
    start_top = int(state.get("top") or 0)
    merge(image_candidates())

    repeated = 0
    for _ in range(max_steps):
        state = page_scroll_state()
        top = int(state.get("top") or 0)
        height = max(int(state.get("height") or 0), 1)
        scroll_height = max(int(state.get("scrollHeight") or 0), 1)
        if top + height >= scroll_height - 4:
            break
        move = scroll_page_once(max(int(height * 0.85), 500))
        time.sleep(pause_seconds)
        merge(image_candidates())
        if int(move.get("after") or 0) == int(move.get("before") or 0):
            repeated += 1
            if repeated >= 2:
                break
        else:
            repeated = 0

    safari_eval(f"window.scrollTo(0, {start_top}); 'ok';")
    return list(collected.values())


POSITIVE_KEYWORDS = [
    "小抄",
    "清单",
    "路线图",
    "模型",
    "方法",
    "框架",
    "表格",
    "公式",
    "原则",
    "维度",
    "三要素",
    "五步法",
    "关键假设",
    "画布",
    "拆解",
]

NEGATIVE_KEYWORDS = [
    "开始上课",
    "快速回顾",
    "为什么要学",
    "作业和课后candy",
    "作业与candy",
    "完成作业的奖励",
    "敲黑板，说重点",
]


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def keyword_score(text):
    score = 0
    normalized = normalize_text(text)
    for keyword in POSITIVE_KEYWORDS:
        if keyword.lower() in normalized:
            score += 3
    for keyword in NEGATIVE_KEYWORDS:
        if keyword.lower() in normalized:
            score -= 4
    return score


def combined_context(item):
    parts = [
        item.get("alt") or "",
        item.get("parentText") or "",
        item.get("previousText") or "",
        item.get("nextText") or "",
    ]
    return " ".join(part for part in parts if part).strip()


def likely_hero_or_title(item, context_text):
    width = int(item.get("width") or 0)
    height = int(item.get("height") or 0)
    top = int(item.get("top") or 0)
    if height <= 0:
        return False
    aspect = width / max(height, 1)
    has_positive = keyword_score(context_text) > 0
    return top < 1800 and aspect > 1.8 and not has_positive


def likely_non_explanatory_photo(item, context_text):
    width = int(item.get("width") or 0)
    height = int(item.get("height") or 0)
    if height <= 0:
        return False
    aspect = width / max(height, 1)
    return keyword_score(context_text) <= 0 and aspect > 1.8


def likely_decorative_or_banner(item, context_text):
    width = int(item.get("width") or 0)
    height = int(item.get("height") or 0)
    area = int(item.get("area") or 0)
    if width <= 0 or height <= 0:
        return False
    aspect = width / max(height, 1)
    normalized = normalize_text(context_text)
    has_context = bool(normalized)
    if width <= 260 and height <= 260 and area < 80000:
        return True
    if not has_context and aspect > 1.6 and height < 700:
        return True
    return False


def rank_image_candidates(candidates):
    primary = []
    fallback = []
    seen = set()
    for item in candidates:
        src = (item.get("src") or "").strip()
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        area = int(item.get("area") or 0)
        if not src or src in seen:
            continue
        if width < 140 or height < 140:
            continue
        if area < 40000:
            continue
        context_text = combined_context(item)
        if likely_hero_or_title(item, context_text):
            continue
        if likely_non_explanatory_photo(item, context_text):
            continue
        if likely_decorative_or_banner(item, context_text):
            continue
        score = area / 50000
        score += keyword_score(context_text)
        if width >= 600 and height >= 400:
            score += 1
        if int(item.get("naturalWidth") or 0) >= 1200:
            score += 1
        item = dict(item)
        item["contextText"] = context_text
        item["score"] = round(score, 2)
        if keyword_score(context_text) > 0:
            primary.append(item)
        else:
            fallback.append(item)
    sorter = lambda x: (-float(x.get("score") or 0), int(x.get("top") or 0), int(x.get("index") or 0))
    return sorted(primary, key=sorter), sorted(fallback, key=sorter)


def select_core_images(candidates, limit, min_count=0):
    selected = []
    seen = set()
    primary, fallback = rank_image_candidates(candidates)

    for item in primary:
        src = (item.get("src") or "").strip()
        seen.add(src)
        selected.append(item)
        if limit and len(selected) >= limit:
            return selected

    if min_count and len(selected) < min_count:
        for item in fallback:
            src = (item.get("src") or "").strip()
            if src in seen:
                continue
            seen.add(src)
            selected.append(item)
            if limit and len(selected) >= limit:
                return selected
            if len(selected) >= min_count:
                return selected

    if limit:
        selected = selected[:limit]
    return selected


def suffix_from_content_type(content_type, fallback=".bin"):
    content_type = (content_type or "").split(";")[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
    }
    return mapping.get(content_type, fallback)


def suffix_from_url(url, fallback=".png"):
    parsed = urllib.parse.urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
        return suffix
    return fallback


def save_data_url(src, path_without_suffix):
    header, encoded = src.split(",", 1)
    is_base64 = ";base64" in header
    mime = header.split(":", 1)[1].split(";", 1)[0] if ":" in header else "image/png"
    suffix = suffix_from_content_type(mime, ".png")
    path = path_without_suffix.with_suffix(suffix)
    if is_base64:
        content = base64.b64decode(encoded)
    else:
        content = urllib.parse.unquote_to_bytes(encoded)
    path.write_bytes(content)
    return path


def download_http_image(src, path_without_suffix):
    request = urllib.request.Request(
        src,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": src,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        content = response.read()
        suffix = suffix_from_content_type(response.headers.get("Content-Type"), suffix_from_url(src))
    path = path_without_suffix.with_suffix(suffix)
    path.write_bytes(content)
    return path


def save_image(src, path_without_suffix):
    if src.startswith("data:image/"):
        return save_data_url(src, path_without_suffix)
    if src.startswith("http://") or src.startswith("https://"):
        return download_http_image(src, path_without_suffix)
    raise RuntimeError(f"unsupported_image_src: {src[:120]}")


def main():
    parser = argparse.ArgumentParser(description="Download core rendered images from the current Safari page.")
    parser.add_argument("--out-dir", required=True, help="Directory to save the extracted images")
    parser.add_argument("--prefix", help="Filename prefix, defaults to current page title")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of core images to save; 0 means no fixed limit")
    parser.add_argument("--min-count", type=int, default=3, help="Minimum number of images to save when enough valid images exist")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = safe_stem(args.prefix or safari_get_title())
    if args.prefix:
        file_prefix = prefix
    else:
        file_prefix = f"{prefix}-{capture_timestamp()}"

    selected = select_core_images(collect_all_image_candidates(), args.limit, min_count=max(args.min_count, 0))
    saved = []
    errors = []

    for index, item in enumerate(selected, start=1):
        base = out_dir / f"{file_prefix}-核心图片-{index:02d}"
        src = item.get("src") or ""
        try:
            path = save_image(src, base)
            saved.append(
                {
                    "path": str(path),
                    "src": src,
                    "alt": item.get("alt") or "",
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "area": item.get("area"),
                }
            )
        except (RuntimeError, ValueError, urllib.error.URLError, TimeoutError) as exc:
            errors.append(
                {
                    "src": src,
                    "error": str(exc),
                }
            )

    payload = {
        "title": prefix,
        "file_prefix": file_prefix,
        "min_count": args.min_count,
        "saved_images": saved,
        "errors": errors,
        "selected_count": len(selected),
        "saved_count": len(saved),
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
