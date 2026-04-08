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
    quoted_url = json.dumps(url)
    run_osascript([
        'tell application "Safari"',
        "activate",
        "if (count of windows) = 0 then",
        "make new document",
        "end if",
        f"set URL of front document to {quoted_url}",
        "end tell",
    ])


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


def safari_get_url():
    return run_osascript([
        'tell application "Safari"',
        "return URL of front document",
        "end tell",
    ])


def safari_window_bounds():
    raw = run_osascript([
        'tell application "Safari"',
        "set b to bounds of front window",
        "return (item 1 of b as string) & \",\" & (item 2 of b as string) & \",\" & (item 3 of b as string) & \",\" & (item 4 of b as string)",
        "end tell",
    ])
    left, top, right, bottom = [int(x.strip()) for x in raw.split(",")]
    return left, top, right, bottom


def normalized_capture_rect():
    left, top, right, bottom = safari_window_bounds()
    safe_left = max(0, left)
    safe_top = max(0, top)
    safe_right = max(safe_left + 1, right)
    safe_bottom = max(safe_top + 1, bottom)
    width = max(1, safe_right - safe_left)
    height = max(1, safe_bottom - safe_top)
    return safe_left, safe_top, width, height


def safe_json_loads(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "capture_error": "non_json_js_result",
            "raw_result": raw,
        }


def capture_payload(selector=None):
    selector_expr = json.dumps(selector) if selector else "null"
    js = f"""
(() => {{
  try {{
    const selector = {selector_expr};
    const bodyText = document.body ? document.body.innerText : "";
    const selectedText = selector
      ? ((document.querySelector(selector) || {{ innerText: "" }}).innerText || "")
      : "";
    const headingTexts = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
      .map(n => (n.innerText || "").trim())
      .filter(Boolean)
      .slice(0, 200);
    return JSON.stringify({{
      title: document.title || "",
      url: location.href || "",
      body_len: bodyText.length,
      body_text: bodyText,
      selected_len: selectedText.length,
      selected_text: selectedText,
      headings: headingTexts
    }});
  }} catch (e) {{
    return JSON.stringify({{
      capture_error: "js_exception",
      error_message: String(e)
    }});
  }}
}})()
""".strip()
    raw = safari_eval(js)
    return safe_json_loads(raw)


def build_validation(payload, min_body_len):
    body_len = int(payload.get("body_len") or 0)
    title = payload.get("title") or ""
    url = payload.get("url") or ""
    headings = payload.get("headings") or []
    body_text = payload.get("body_text") or ""
    warnings = []

    if not url:
        warnings.append("missing_final_url")
    if not title:
        warnings.append("missing_title")
    if body_len < min_body_len:
        warnings.append(f"body_too_short_lt_{min_body_len}")
    if len(headings) == 0:
        warnings.append("no_headings_detected")
    if looks_like_toc_only(body_text):
        warnings.append("toc_heavy_capture_check_scroll_or_selector")
    if looks_like_partial_course_capture(body_text):
        warnings.append("partial_course_capture_suspected")

    payload["validation"] = {
        "ok": len(warnings) == 0,
        "warnings": warnings,
        "body_len": body_len,
        "heading_count": len(headings),
    }
    return payload


def looks_ready(payload, min_body_len):
    body_text = (payload.get("body_text") or "").strip()
    body_len = int(payload.get("body_len") or 0)
    selected_len = int(payload.get("selected_len") or 0)
    headings = payload.get("headings") or []
    loading_markers = {"加载中…", "加载中...", "Loading...", "Loading…"}

    if body_text in loading_markers:
        return False
    if body_len >= min_body_len:
        return True
    if selected_len > 0:
        return True
    if len(headings) > 0:
        return True
    return False


def looks_like_toc_only(body_text):
    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    if len(lines) < 12:
        return False
    short_lines = lines[:24]
    short_count = sum(1 for line in short_lines if len(line) <= 18)
    return short_count >= 10


def looks_like_partial_course_capture(body_text):
    markers = [
        "60分 基础",
        "75分 拆解",
        "85分 高阶",
        "维度1：专业拆解\"用户\"",
        "维度2：专业拆解\"场景\"",
        "维度3：专业剥离\"问题\"",
        "作业与Candy",
    ]
    hit_count = sum(1 for marker in markers if marker in body_text)
    return hit_count >= 4 and body_text.count("第一部分") <= 1 and body_text.count("第二部分") <= 1


def wait_for_stable_page(timeout_s, poll_interval, stable_rounds, selector=None, min_body_len=500):
    deadline = time.time() + timeout_s
    last_signature = None
    stable_count = 0
    last_payload = {}

    while time.time() < deadline:
        payload = capture_payload(selector=selector)
        payload["safari_document_title"] = safari_get_title()
        payload["safari_document_url"] = safari_get_url()
        signature = (
            payload.get("url", ""),
            payload.get("title", ""),
            int(payload.get("body_len") or 0),
            int(payload.get("selected_len") or 0),
        )
        last_payload = payload

        if signature == last_signature:
            stable_count += 1
        else:
            stable_count = 1
            last_signature = signature

        if stable_count >= stable_rounds and looks_ready(payload, min_body_len=min_body_len):
            payload["stability"] = {
                "stable": True,
                "stable_rounds": stable_count,
                "signature": list(signature),
            }
            return payload

        time.sleep(poll_interval)

    last_payload["stability"] = {
        "stable": False,
        "stable_rounds": stable_count,
        "signature": list(last_signature or []),
    }
    return last_payload


def save_visible_screenshot(path):
    left, top, width, height = normalized_capture_rect()
    cmd = [
        "screencapture",
        "-x",
        "-R",
        f"{left},{top},{width},{height}",
        str(path),
    ]
    subprocess.run(cmd, check=True)


def write_bundle(bundle_dir, payload, save_visible):
    bundle_dir.mkdir(parents=True, exist_ok=True)
    images_dir = bundle_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    (bundle_dir / "metadata.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (bundle_dir / "content.txt").write_text(payload.get("body_text", ""), encoding="utf-8")
    (bundle_dir / "selected.txt").write_text(payload.get("selected_text", ""), encoding="utf-8")
    (bundle_dir / "headings.txt").write_text(
        "\n".join(payload.get("headings", [])),
        encoding="utf-8",
    )

    if save_visible:
        save_visible_screenshot(images_dir / "visible-page.png")


def main():
    parser = argparse.ArgumentParser(description="Capture rendered page text from Safari.")
    parser.add_argument("--url", required=True, help="Target URL to open in Safari")
    parser.add_argument("--wait", type=float, default=10.0, help="Initial seconds to wait after opening")
    parser.add_argument("--settle-timeout", type=float, default=30.0, help="Max seconds to wait for redirect/render stabilization")
    parser.add_argument("--poll-interval", type=float, default=1.5, help="Polling interval in seconds while waiting for page stabilization")
    parser.add_argument("--stable-rounds", type=int, default=3, help="How many identical polling rounds count as stable")
    parser.add_argument("--selector", help="Optional CSS selector to capture a focused text region in addition to body text")
    parser.add_argument("--min-body-len", type=int, default=1000, help="Minimum body length before the capture is considered likely complete")
    parser.add_argument("--out-json", help="Path to save capture JSON")
    parser.add_argument("--out-text", help="Path to save rendered text")
    parser.add_argument("--bundle-dir", help="Directory to save a standard capture bundle")
    parser.add_argument("--screenshot-visible", action="store_true", help="Save a screenshot of the visible Safari page into the bundle images directory")
    args = parser.parse_args()

    safari_open(args.url)
    time.sleep(args.wait)

    payload = wait_for_stable_page(
        timeout_s=args.settle_timeout,
        poll_interval=args.poll_interval,
        stable_rounds=args.stable_rounds,
        selector=args.selector,
        min_body_len=args.min_body_len,
    )
    payload = build_validation(payload, min_body_len=args.min_body_len)
    payload["requested_url"] = args.url

    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.out_text:
        out_text = Path(args.out_text)
        out_text.parent.mkdir(parents=True, exist_ok=True)
        out_text.write_text(payload.get("body_text", ""), encoding="utf-8")

    if args.bundle_dir:
        write_bundle(Path(args.bundle_dir), payload, save_visible=args.screenshot_visible)

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
