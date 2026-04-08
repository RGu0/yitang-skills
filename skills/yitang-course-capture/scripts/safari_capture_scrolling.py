#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def run_osascript(lines):
    cmd = ["osascript"]
    for line in lines:
        cmd.extend(["-e", line])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "osascript failed")
    return result.stdout.rstrip("\n")


def safari_open(url):
    run_osascript([
        'tell application "Safari"',
        "activate",
        "if (count of windows) = 0 then",
        "make new document",
        "end if",
        f"set URL of front document to {json.dumps(url)}",
        "end tell",
    ])


def safari_eval(js):
    return run_osascript([
        'tell application "Safari"',
        f"return do JavaScript {json.dumps(js)} in front document",
        "end tell",
    ])


def safari_get_url():
    return run_osascript([
        'tell application "Safari"',
        "return URL of front document",
        "end tell",
    ])


def safari_get_title():
    return run_osascript([
        'tell application "Safari"',
        "return name of front document",
        "end tell",
    ])


def js_json(js):
    raw = safari_eval(js)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "non_json_js_result", "raw": raw}


def read_snapshot(scroll_selector=None, text_selector=None):
    scroll_expr = json.dumps(scroll_selector) if scroll_selector else "null"
    text_expr = json.dumps(text_selector) if text_selector else "null"
    js = f"""
(() => {{
  try {{
    const scrollSelector = {scroll_expr};
    const textSelector = {text_expr};
    const scroller = scrollSelector ? document.querySelector(scrollSelector) : document.scrollingElement;
    const textRoot = textSelector ? document.querySelector(textSelector) : document.body;
    const text = textRoot ? (textRoot.innerText || "") : "";
    const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
      .map(n => (n.innerText || "").trim())
      .filter(Boolean)
      .slice(0, 200);
    return JSON.stringify({{
      url: location.href || "",
      title: document.title || "",
      text,
      text_len: text.length,
      headings,
      scrollTop: scroller ? scroller.scrollTop : 0,
      scrollHeight: scroller ? scroller.scrollHeight : 0,
      clientHeight: scroller ? scroller.clientHeight : 0
    }});
  }} catch (e) {{
    return JSON.stringify({{ error: String(e) }});
  }}
}})()
""".strip()
    return js_json(js)


def scroll_once(scroll_selector=None, pixels=None):
    scroll_expr = json.dumps(scroll_selector) if scroll_selector else "null"
    pixels_expr = "null" if pixels is None else str(int(pixels))
    js = f"""
(() => {{
  const scrollSelector = {scroll_expr};
  const scroller = scrollSelector ? document.querySelector(scrollSelector) : document.scrollingElement;
  if (!scroller) return JSON.stringify({{ ok: false, reason: "no_scroller" }});
  const before = scroller.scrollTop;
  const step = {pixels_expr} === null ? Math.max(400, scroller.clientHeight - 120) : {pixels_expr};
  scroller.scrollTop = Math.min(scroller.scrollTop + step, Math.max(0, scroller.scrollHeight - scroller.clientHeight));
  return JSON.stringify({{
    ok: true,
    before,
    after: scroller.scrollTop,
    step,
    scrollHeight: scroller.scrollHeight,
    clientHeight: scroller.clientHeight
  }});
}})()
""".strip()
    return js_json(js)


def normalize_text(text):
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = []
    for line in lines:
        if not line.strip():
            if cleaned and cleaned[-1] == "":
                continue
            cleaned.append("")
        else:
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def merge_snapshots_text(snapshots):
    seen = set()
    merged = []
    for shot in snapshots:
        text = normalize_text(shot.get("text", ""))
        for line in text.splitlines():
            key = line.strip()
            if not key:
                if merged and merged[-1] != "":
                    merged.append("")
                continue
            if key in seen:
                continue
            seen.add(key)
            merged.append(line)
    return "\n".join(merged).strip()


def build_scroll_validation(payload, required_markers=None):
    warnings = []
    snapshots = payload.get("snapshots") or []
    merged_text_len = int(payload.get("merged_text_len") or 0)
    merged_text = payload.get("merged_text") or ""
    final_scroll_height = 0
    max_scroll_bottom = 0

    for shot in snapshots:
        scroll_top = int(shot.get("scrollTop") or 0)
        client_height = int(shot.get("clientHeight") or 0)
        scroll_height = int(shot.get("scrollHeight") or 0)
        final_scroll_height = max(final_scroll_height, scroll_height)
        max_scroll_bottom = max(max_scroll_bottom, scroll_top + client_height)

    coverage_ratio = 0.0
    if final_scroll_height > 0:
        coverage_ratio = min(1.0, max_scroll_bottom / final_scroll_height)

    if merged_text_len < 1500:
        warnings.append("merged_text_too_short")
    if coverage_ratio < 0.9:
        warnings.append("scroll_coverage_below_90_percent")
    if looks_like_toc_only(merged_text):
        warnings.append("toc_heavy_capture_check_selector")
    if looks_like_partial_course_capture(merged_text):
        warnings.append("partial_course_capture_suspected")
    missing_markers = []
    for marker in required_markers or []:
        if marker and marker not in merged_text:
            missing_markers.append(marker)
    for marker in missing_markers:
        warnings.append(f"missing_required_marker:{marker}")

    payload["validation"] = {
        "ok": len(warnings) == 0,
        "warnings": warnings,
        "merged_text_len": merged_text_len,
        "coverage_ratio": round(coverage_ratio, 4),
        "snapshot_count": len(snapshots),
        "missing_required_markers": missing_markers,
    }
    return payload


def looks_like_toc_only(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 12:
        return False
    return sum(1 for line in lines[:24] if len(line) <= 18) >= 10


def looks_like_partial_course_capture(text):
    markers = [
        "60分 基础",
        "75分 拆解",
        "85分 高阶",
        "维度1：专业拆解\"用户\"",
        "维度2：专业拆解\"场景\"",
        "维度3：专业剥离\"问题\"",
        "作业与Candy",
    ]
    hit_count = sum(1 for marker in markers if marker in text)
    return hit_count >= 4 and text.count("第一部分") <= 1 and text.count("第二部分") <= 1


def write_bundle(bundle_dir, payload):
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "metadata.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "content.txt").write_text(payload.get("merged_text", ""), encoding="utf-8")
    (bundle_dir / "headings.txt").write_text("\n".join(payload.get("headings", [])), encoding="utf-8")
    (bundle_dir / "snapshots.json").write_text(json.dumps(payload.get("snapshots", []), ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Capture long rendered page text from Safari by scrolling.")
    parser.add_argument("--url", required=True, help="Target URL to open in Safari")
    parser.add_argument("--wait", type=float, default=10.0, help="Initial wait after opening (increase for slow pages)")
    parser.add_argument("--settle-wait", type=float, default=8.0, help="Additional wait before scrolling starts")
    parser.add_argument("--steps", type=int, default=250, help="Maximum number of scroll iterations (250+ for long courses)")
    parser.add_argument("--scroll-selector", help="Optional CSS selector for the actual scroll container")
    parser.add_argument("--text-selector", default=".page-body", help="Optional CSS selector for the text root (use .page-body for yitang courses)")
    parser.add_argument("--step-pixels", type=int, help="Optional fixed scroll step in pixels")
    parser.add_argument("--pause", type=float, default=1.0, help="Pause between scroll iterations (1.0s recommended for dynamic content)")
    parser.add_argument("--bundle-dir", help="Directory to save metadata and merged text")
    parser.add_argument("--required-marker", action="append", default=[], help="Marker that must appear in merged text for the capture to count as complete; can be passed multiple times")
    args = parser.parse_args()

    safari_open(args.url)
    time.sleep(args.wait)
    time.sleep(args.settle_wait)

    snapshots = []
    last_top = None
    repeated_bottom = 0
    repeated_no_growth = 0
    last_text_len = -1

    for _ in range(args.steps):
        shot = read_snapshot(scroll_selector=args.scroll_selector, text_selector=args.text_selector)
        snapshots.append(shot)
        top = shot.get("scrollTop", 0)
        scroll_height = shot.get("scrollHeight", 0)
        client_height = shot.get("clientHeight", 0)
        text_len = int(shot.get("text_len") or 0)

        if text_len <= last_text_len:
            repeated_no_growth += 1
        else:
            repeated_no_growth = 0
        last_text_len = text_len

        if top == last_top and top + client_height >= scroll_height:
            repeated_bottom += 1
        else:
            repeated_bottom = 0
        if repeated_bottom >= 2:
            break
        if repeated_no_growth >= 10 and top + client_height >= scroll_height * 0.98:
            break

        move = scroll_once(scroll_selector=args.scroll_selector, pixels=args.step_pixels)
        if not move.get("ok", False):
            break
        if int(move.get("after", top)) == int(move.get("before", top)):
            repeated_bottom += 1
            if repeated_bottom >= 2:
                break
        last_top = move.get("after", top)
        time.sleep(args.pause)

    merged_text = merge_snapshots_text(snapshots)
    headings = []
    for shot in snapshots:
        for item in shot.get("headings", []):
            if item not in headings:
                headings.append(item)

    payload = {
        "requested_url": args.url,
        "final_url": safari_get_url(),
        "final_title": safari_get_title(),
        "scroll_selector": args.scroll_selector,
        "text_selector": args.text_selector,
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "headings": headings,
        "merged_text": merged_text,
        "merged_text_len": len(merged_text),
    }
    payload = build_scroll_validation(payload, required_markers=args.required_marker)

    if args.bundle_dir:
        write_bundle(Path(args.bundle_dir), payload)

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
