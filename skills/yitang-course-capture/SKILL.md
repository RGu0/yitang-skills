---
name: yitang_course_capture
description: Capture and restructure course content from yitang.top course pages, especially /fs-doc pages that may redirect into Feishu docs. Use when the user wants a yitang.top lesson page analyzed, extracted, summarized, converted into Markdown, or turned into a reusable AI prompt/spec, and the page may require browser-assisted capture through a logged-in local Safari session.
---

# Yitang.top Course Capture

Use this skill when the user provides a `yitang.top` course link and wants the course content extracted, analyzed, rewritten into Markdown, or distilled into a reusable AI prompt/specification that applies the course's methods to real problems.

This workflow is optimized for:

1. `https://yitang.top/fs-doc/...` lesson pages
2. pages that render client-side and do not expose full HTML in `curl`
3. pages that redirect into Feishu docs
4. pages that require a logged-in browser session

## Bundled Resources

This skill should keep a dedicated image folder:

1. `assets/key-images/`
2. `scripts/`
3. `references/`

Use this folder to save high-value visuals that explain the course content, especially:

1. model diagrams
2. methodology diagrams
3. radar charts
4. framework screenshots
5. process maps

Do not dump every screenshot into this folder. Save only images that help explain the course's structure, methods, or core frameworks.
Do not prioritize title slides, transition pages, or decorative banners. Prefer images that contain models, checklists, cheat sheets, roadmaps, tables, or structured visual frameworks.

The bundled resources are intended for:

1. `scripts/safari_capture_page.py`
   Use to open a target page in Safari, wait for redirects, validate page stability, and export title, final URL, rendered text, headings, and bundle artifacts.
2. `scripts/safari_capture_scrolling.py`
   Use when the page is long, virtualized, or only partially available from a single `document.body.innerText` read.
3. `scripts/safari_save_key_image.py`
   Use to extract and download high-value rendered images from the current Safari page into the active course bundle directory.
   The default behavior should prefer explanatory images over title images, and should not stop at a fixed count like 6 unless the caller explicitly sets a limit.
4. `scripts/run_yitang_capture_bundle.py`
   Use as the default orchestrator when you want a standard bundle with one-shot capture, optional scrolling capture, optional key image extraction, and a detailed course report.
   When a course page has a known tail section, use `--required-marker` to force completion checks against that section title.
5. `scripts/generate_course_prompt.py`
   Use to turn a completed capture bundle into a reusable AI prompt/spec file grounded in the captured course content.
6. `references/yitang-feishu-capture.md`
   Use when you need reminders on the `yitang.top -> Feishu` capture pattern, DOM probing order, and fallback strategy.
7. `references/通用课程转AI提示词-template.md`
   Use as the default generic template when the user wants any captured course turned into a reusable AI prompt/spec.
8. `references/需求拆解专家-prompt-template.md`
   Use as a concrete example of how a specific course can be turned into a course-expert prompt/spec.

## Goal

Produce a clean Markdown deliverable from the course page, preserving:

1. title
2. major sections
3. key arguments
4. examples and frameworks
5. practical takeaways

This skill must default to producing three end deliverables for a captured course page:

1. a detailed human-readable course document written like a strong textbook or training manual
2. an AI prompt/spec file that makes an AI act like a course expert and apply the course's methods to concrete business questions
3. at least 3 core method images from the course page, prioritizing diagrams, frameworks, tables, checklists, and methodology visuals

Prefer a structured rewrite over raw copy-paste. The default report should be a detailed structured course note, not a thin summary.
All substantive content in the report must come from the captured webpage itself. Do not introduce outside facts, outside examples, or fabricated explanations.
You may infer structure, causal logic, or teaching intent from the captured text, but when you do so, label it clearly as a summary or analysis based on the captured page.

When generating an AI prompt/spec from the course, the prompt must also be grounded only in the captured course content. Do not inject outside frameworks, outside heuristics, or generic prompt boilerplate unless the course itself supports them.

When saving core images, the default expectation is not “save some if convenient”, but “deliver at least 3 method-relevant images whenever the page materially contains them”. If the page truly does not contain 3 suitable method visuals, say so explicitly and describe what was found instead.

## Workflow

### 1. Check whether the page is directly fetchable

Start with the raw URL:

1. fetch the HTML with `curl -L`
2. inspect whether the response already contains useful text
3. if the HTML is only a frontend shell, inspect the JS bundle or route shape only as needed

Typical signs that direct fetch is insufficient:

1. HTML contains only `#app`
2. main content is loaded by JS
3. page requires login and API returns unauthenticated

### 2. Identify the page type

For `yitang.top` course pages, quickly classify:

1. static HTML page
2. Vue-rendered `fs-doc` page
3. redirected Feishu doc

For `fs-doc` pages, note these common parameters:

1. `acl`
2. document id
3. query fields such as `fromAcl`

Do not spend too long reverse-engineering APIs if browser capture is faster.

### 3. Prefer browser-assisted extraction when login or client rendering blocks direct access

#### 3.1 环境准备（关键！）

**必须检查的 Safari 配置：**

1. **启用开发菜单**
   - 打开 Safari → `设置` → `高级` → 勾选 `在菜单栏中显示开发菜单`

2. **允许 JavaScript from Apple Events**
   - 点击菜单栏的 `开发` → 勾选 `允许 Apple Events 中的 JavaScript`

**如果 Safari 未配置正确，会出现如下错误：**
```
RuntimeError: 33:910: execution error: Safari got an error: You must enable 'Allow JavaScript from Apple Events' in the Developer section of Safari Settings to use 'do JavaScript'. (8)
```

**其他准备：**
- 确保网络连接稳定
- 如果页面需要登录，确保 Safari 已处于登录状态

#### 3.2 页面分类优化

对于 `yitang.top` 课程页面，分为两类：
1. **一堂课程页面**：直接由一堂系统渲染的 Vue 页面（如本案例），特征：
   - 包含 `.page-body` 内容容器
   - 使用 Element UI 组件
   - 有完整的课程目录和内容
2. **飞书文档嵌入**：重定向到飞书文档的页面，特征：
   - 页面包含飞书文档的特征（如 `.b3-rich-text` 等类）
   - 通常需要登录飞书账号

#### 3.3 优化的参数建议

**一堂课程页面最佳参数：**

```bash
# 基础捕获
python3 scripts/safari_capture_page.py \
  --url "https://yitang.top/fs-doc/..." \
  --wait 10 \
  --settle-timeout 20 \
  --min-body-len 1000 \
  --bundle-dir ./captures/one-shot

# 滚动捕获（建议）
python3 scripts/safari_capture_scrolling.py \
  --url "https://yitang.top/fs-doc/..." \
  --wait 12 \
  --settle-wait 8 \
  --steps 250 \
  --pause 1 \
  --text-selector ".page-body" \
  --bundle-dir ./captures/scroll-full \
  --required-marker "作业与Candy"
```

**关键参数说明：**
- `--wait`：增加到 10-15 秒（页面加载需要时间）
- `--settle-wait`：增加到 8-10 秒（DOM 渲染稳定时间）
- `--steps`：至少 200 步（一堂课程页面通常有 700+ 行）
- `--pause`：1 秒/步（确保内容加载）
- `--text-selector ".page-body"`：指定内容容器（重要！）

#### 3.4 失败排查步骤

**常见问题与解决方案：**

1. **Vue 应用未加载**
   ```javascript
   // 检查页面状态
   osascript -e 'tell application "Safari" to return do JavaScript "typeof Vue !== \"undefined\" && document.getElementById(\"app\").innerHTML.length > 100" in front document'
   ```
   解决：刷新页面，增加等待时间

2. **内容只显示加载提示**
   ```
   text: "加载中…"
   ```
   解决：页面需要更长时间加载，检查网络或增加等待时间

3. **滚动捕获内容少**
   ```
   merged_text_len: 0
   ```
   解决：使用正确的文本选择器（`.page-body`），增加滚动步数

#### 3.5 主流程优化

Primary browser path:

1. open the URL in local Safari
2. wait for redirects to settle
3. read `URL of front document` and `name of front document`
4. use `do JavaScript` in Safari to inspect rendered DOM

Do not rely on a fixed sleep alone for final extraction. Prefer polling until URL, title, and text length stabilize.

Preferred first probes:

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

If the page redirects to Feishu, continue extraction from the Feishu page rather than trying to force the original `yitang.top` endpoint.

### 4. Extract the content in layers

Use this order:

1. page title
2. visible table of contents or heading list
3. `document.body.innerText`
4. heading extraction
5. block-level text if available
6. screenshots or saved visuals for models and methodology when they materially improve the final Markdown

### 5. Synthesize the course method before writing outputs

Do not jump directly from raw capture to final deliverable.

First compress the course into a method model:

1. what problem the course is trying to solve
2. what sequence of thinking the course enforces
3. what formulas, checklists, or principles it repeats
4. what counts as a good answer vs a bad answer in the course's worldview
5. what failure patterns, misjudgments, or traps the course repeatedly warns about
6. what concrete outputs or actions the learner is expected to produce

If the course is practical, identify:

1. the role the course expects the learner to play
2. the decision standard the course uses
3. the exact order of operations
4. the minimal viable checklist for applying the method to a real case

### 6. When the user wants an AI prompt/spec, convert the course into an operator

If the user asks for a prompt, prompt file, AI instructions, agent spec, or reusable workflow, do not write a generic summary prompt.

Instead:

1. infer the expert role from the course itself
2. convert the course's method into explicit operating rules
3. preserve the course's sequence, judgment criteria, and constraints
4. turn repeated formulas into required analysis steps
5. turn repeated warnings into hard prohibitions or guardrails
6. force the output structure to match the course's problem-solving style

For prompt/spec outputs, prefer this structure:

1. role and stance
2. core principles
3. required analysis sequence
4. judgment criteria
5. hard constraints / anti-patterns
6. fixed output format
7. optional user input template

The resulting prompt should feel like the AI has internalized the course's method, not like the AI merely “knows about” the course.

### 7. Output bias

When the user asks for analysis:

1. explain the course's logic clearly
2. connect methods to concrete cases from the captured page
3. separate source-grounded summary from your own inference

When the user asks for a prompt/spec:

1. optimize for direct reusability
2. make the prompt operational, not inspirational
3. force explicit steps and decision criteria
4. prefer concrete output schemas over vague advice
5. encode the course's standard for what counts as a valid answer

### 8. Default completion checklist

Unless the user explicitly narrows the task, a complete use of this skill should finish with all of the following:

1. a detailed course document for humans
2. a reusable AI prompt/spec derived from the course's actual method
3. a saved set of at least 3 core method images
4. clear file paths for all generated outputs

For the human-readable course document, aim for classic教材/教案 quality:

1. clear chapter structure
2. progressive logic from foundations to method to application
3. explicit definitions, principles, examples, and takeaways
4. readable explanatory prose rather than raw notes

Useful DOM probes:

```javascript
document.body.innerText
```

```javascript
[...document.querySelectorAll('[data-block-id]')].map(n => n.innerText).filter(Boolean)
```

```javascript
JSON.stringify({
  url: location.href,
  title: document.title,
  bodyLen: document.body.innerText.length
})
```

```javascript
[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(n => n.innerText).filter(Boolean)
```

If a selector returns nothing, fall back immediately. Do not overfit to one DOM structure.

### 5. Handle Feishu-specific behavior pragmatically

Feishu docs often behave like this:

1. short visible text window
2. virtualized block rendering
3. redirected authenticated pages
4. partial text in `body.innerText`

When `body.innerText` is enough to identify the article and capture its core sections, use it plus the visible headings to build the Markdown deliverable.

When the doc is longer than the visible capture:

1. inspect likely scroll containers
2. try block selectors such as `[data-block-id]`
3. save key framework or model visuals into `assets/key-images/` if they help recover the document structure
4. if block extraction fails, rely on visible content plus any existing local copy or previous capture artifacts
5. say clearly when the capture is partial

If the capture body is short but the page is clearly longer, treat the capture as partial even if the script succeeds.

### 6. Produce the Markdown output

Default deliverable:

1. title
2. source URL
3. short capture note
4. detailed section-by-section整理
5. methods / frameworks / examples
6. case-by-case notes with key details
7. practical checklist or takeaway summary
8. image references when saved visuals are relevant

When writing the report, separate these two layers whenever possible:

1. `原文整理`
2. `归纳分析（基于原文）`

This is especially important when the target reader is a beginner. The report may become more readable than the source page, but it must not become a new article that invents content beyond the captured material.

Prefer:

1. cleaned headings
2. rewritten prose
3. explicit grouping by theme
4. section names that mirror the course structure
5. case summaries that retain the concrete project details, judgment logic, and outcomes

Avoid:

1. dumping raw OCR-like text
2. copying huge unstructured blocks
3. pretending the capture is complete when it is not
4. outputting a metadata-only report

If you save key visuals, reference them from the Markdown using absolute paths.

## Validation Gates

Before turning a capture into a final Markdown rewrite, check:

1. final URL is present
2. title is present
3. body length is above a reasonable threshold for the page type
4. at least some headings or structural markers were captured
5. the capture is explicitly marked partial when those conditions are not met

If the page has a known tail section, add a required marker and do not treat the capture as complete unless that marker appears in the merged text. For example:

`--required-marker "作业与Candy"`

## Fallback Order

If the standard path fails, use this order:

1. `curl` raw HTML
2. inspect frontend route and likely API only briefly
3. use `scripts/run_yitang_capture_bundle.py` with the local Safari session
4. if the page is long or partial, ensure the scrolling phase is enabled
5. if the page has a known terminal section, pass `--required-marker` and verify it appears in the merged text
6. inspect the bundle output and validation warnings
7. inspect redirected Feishu page
8. use user-provided PDF/text as last resort

## Output Rules

When you generate the Markdown document:

1. use the filename `课程标题-分析报告.md`
2. include the source URL at the top
3. state whether the document came from direct fetch, browser render, or redirected Feishu page
4. if capture is partial, explicitly mark it
5. place any extracted core images in the same course bundle directory as the report
6. use descriptive filenames, for example:

`method-radar.jpg`

`oscar-framework.png`

`research-types-overview.jpg`

`auto-research-pipeline.png`

The detailed report should usually contain:

1. 课程定位
2. 阅读说明（注明只基于当前网页）
3. 课程结构
4. 分章节整理
5. 方法框架
6. 把案例放到对应方法前后进行解释
7. 作业与Candy
8. 可执行清单
9. 附录与图片引用

For repeatable runs, prefer a bundle layout like:

`captures/<slug-or-doc-id>/课程标题-分析报告.md`

`captures/<slug-or-doc-id>/课程标题-核心图片-01.png`

`captures/<slug-or-doc-id>/manifest.json`

`captures/<slug-or-doc-id>/one-shot/content.txt`

`captures/<slug-or-doc-id>/scroll/content.txt`

## Known Constraints

1. Some `yitang.top` APIs require login and signed headers.
2. Reverse-engineering the signed API is usually not worth it unless browser capture is impossible.
3. Safari must allow JavaScript from Apple Events if browser-side extraction is needed.
4. Chrome may block Apple Events JS by default.

## Minimal Safari Commands

Open the page:

```applescript
tell application "Safari"
    activate
    if (count of windows) = 0 then
        make new document
    end if
    set URL of front document to "https://yitang.top/..."
end tell
```

Read rendered text:

```applescript
tell application "Safari"
    return do JavaScript "document.body.innerText.slice(0,5000)" in front document
end tell
```

Read current URL after redirects:

```applescript
tell application "Safari"
    return URL of front document
end tell
```

## Script Usage Optimization

### 4.1 最佳实践：完整流程

#### 针对一堂课程页面的完整捕获命令

```bash
cd '/Users/rui/Documents/0. AI/调研/yitang-top-course-skill' && 

# 步骤1：先尝试基础捕获
python3 scripts/safari_capture_page.py \
  --url "https://yitang.top/fs-doc/7etN6939409aa0a8/TeyEdg5Ojo3n2dxxBsocIxG2nYs?fromAcl=lesson-founder" \
  --wait 10 \
  --settle-timeout 20 \
  --min-body-len 1000 \
  --bundle-dir ./captures/one-shot

# 步骤2：使用滚动捕获获取完整内容（推荐）
python3 scripts/safari_capture_scrolling.py \
  --url "https://yitang.top/fs-doc/7etN6939409aa0a8/TeyEdg5Ojo3n2dxxBsocIxG2nYs?fromAcl=lesson-founder" \
  --wait 12 \
  --settle-wait 8 \
  --steps 250 \
  --pause 1 \
  --text-selector ".page-body" \
  --bundle-dir ./captures/scroll-full \
  --required-marker "作业与Candy"

# 步骤3：保存关键图片
python3 scripts/safari_save_key_image.py \
  --name yitang-course-images \
  --bundle-dir ./captures/images
```

### 4.2 使用 run_yitang_capture_bundle.py 优化版本

```bash
cd '/Users/rui/Documents/0. AI/调研/yitang-top-course-skill' && 
python3 scripts/run_yitang_capture_bundle.py \
  --url "https://yitang.top/fs-doc/7etN6939409aa0a8/TeyEdg5Ojo3n2dxxBsocIxG2nYs?fromAcl=lesson-founder" \
  --with-scroll \
  --save-core-images \
  --bundle-root ./captures \
  --slug yitang_lesson_analysis \
  --text-selector ".page-body" \
  --wait 10 \
  --settle-timeout 25 \
  --scroll-steps 250
```

### 4.3 调试和验证

**检查页面加载状态：**
```bash
osascript -e 'tell application "Safari" to activate' -e 'tell application "Safari" to return do JavaScript "JSON.stringify({
  hasVue: typeof Vue !== \"undefined\",
  bodyLength: document.body.innerText.length,
  appContent: document.getElementById(\"app\").innerHTML.length
})" in front document'
```

**验证捕获完整性：**
```bash
# 检查内容长度（一堂课程通常 > 5000 字符）
wc -c captures/yitang_lesson_analysis/scroll-full/content.txt

# 检查是否包含完整章节标记
grep -E "作业与Candy|重新理解|60分.*基础" captures/yitang_lesson_analysis/scroll-full/content.txt
```

### 4.4 常见问题修复

**问题1：Vue应用未加载**
```bash
# 刷新页面并重新捕获
osascript -e 'tell application "Safari" to set URL of front document to "https://yitang.top/fs-doc/7etN6939409aa0a8/TeyEdg5Ojo3n2dxxBsocIxG2nYs?fromAcl=lesson-founder"'
sleep 15
python3 scripts/safari_capture_scrolling.py --url "https://yitang.top/fs-doc/..." --with-scroll --bundle-dir ./captures/retry
```

**问题2：内容不完整**
```bash
# 增加滚动步数
python3 scripts/safari_capture_scrolling.py \
  --url "https://yitang.top/fs-doc/..." \
  --steps 350 \
  --pause 1.2 \
  --text-selector ".page-body" \
  --bundle-dir ./captures/full-content
```
  --bundle-root ./captures \
  --slug example \
  --wait 2 \
  --settle-timeout 20
```

This creates a standard structure like:

```text
captures/example/
  manifest.json
  one-shot/
    metadata.json
    content.txt
    headings.txt
  scroll/
    metadata.json
    content.txt
    headings.txt
```

The orchestrator should be the default first choice when:

1. you need a repeatable capture
2. you want both title and final redirected URL
3. you want text persisted to disk before writing the final Markdown
4. you want validation warnings before starting the rewrite
5. you want one standard command for the whole capture flow

If you only need one-shot capture, you can still call:

```bash
python3 scripts/safari_capture_page.py \
  --url "https://yitang.top/fs-doc/..." \
  --bundle-dir ./captures/example/one-shot
```

Scrolling helper for long or virtualized pages:

```bash
python3 scripts/safari_capture_scrolling.py \
  --url "https://yitang.top/fs-doc/..." \
  --steps 12 \
  --bundle-dir ./captures/example-scroll
```

Key image helper:

```bash
python3 scripts/safari_save_key_image.py \
  --name oscar-framework
```

## Completion Standard

This skill is successful when:

1. the true rendered page source is identified
2. the course title and major sections are captured
3. a reusable capture bundle exists when needed
4. the capture is marked complete or partial with an explicit reason
5. the user receives a useful Markdown document instead of raw page output
