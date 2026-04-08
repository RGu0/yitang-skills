#!/usr/bin/env python3

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def safe_stem(text):
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r'[\\\\/:*?\"<>|]+', "-", text)
    text = re.sub(r"-{2,}", "-", text).strip(" .-")
    return text or "未命名课程"


def load_manifest(bundle_dir):
    return json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))


def choose_source_text(manifest):
    scroll = manifest.get("scroll") or {}
    one_shot = manifest.get("one_shot") or {}
    scroll_text = scroll.get("merged_text") or ""
    one_shot_text = one_shot.get("body_text") or ""
    return scroll_text if len(scroll_text) >= len(one_shot_text) else one_shot_text


def normalize_line(text):
    text = text.replace("​", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def nonempty_lines(text):
    return [normalize_line(line) for line in text.splitlines() if normalize_line(line)]


def unique_keep_order(items):
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def split_sentences(text):
    text = normalize_line(text)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;])\s+|(?<=[。！？!?；;])", text)
    return [normalize_line(part) for part in parts if normalize_line(part)]


def extract_outline(lines):
    patterns = [
        r"^\d+分\s",
        r"^第[一二三四五六七八九十\d]+(部分|章|节|讲|步|课)",
        r"^维度[一二三四五六七八九十\d：:]",
        r"^模块[一二三四五六七八九十\d：:]",
        r"^阶段[一二三四五六七八九十\d：:]",
        r"^步骤[一二三四五六七八九十\d：:]",
        r"^(开始上课|快速回顾|为什么要学|预热思考题|提前划重点|重新理解|作业与Candy)$",
    ]
    outline = []
    for line in lines:
        if len(line) > 60:
            continue
        if any(re.search(pattern, line) for pattern in patterns):
            outline.append(line)
    return unique_keep_order(outline)


def extract_formula_lines(lines):
    formulas = []
    for line in lines:
        if len(line) > 80:
            continue
        if re.search(r"[=＝×xX→➜]|公式|模型|框架|原则|方法|逻辑|四字诀|三要素|清单|画布|JTBD|GAP|匹配", line):
            formulas.append(line)
    return unique_keep_order(formulas)


def extract_numbered_lists(lines):
    bullets = []
    for line in lines:
        if re.match(r"^(\d+\.|[①②③④⑤⑥⑦⑧⑨⑩]|[-•])", line):
            bullets.append(line)
    return unique_keep_order(bullets)


def top_repeated_phrases(lines, min_len=2, max_len=8, topn=12):
    stopwords = {
        "我们", "你们", "大家", "这个", "那个", "如果", "因为", "所以", "什么", "一个", "一些",
        "然后", "就是", "不是", "可以", "需要", "以及", "自己", "进行", "时候", "这样", "通过",
        "里面", "后面", "现在", "最后", "可能", "很多", "没有", "已经", "还是", "非常", "应该",
    }
    counter = Counter()
    for line in lines:
        clean = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", line)
        for size in range(min_len, max_len + 1):
            for i in range(0, max(0, len(clean) - size + 1)):
                phrase = clean[i:i + size]
                if len(phrase) < min_len:
                    continue
                if phrase in stopwords:
                    continue
                if phrase.isdigit():
                    continue
                counter[phrase] += 1
    ranked = [phrase for phrase, count in counter.most_common(topn * 4) if count >= 3]
    filtered = []
    for phrase in ranked:
        if any(phrase in existing and phrase != existing for existing in filtered):
            continue
        filtered.append(phrase)
        if len(filtered) >= topn:
            break
    return filtered


def extract_candidate_sentences(lines, patterns, limit=8, max_len=140):
    result = []
    for line in lines:
        for sentence in split_sentences(line):
            if len(sentence) > max_len:
                continue
            if any(noise in sentence for noise in ["热场", "互动", "报名", "扣一个", "评论区", "直播间", "学习委员"]):
                continue
            if any(re.search(pattern, sentence) for pattern in patterns):
                result.append(sentence)
    return unique_keep_order(result)[:limit]


def infer_course_type(title, text, outline):
    signals = {
        "method": 0,
        "process": 0,
        "concept": 0,
        "case": 0,
        "tool": 0,
    }

    method_markers = ["方法", "框架", "模型", "原则", "拆解", "公式", "逻辑", "体系", "分析"]
    process_markers = ["步骤", "流程", "阶段", "操作", "实操", "执行", "SOP", "清单"]
    concept_markers = ["认知", "理解", "本质", "原点", "为什么", "底层", "思维"]
    case_markers = ["案例", "复盘", "推演", "项目", "作业", "实战"]
    tool_markers = ["提示词", "工具", "AI", "软件", "系统", "表格", "画布"]

    def score(markers, bucket, weight=1):
        total = sum(text.count(marker) + title.count(marker) for marker in markers)
        signals[bucket] += total * weight

    score(method_markers, "method", 2)
    score(process_markers, "process", 2)
    score(concept_markers, "concept", 2)
    score(case_markers, "case", 1)
    score(tool_markers, "tool", 1)

    for item in outline:
        if any(marker in item for marker in process_markers):
            signals["process"] += 3
        if any(marker in item for marker in method_markers):
            signals["method"] += 3
        if any(marker in item for marker in concept_markers):
            signals["concept"] += 2
        if "案例" in item:
            signals["case"] += 2

    return max(signals.items(), key=lambda x: x[1])[0]


def infer_role(title, course_type, repeated_phrases):
    if course_type == "method":
        if "拆解" in title:
            return f"{title} 课程专家 / 方法教练"
        return f"{title} 方法论专家"
    if course_type == "process":
        return f"{title} 实操教练"
    if course_type == "concept":
        return f"{title} 认知教练"
    if course_type == "tool":
        return f"{title} 工具应用顾问"
    if course_type == "case":
        return f"{title} 案例分析导师"
    return repeated_phrases[0] + " 专家" if repeated_phrases else f"{title} 课程专家"


def infer_core_problem(title, lines, course_type):
    candidates = extract_candidate_sentences(
        lines,
        [
            r"本质.*是",
            r"目标.*是",
            r"关键.*是",
            r"真正.*是",
            r"要解决",
            r"要研究",
            r"希望.*能力",
            r"需求分析.*实质",
        ],
        limit=10,
        max_len=100,
    )
    if candidates:
        return candidates[0]
    defaults = {
        "method": f"严格按照《{title}》的方法解决问题，而不是只做泛泛讨论",
        "process": f"严格按照《{title}》的步骤和流程推进任务",
        "concept": f"用《{title}》的底层认知和判断标准理解并分析问题",
        "case": f"用《{title}》的案例分析方式处理真实情境",
        "tool": f"按《{title}》的方法正确使用工具并解决实际问题",
    }
    return defaults.get(course_type, f"严格按照《{title}》的方法解决具体问题")


def extract_method_card(title, text):
    lines = nonempty_lines(text)
    outline = extract_outline(lines)
    repeated = top_repeated_phrases(lines)
    formulas = extract_formula_lines(lines)
    explicit_principles = extract_candidate_sentences(
        lines,
        [
            r"原则",
            r"建议",
            r"必须",
            r"要",
            r"不要",
            r"不能",
            r"应该",
            r"价值",
            r"核心逻辑",
        ],
        limit=20,
        max_len=80,
    )
    traps = extract_candidate_sentences(
        lines,
        [
            r"误判",
            r"误区",
            r"陷阱",
            r"错误",
            r"风险",
            r"不要",
            r"不能",
            r"虚假",
            r"矛盾",
            r"冲突",
            r"硬伤",
        ],
        limit=14,
        max_len=90,
    )
    outputs = extract_candidate_sentences(
        lines,
        [
            r"输出",
            r"清单",
            r"提示词",
            r"案例分析",
            r"学习心得",
            r"完成.*什么",
            r"提交",
        ],
        limit=10,
        max_len=90,
    )
    course_type = infer_course_type(title, text, outline)
    role = infer_role(title, course_type, repeated)
    core_problem = infer_core_problem(title, lines, course_type)

    steps = [item for item in outline if item not in {"开始上课", "快速回顾", "为什么要学", "预热思考题", "提前划重点", "作业与Candy"}]
    steps = steps[:8]
    if not steps:
        step_candidates = extract_candidate_sentences(
            lines,
            [r"第[一二三四五六七八九十\d]+", r"步骤", r"阶段", r"维度", r"模块"],
            limit=8,
            max_len=80,
        )
        steps = step_candidates

    principle_priority = extract_candidate_sentences(
        lines,
        [
            r"先.*再",
            r"需求.*不是",
            r"每.*都.*需求",
            r"向上支撑",
            r"内部证伪",
            r"横向自检",
            r"虚假拆解",
            r"问题.*GAP",
            r"最重要.*3-5刀",
        ],
        limit=12,
        max_len=90,
    )
    principles = unique_keep_order(principle_priority + formulas[:6] + explicit_principles[:8])[:10]

    return {
        "title": title,
        "course_type": course_type,
        "role": role,
        "core_problem": core_problem,
        "outline": outline,
        "steps": steps,
        "formulas": formulas[:8],
        "principles": principles,
        "traps": traps[:8],
        "outputs": outputs[:8],
        "repeated_phrases": repeated[:10],
        "numbered_lists": extract_numbered_lists(lines)[:12],
    }


def course_type_instructions(course_type):
    mapping = {
        "method": {
            "focus": "优先保持方法顺序、判断标准和适用边界",
            "bad": "跳步、空话、只给概念不落到动作",
        },
        "process": {
            "focus": "优先保证步骤完整、前后依赖明确、输出可执行",
            "bad": "缺步骤、乱顺序、缺前置条件",
        },
        "concept": {
            "focus": "优先澄清核心概念、本质和判断框架，再落到具体分析",
            "bad": "只列术语、不解释关系、直接给结论",
        },
        "case": {
            "focus": "优先复用课程中的案例分析方式，把抽象方法落到真实情境",
            "bad": "脱离案例语境、只做空泛复盘",
        },
        "tool": {
            "focus": "优先说明工具使用前提、正确动作、检查点和结果标准",
            "bad": "只说工具能做什么，不说如何正确使用",
        },
    }
    return mapping.get(course_type, {"focus": "优先按课程逻辑处理问题", "bad": "泛泛总结课程"})


def render_list(items, fallback):
    return items if items else fallback


def build_prompt(method_card):
    title = method_card["title"]
    course_type = method_card["course_type"]
    role = method_card["role"]
    focus = course_type_instructions(course_type)

    principles = render_list(
        method_card["principles"][:6],
        ["严格按照课程给出的逻辑顺序工作", "不要脱离课程边界自由发挥", "用课程自己的标准判断答案质量"],
    )
    formulas = method_card["formulas"][:6]
    steps = render_list(
        method_card["steps"][:6],
        ["先定义问题", "再按课程方法拆解", "再用课程标准判断", "最后给出动作建议"],
    )
    traps = render_list(
        method_card["traps"][:6],
        ["泛泛总结课程", "跳步下结论", "套用课外框架", "忽略课程边界"],
    )
    outputs = render_list(
        method_card["outputs"][:5],
        ["结构化分析", "行动建议", "风险提示"],
    )

    lines = [
        f"# {title}-课程专家AI Prompt",
        "",
        "## 自动提炼的方法卡",
        "",
        f"- 课程类型：`{course_type}`",
        f"- 专家角色：`{role}`",
        f"- 课程核心问题：{method_card['core_problem']}",
        "",
    ]
    if method_card["outline"]:
        lines.extend(["- 课程结构："])
        for item in method_card["outline"][:10]:
            lines.append(f"  - {item}")
        lines.append("")

    lines.extend(
        [
            "## Prompt 正文",
            "",
            "```md",
            f"你现在扮演一位真正学懂了《{title}》的专家操作者。",
            "",
            "你的目标不是泛泛介绍这门课，也不是把课程内容复述给我听，而是严格按照这门课的方法、顺序、标准和边界来解决我提出的具体问题。",
            "",
            "一、角色与任务",
            "",
            f"1. 你的角色是：{role}",
            f"2. 你的核心任务是：{method_card['core_problem']}",
            f"3. 你优先处理的是：{focus['focus']}",
            "4. 你不能退化成：通用顾问、摘要生成器、创意包装师。",
            "",
            "二、必须遵守的课程原则",
            "",
        ]
    )
    for idx, item in enumerate(principles, start=1):
        lines.append(f"{idx}. {item}")

    if formulas:
        lines.extend(["", "课程中的关键公式/框架：", ""])
        for item in formulas:
            lines.append(f"- {item}")

    lines.extend(["", "三、你的工作顺序", ""])
    for idx, step in enumerate(steps, start=1):
        lines.append(f"第 {idx} 步：{step}")
        lines.append("- 明确这一阶段要解决的问题。")
        lines.append("- 严格按课程逻辑分析。")
        lines.append("- 不足信息要明确指出。")
        lines.append("")

    lines.extend(
        [
            "四、判断标准",
            "",
            "- 好答案应该符合课程的方法顺序、核心原则和判断标准。",
            "- 好答案应该能把课程内容落到具体动作、判断和约束上。",
            f"- 好答案应该优先做到：{focus['focus']}。",
            f"- 坏答案的典型表现是：{focus['bad']}。",
            "",
            "五、必须警惕的误区",
            "",
        ]
    )
    for item in traps:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "六、输出约束",
            "",
            "1. 不能脱离课程方法自由发挥。",
            "2. 不能把课程外的框架强行塞进来。",
            "3. 如果我的输入与课程方法冲突，你要明确指出冲突点。",
            "4. 如果课程强调先后顺序，你必须保持这个顺序。",
            "5. 如果课程有典型误区，你要主动指出并纠正。",
            "",
            "七、固定输出格式",
            "",
            "# 一、问题重述",
            "- 你理解到的问题：",
            "- 课程会如何定义这个问题：",
            "",
            "# 二、按课程方法拆解",
            "- 第一步分析：",
            "- 第二步分析：",
            "- 第三步分析：",
            "- 如有必要继续补充后续步骤：",
            "",
            "# 三、课程标准下的判断",
            "- 当前判断：",
            "- 对应依据：",
            "- 哪些地方成立：",
            "- 哪些地方不成立：",
            "",
            "# 四、关键风险与误区",
            "- 风险 1：",
            "- 风险 2：",
            "- 风险 3：",
            "",
            "# 五、下一步动作",
            "- 现在最该做的动作 1：",
            "- 现在最该做的动作 2：",
            "- 现在最该做的动作 3：",
            "",
            "# 六、不确定项",
            "- 缺失信息 1：",
            "- 缺失信息 2：",
            "- 这些信息会影响哪部分判断：",
            "```",
            "",
            "## 建议用户输入模板",
            "",
            "```md",
            f"请你扮演《{title}》课程专家，帮我处理下面这个实际问题：",
            "",
            "1. 我的具体问题/项目：",
            "2. 我的目标：",
            "3. 我已知的信息：",
            "4. 我当前的做法或设想：",
            "5. 我最担心的点：",
            "```",
            "",
            "## 课程导出的建议输出",
            "",
        ]
    )
    for item in outputs:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate a reusable AI prompt/spec from a captured course bundle.")
    parser.add_argument("--bundle-dir", required=True, help="Capture bundle directory containing manifest.json")
    parser.add_argument("--out", help="Output markdown path; defaults to <course>-AI提示词.md inside the bundle")
    args = parser.parse_args()

    bundle_dir = Path(args.bundle_dir)
    manifest = load_manifest(bundle_dir)
    title = safe_stem(manifest.get("title_for_files") or "未命名课程")
    text = choose_source_text(manifest)
    method_card = extract_method_card(title, text)

    output_path = Path(args.out) if args.out else bundle_dir / f"{title}-AI提示词.md"
    output_path.write_text(build_prompt(method_card), encoding="utf-8")

    payload = {
        "bundle_dir": str(bundle_dir),
        "title": title,
        "course_type": method_card["course_type"],
        "role": method_card["role"],
        "prompt_path": str(output_path),
        "method_card": method_card,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
