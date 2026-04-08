# Yitang / Feishu Capture Notes

Use this reference when a `yitang.top` lesson link is not directly readable through `curl` and the content is rendered or redirected into Feishu.

## Common Patterns

### 1. 一堂课程页面（Vue 渲染）
1. User shares a `yitang.top/fs-doc/...` URL.
2. Raw HTML only contains a frontend shell with `#app`.
3. Page uses Vue.js + Element UI for rendering.
4. Content container is usually `.page-body`.
5. Requires Safari browser capture with JavaScript enabled.
6. Long pages use virtual scrolling, needs scrolling capture.
7. Complete pages usually end with "作业与Candy" section.

### 2. 飞书文档嵌入页面
1. User shares a `yitang.top/fs-doc/...` URL.
2. Raw HTML only contains a frontend shell.
3. Anonymous API access fails or is not worth fully reverse-engineering.
4. The page is opened in a logged-in local Safari session.
5. The page may redirect into a Feishu wiki/doc URL.
6. Capture is performed from the rendered page.
7. A good capture should be validated before rewrite, not blindly trusted.

## Fast Checks

### Raw fetch

Use:

```bash
curl -L "https://yitang.top/..."
```

If the response is only a shell page with `#app`, switch to browser capture quickly.

### Safari checks

Use these in order:

```applescript
tell application "Safari"
    return URL of front document
end tell
```

```applescript
tell application "Safari"
    return name of front document
end tell
```

```applescript
tell application "Safari"
    return do JavaScript "document.body.innerText.slice(0,3000)" in front document
end tell
```

```applescript
tell application "Safari"
    return do JavaScript "String(document.body.innerText.length)" in front document
end tell
```

Then compare the values across multiple polls if the page is still redirecting or rendering.

## DOM Probe Order

Try these from simplest to most specific:

1. `document.body.innerText`
2. heading list or visible TOC in body text
3. block selectors like `[data-block-id]`
4. container metrics such as `scrollHeight`, `clientHeight`, and likely scroll wrappers
5. visible screenshots for framework-heavy sections

Do not over-invest in brittle DOM reverse-engineering if `body.innerText` already reveals:

1. true document title
2. section headings
3. main argument
4. enough content to reconstruct a useful Markdown output

## Feishu Reality

Feishu pages may show:

1. virtualized blocks
2. incomplete `body.innerText`
3. redirected authenticated content
4. image-heavy sections that are not recoverable as plain text

In those cases:

1. capture the headings and visible text first
2. save key explanatory visuals into `assets/key-images/`
3. explicitly mark any partial capture in the final Markdown
4. if needed, switch from one-shot capture to scrolling capture

## Validation Checklist

Treat the capture as stronger when:

1. final URL is stable
2. title is stable
3. body length is stable across multiple polls
4. headings were extracted
5. there is no obvious mismatch between visible page depth and captured text length

Treat the capture as partial when:

1. body text is unexpectedly short
2. the page is image-heavy
3. virtualized sections are not included
4. the content clearly extends beyond the captured text

## Suggested Bundle Layout

For repeatable work, save output in a run-specific folder:

```text
captures/<slug-or-doc-id>/
  metadata.json
  content.txt
  headings.txt
  images/
    visible-page.png
```

Keep reusable methodology screenshots in:

```text
assets/key-images/
```

## When To Use Scrolling Capture

Prefer scrolling capture when:

1. the one-shot body text is much shorter than expected
2. the page uses a virtualized or custom scroll container
3. the TOC shows many sections but the captured text is shallow
4. repeated probes show content changing as you scroll

Suggested command:

```bash
python3 scripts/run_yitang_capture_bundle.py \
  --url "https://yitang.top/fs-doc/..." \
  --with-scroll \
  --bundle-root ./captures \
  --slug example-scroll
```

If the page uses a custom scroll container, you can still call the lower-level scrolling script directly and pass `--scroll-selector`.

## When To Save Key Images

Save a key image when:

1. a diagram explains the method better than text alone
2. a framework screenshot is repeatedly referenced in the course
3. the page contains a radar chart, matrix, SOP, or model diagram

Suggested command:

```bash
python3 scripts/safari_save_key_image.py --name method-radar
```

## Output Bias

Prefer:

1. structured rewrite
2. section regrouping
3. framework extraction
4. concise source note

Avoid:

1. raw DOM dumps
2. giant unedited text blocks
3. claiming completeness without evidence
