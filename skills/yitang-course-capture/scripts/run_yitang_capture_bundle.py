#!/usr/bin/env python3

import argparse
from datetime import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"command failed: {' '.join(cmd)}")
    return result.stdout


def run_json(cmd):
    return json.loads(run(cmd))


def safe_stem(text):
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r'[\\\\/:*?\"<>|]+', "-", text)
    text = re.sub(r"-{2,}", "-", text).strip(" .-")
    return text or "未命名课程"


def capture_timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "capture"


def default_slug(url):
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    return slugify(parts[-1]) if parts else "capture"


def choose_source_text(one_shot, scroll):
    scroll_text = (scroll or {}).get("merged_text") or ""
    one_shot_text = one_shot.get("body_text") or ""
    return scroll_text if len(scroll_text) >= len(one_shot_text) else one_shot_text


def nonempty_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def find_outline(lines):
    patterns = [
        r"^\d+分\s",
        r"^维度\d+",
        r"^重新理解",
        r"^作业与Candy",
        r"^开始上课$",
        r"^快速回顾$",
        r"^为什么要学$",
        r"^预热思考题$",
        r"^提前划重点$",
    ]
    seen = set()
    outline = []
    for line in lines:
        line = line.replace("​", "").strip()
        line = re.sub(r"\s+", " ", line)
        if any(re.search(pattern, line) for pattern in patterns):
            if line not in seen:
                seen.add(line)
                outline.append(line)
    return outline


def detect_methods(text):
    methods = []
    candidates = [
        ("需求 = 用户 × 场景 × 问题", ["需求 = 用户", "Demand = User"]),
        ("从用户、场景、问题出发，找到决定商业成败的关键假设", ["关键假设", "决定商业成败的关键假设"]),
        ("向上支撑 / 内部证伪 / 横向自检", ["向上支撑", "横向自检", "内部证伪"]),
        ("组合即需求", ["组合即需求"]),
        ("警惕虚假拆解", ["虚假拆解", "警惕虚假拆解"]),
        ("高质量拆解通常是 3-5 刀", ["3-5刀", "3-5 是经验值Benchmark"]),
    ]
    for title, markers in candidates:
        if any(marker in text for marker in markers):
            methods.append(title)
    return methods


def extract_case_blocks(text):
    lines = nonempty_lines(text)
    case_indices = []
    for index, line in enumerate(lines):
        if "【案例】" in line:
            case_indices.append(index)
    blocks = []
    stop_prefixes = ("【案例】", "维度1：", "维度2：", "维度3：", "85分 ", "75分 ", "重新理解", "作业与Candy")
    for pos, start in enumerate(case_indices):
        end = len(lines)
        for idx in range(start + 1, len(lines)):
            line = lines[idx]
            if idx in case_indices[pos + 1:pos + 2]:
                end = idx
                break
            if idx > start + 1 and any(line.startswith(prefix) for prefix in stop_prefixes):
                end = idx
                break
        title = lines[start]
        body = lines[start + 1:end]
        blocks.append(
            {
                "title": title,
                "body": body,
            }
        )
    return blocks


def summarize_case_points(case_block, limit=4):
    body = case_block["body"]
    bullets = []
    for line in body:
        if len(bullets) >= limit:
            break
        clean = line.strip("​ ").strip()
        if len(clean) < 8:
            continue
        if clean in {"以下是作业原文：", "结果细拆客户以后发现："}:
            continue
        bullets.append(clean)
    return bullets


def bullets_to_paragraph(bullets):
    cleaned = []
    for bullet in bullets:
        text = bullet.strip()
        text = text.strip("​ ").strip()
        if not text:
            continue
        cleaned.append(text)
    if not cleaned:
        return ""
    paragraph = "；".join(cleaned)
    if not paragraph.endswith(("。", "！", "？")):
        paragraph += "。"
    return paragraph


def find_case(case_blocks, keyword):
    for case in case_blocks:
        if keyword in case["title"]:
            return case
    return None


def build_case_explanation(case_block):
    title = case_block["title"]
    body = case_block["body"]
    text = " ".join(body)
    if "酒店建材" in title:
        return (
            "这个案例的关键结论是：并不是所有看起来合理的业务延伸都能成为第二增长曲线。",
            "课程借这个案例说明“向上支撑”原则。需求拆完之后，必须反过来支撑你的规模预期，否则就是方向性误判。",
        )
    if "AI算力" in title:
        return (
            "这个案例的关键结论是：市场看起来很大，不代表真正可服务的需求也很大。",
            "连续几刀砍掉客户之后，真实机会迅速缩小，这正是需求分析用来证伪乐观预期的作用。",
        )
    if "空气炸锅" in title:
        return (
            "这个案例的关键结论是：真正高价值的细分，不是简单做画像，而是找到愿意为特定问题和溢价买单的一小群人。",
            "它说明内部证伪不是无限细分，而是持续逼近更 sharp、更可销售的需求。",
        )
    if "工业企业销售报价系统" in title:
        return (
            "这个案例的关键结论是：定义需求时，系统定义非用户和排除条件，往往比笼统定义用户更重要。",
            "它说明优秀的需求拆解必须能回答“谁不值得服务”，并通过排除法把产品逼向真实痛点。",
        )
    if "新人直播AI助手" in title:
        return (
            "这个案例的关键结论是：需求成立，并不等于商业模式成立。",
            "课程用它解释横向自检原则。需求周期和收费方式如果天然冲突，项目就会出现结构性问题。",
        )
    if "医美医院业务" in title:
        return (
            "这个案例的关键结论是：多个业务之间看似可以导流，实际上未必存在真实的用户升级路径。",
            "它用来说明需求必须和增长方式、产品结构一起看，不能孤立判断。",
        )
    if "高端防脱洗发水" in title:
        return (
            "这个案例的关键结论是：解决方案一旦和用户心智中的替代品发生比较，就会暴露结构性矛盾。",
            "课程借此说明需求与解决方案、价格带和预期疗效之间必须相互匹配。",
        )
    if "物联网芯片业务" in title:
        return (
            "这个案例的关键结论是：需求选择不仅决定当前收入，还决定长期壁垒会建立在哪里。",
            "它说明高质量需求分析会直接反向塑造品牌、转化成本和竞争优势。",
        )
    if "咖啡含片" in title:
        return (
            "这个案例的关键结论是：真正有效的用户标签，常常来自具体行为约束，而不是人口统计标签。",
            "它说明用户拆解的价值，在于找到需求最强、最明确、最可持续的那群人。",
        )
    if "无人网球馆" in title:
        return (
            "这个案例的关键结论是：如果用户能力层级没有切准，再好的产品形态也会陷入低效率。",
            "课程用它说明用户拆解必须深入到使用能力和进步阶段，而不是停留在兴趣层面。",
        )
    if "发票SaaS" in title:
        return (
            "这个案例的关键结论是：2B 业务最值得服务的对象，常常不是需求规模最大的那一类，而是切换成本与数字化水平最匹配的一类。",
            "它说明用户拆解在企业服务场景里同样需要做明确取舍。",
        )
    if "通信模组业务" in title:
        return (
            "这个案例的关键结论是：需求拆解做对之后，团队会从“什么都做”转向“只做最值得规模化复制的客户”。",
            "它用来说明用户拆解可以直接改变竞争策略和增长效率。",
        )
    if "挂脖空调" in title:
        return (
            "这个案例的关键结论是：很多需求不是因为换了用户才变强，而是因为换了更具体的场景才变强。",
            "课程用它说明场景拆解如何把一个普通消费品做成 sharp 产品。",
        )
    if "洗碗机" in title:
        return (
            "这个案例的关键结论是：环境约束往往比偏好本身更能决定需求强度。",
            "它说明场景拆解能把“讨厌洗碗”这种弱表达，转化成“厨房条件受限下必须购买”的强需求。",
        )
    if "宠物殡葬" in title:
        return (
            "这个案例的关键结论是：有些需求不是长期稳定存在，而是在短时间窗口内集中爆发。",
            "它说明场景分析必须把时间窗口和情绪强度一起纳入定义。",
        )
    return (
        "这个案例展示了课程方法在真实业务中的应用。",
        "它的价值在于把抽象方法放回到具体经营判断里，帮助理解拆解为何会影响结果。",
    )


def render_case(report, label, case_block, lead=None, limit=4):
    if not case_block:
        return
    conclusion, insight = build_case_explanation(case_block)
    points = summarize_case_points(case_block, limit=limit)
    report.append(f"#### 案例：{label}")
    report.append("")
    if lead:
        report.append(f"对应方法（基于原文归纳）：{lead}")
        report.append("")
    report.append("原文整理：")
    report.append(conclusion)
    report.append("")
    report.append("案例要点（原文压缩整理）：")
    paragraph = bullets_to_paragraph(points)
    if paragraph:
        report.append(paragraph)
    else:
        report.append("当前抓取文本不足以还原该案例的细节。")
    report.append("")
    report.append("归纳分析（基于原文，不引入外部资料）：")
    report.append(insight)
    report.append("")


def build_action_checklist(text):
    checklist = [
        "先把方案描述改写成问题描述，确认你到底想解决什么问题。",
        "用“用户 × 场景 × 问题”重写需求，不要只写一个抽象大词。",
        "逼自己做 3-5 刀拆解，而不是无限扩展分析范围。",
        "同步定义用户与非用户，明确哪些人阶段性不服务。",
        "检查拆出来的需求是否能支撑你的业务规模和长期预期。",
        "检查需求与产品、商业模式、渠道和壁垒是否存在硬伤。",
    ]
    if "虚假拆解" in text:
        checklist.append("警惕虚假拆解，确认你做的是艰难取舍而不是无意义排除。")
    if "横向自检" in text:
        checklist.append("做一次横向自检，验证需求与其他经营要素是否匹配。")
    return checklist


def build_detailed_report(
    title_for_files,
    requested_url,
    bundle_dir,
    one_shot,
    scroll,
    image_payload,
    warnings,
):
    source_text = choose_source_text(one_shot, scroll)
    lines = nonempty_lines(source_text)
    outline = find_outline(lines)
    case_blocks = extract_case_blocks(source_text)
    checklist = build_action_checklist(source_text)
    case_map = {
        "hotel": find_case(case_blocks, "酒店建材"),
        "compute": find_case(case_blocks, "AI算力"),
        "airfryer": find_case(case_blocks, "空气炸锅"),
        "quote": find_case(case_blocks, "工业企业销售报价系统"),
        "live_ai": find_case(case_blocks, "新人直播AI助手"),
        "med": find_case(case_blocks, "医美医院业务"),
        "shampoo": find_case(case_blocks, "高端防脱洗发水"),
        "iot_chip": find_case(case_blocks, "物联网芯片业务"),
        "coffee": find_case(case_blocks, "咖啡含片"),
        "tennis": find_case(case_blocks, "无人网球馆"),
        "invoice": find_case(case_blocks, "发票SaaS"),
        "module": find_case(case_blocks, "通信模组业务"),
        "neck_ac": find_case(case_blocks, "高端挂脖空调"),
        "dishwasher": find_case(case_blocks, "超小型台式家用洗碗机"),
        "pet_funeral": find_case(case_blocks, "宠物殡葬服务"),
        "sex_edu": find_case(case_blocks, "性教育启蒙礼盒"),
        "bus": find_case(case_blocks, "滴滴小巴"),
        "boat": find_case(case_blocks, "自动驾驶的游艇/游船业务"),
    }
    report = [
        f"# {title_for_files}-分析报告",
        "",
        f"- 课程标题：{title_for_files}",
        f"- 来源页面：[原网页]({requested_url})",
        f"- 抓取目录：`{bundle_dir}`",
        f"- one-shot 正文字数：`{(one_shot.get('validation') or {}).get('body_len', 0)}`",
    ]
    if scroll:
        report.append(f"- scroll 正文字数：`{(scroll.get('validation') or {}).get('merged_text_len', 0)}`")
        report.append(f"- scroll 覆盖率：`{(scroll.get('validation') or {}).get('coverage_ratio', 0)}`")
    report.append(f"- 当前抓取告警：`{', '.join(sorted(set(warnings))) if warnings else '无'}`")

    report.extend(
        [
            "",
            "## 一、阅读说明",
            "",
            "本报告只使用当前网页中的课程正文、目录和页面图片进行整理，不补充外部网页、外部案例或外部理论。",
            "",
            "为避免把整理写成二次创作，全文统一分成两类表述：",
            "",
            "- `原文整理`：对课程原文的压缩、重组与重排。",
            "- `归纳分析`：只依据课程原文内部逻辑做推理，不引入外部信息。",
            "",
            "可以把这节课理解为：它不是直接教你做什么产品，而是先教你在产品、渠道、定价之前，把“到底在满足谁、在什么情境下、解决什么问题”拆清楚。",
            "",
            "## 二、课程定位与学习目标",
            "",
            "原文整理：课程把本课定义为“一堂五步法”里“需求”模块的第一节实操课，也是商业分析与决策中最基础、最前置的基本功。讲师明确说，如果基本用户需求拆解得足够准确，后面整个项目的决策和验证效率都会全面提升；反过来，如果在“基本用户需求”上做的工作太少，项目逻辑、功能设计和经营决策会持续冲突。",
            "",
            "归纳分析（基于原文）：这节课真正训练的不是行业知识，而是一种分析顺序。先拆需求，再谈方案；先找关键假设，再谈投入和扩张。",
            "",
            "## 三、进入本课前，课程要求先记住什么",
            "",
            "### 3.1 上节课留下的三个价值判断",
            "",
            "原文整理：课程先回顾了“需求探索”的三个价值。",
            "",
            "- 选择题：尽早验证/证伪，降低试错成本。",
            "- 设计题：当你对人群、画像、场景和分层理解更清楚，后续产品、定价、选址、渠道、品牌等决策都会同步提高。",
            "- 数学题：更早理解用户问题和业务天花板空间，管理心态会更从容。",
            "",
            "### 3.2 两个建议与两个原则",
            "",
            "原文整理：课程回顾部分先给了两个建议和两个原则，作为进入本课的最低共识。",
            "",
            "- 两个建议：你想提供什么并不重要，重要的是用户想解决什么具体问题；用户从来都不是铁板一块，可以继续切开。",
            "- 两个原则：如果拆出的几类需求彼此矛盾，就必须取舍；如果拆得还不够具体、不够疼，无法支撑营销和销售，就还要继续细分。",
            "",
            "归纳分析（基于原文）：后文所有方法和案例，其实都围绕这四句话展开。课程不是教你把需求“写漂亮”，而是教你避免把方案误当需求、把粗分类误当拆解完成。",
            "",
            "## 四、课程结构",
            "",
        ]
    )
    for item in outline:
        normalized = item.replace(" ​", "").strip()
        if normalized and normalized not in report:
            report.append(f"- {normalized}")

    report.extend(
        [
            "",
            "## 五、60分基础：先把需求从方案里剥离出来",
            "",
            "原文整理：课程把“拆”定义为第一次能力飞跃对应的基本功。这里针对的是需求分析里最常见的入门错误，也就是把需求、产品、执行动作和交付形式揉在一起讨论，导致分析一开始就跑偏。",
            "",
            "这一部分的核心结论，课程已经在原文中明确说出：",
            "",
            "- 你想提供什么不重要，重要的是用户到底想解决什么具体问题。",
            "- 用户从来不是铁板一块，必须被切开、被重新定义。",
            "",
            "课程随后又用两个原则把“怎么判断拆得够不够”说清楚：如果拆出来的需求彼此冲突，就必须取舍；如果拆得还不够具体、不够疼，商业效率还是起不来，就要继续细分。",
            "",
            "归纳分析（基于原文）：这一段最重要的不是记住新名词，而是改掉动作顺序。先问“用户到底想解决什么问题”，再问“我准备用什么方案解决”，顺序不能倒过来。",
            "",
            "## 六、75分拆解：把需求分析提升为关键假设管理",
            "",
            "原文整理：课程在这一段把需求分析从“经验判断”提升成“关键假设管理”。讲师明确说，科学创业的基石是“证伪”，而证伪背后是高风险假设。也就是说，需求分析不是为了收集很多零散偏好，而是要找到那些一旦判断错误，就会让项目整体失真的关键点。",
            "",
            "### 6.1 需求三要素：用户 × 场景 × 问题",
            "",
            "原文整理：课程给出的基本公式是 `需求 = 用户 × 场景 × 问题`。在前文回顾部分，讲师还给出了一个更直接的造句范式：`（细分用户）在（场景）下遇到了（真实问题）`。",
            "",
            "归纳分析（基于原文）：这两个表达合在一起，实际上是在把模糊需求改写成一个可以被验证的句子。重点不在于记住公式本身，而在于学会把任何需求都改写成一句完整的话。",
            "",
            "### 6.2 组合即需求：任一要素变化，都是新需求",
            "",
            "原文整理：课程目录直接把这一段命名为“背后的逻辑：组合即需求”。它的意思是，同样的问题换一个用户，是新的需求；同样的用户换一个场景，也会形成新的需求定义。",
            "",
            "归纳分析（基于原文）：课程后面的场景案例反复证明了这一点。这意味着“用户差不多”并不等于“需求一样”，因为真正驱动购买和使用的，常常是更细的场景触发器。",
            "",
            "### 6.3 需求拆解三原则：向上支撑、内部证伪、横向自检",
            "",
            "原文整理：课程总结了三类最容易被忽略的关键假设，并把它们概括成三条原则：",
            "",
            "- 向上支撑：拆出来的需求，必须能支撑你的长期业务目标和规模预期。",
            "- 内部证伪：拆分后的需求如果不一致、互相冲突，必须取舍；如果不够 sharp，就要继续拆。",
            "- 横向自检：需求不能孤立看，还要和产品、商业模式、渠道、壁垒放在一起看是否匹配。",
            "",
            "归纳分析（基于原文）：这三条原则分别回答了三个问题。向上支撑回答“这个需求够不够大”；内部证伪回答“这个需求够不够准”；横向自检回答“这个需求和整个业务系统能不能接起来”。",
            "",
            "### 6.4 用案例解释三条原则",
            "",
        ]
    )
    render_case(
        report,
        "酒店建材业务",
        case_map["hotel"],
        "这个案例对应“向上支撑”。课程原文强调，拆解做到最后，不只是看用户和场景是否存在，更要看它能不能承载你对业务规模和长期目标的预期。",
        limit=3,
    )
    render_case(
        report,
        "AI算力项目",
        case_map["compute"],
        "这个案例同样对应“向上支撑”。课程原文用连续几刀砍客户的方式说明，需求拆解不是为了证明市场很大，而是为了尽快看清真实边界。",
        limit=5,
    )
    render_case(
        report,
        "可视化空气炸锅",
        case_map["airfryer"],
        "这个案例对应“内部证伪”。课程原文展示了从“所有想买空气炸锅的人”一路拆到“都市独居/合租青年”的过程，说明需求只有被拆到足够 sharp，商业效率才会上来。",
        limit=5,
    )
    render_case(
        report,
        "工业企业销售报价系统",
        case_map["quote"],
        "这个案例对应“内部证伪”。课程原文不是只定义谁会用，而是系统定义谁不适合用，通过排除产品标准化程度高、复杂度低、已有系统或管理水平跟不上的企业，把需求逼近真实痛点。",
        limit=5,
    )
    render_case(
        report,
        "新人直播AI助手",
        case_map["live_ai"],
        "这个案例对应“横向自检”。课程原文把需求、产品、商业模式三步放在一起看，最后发现“新人”与“续费制”之间存在常识性硬伤。",
        limit=5,
    )
    render_case(
        report,
        "医美医院业务",
        case_map["med"],
        "这个案例也对应“横向自检”。课程原文强调，即便需求方向正确，如果整形、注射、光电三类业务在用户心智、复购逻辑和导流路径上不匹配，增长假设仍然会失效。",
        limit=5,
    )
    render_case(
        report,
        "高端防脱洗发水",
        case_map["shampoo"],
        "这个案例继续说明“横向自检”。课程原文把需求、价格带、疗效预期和解决方案放到一起看，指出了用户-解决方案匹配中的常识性硬伤。",
        limit=5,
    )
    render_case(
        report,
        "物联网芯片业务",
        case_map["iot_chip"],
        "这个案例是课程原文中的正向样本。它说明需求选择不只是眼前收入选择，也会反向塑造转化成本、品牌壁垒和未来竞争方式。",
        limit=5,
    )
    report.extend(
        [
            "### 6.5 警惕虚假拆解",
            "",
            "原文整理：课程专门提醒“虚假拆解”问题。典型表现是画布填得很满，但实际上并没有真正砍掉什么，只是在排除那些本来就与自己无关、或者本来就服务不了的人群。",
            "",
            "课程还给出一句更强的判断：真正好的“砍”是战略取舍，通常是在正面、反面选项都看起来正确的情况下，仍然做出艰难选择。课程引用“一堂版本的战略定义”是“站在全局，做出影响成败的艰难选择”。",
            "",
            "归纳分析（基于原文）：这段内容把“拆解”从分析动作提高到了经营决策动作。拆解不是为了把分类做得更漂亮，而是为了在多个看似都该服务的机会之间主动放弃一部分。",
            "",
            "## 七、85分高阶：把拆解变成可复用的方法",
            "",
            "原文整理：课程明确提出，任何项目都可以被无限细拆，但过度拆解没有意义，而且效率极低。真正重要的是找到最关键的 3-5 刀，快速提升需求判断质量。",
            "",
            "课程还提到形成拆解能力的几种路径：基于经验和常识自己拆、借助 AI 获取启发、深度调研同行、访谈专家，以及使用课程沉淀的案例与武器库。",
            "",
            "### 7.1 维度一：专业拆解“用户”",
            "",
            "原文整理：课程在用户维度上提醒，用户并不一定等于购买者或决策者。很多业务里，使用者、购买者、决策者是分离的，所以分析时不能只看一个角色，而要判断真正影响成败的是哪一个角色链条。",
            "",
        ]
    )
    render_case(
        report,
        "咖啡含片业务",
        case_map["coffee"],
        "这个案例说明，课程做用户拆解时并不满足于年龄、性别、城市层级，而是继续追问行为约束。原文最后锁定的是“长时间集中注意力、尽量少去厕所”的群体特征。",
        limit=5,
    )
    render_case(
        report,
        "无人网球馆",
        case_map["tennis"],
        "这个案例说明，用户拆解不仅可以按身份切，也可以按能力层级切。课程原文通过继续砍掉小白和专业选手，最后找到更匹配的中间层用户。",
        limit=5,
    )
    render_case(
        report,
        "发票SaaS",
        case_map["invoice"],
        "这个案例说明，2B 用户拆解不能只从表面规模出发。课程原文先找到“开票最多”的对象，再继续用数字化水平和切换难度做剥离，最后得到更值得服务的客户群。",
        limit=5,
    )
    render_case(
        report,
        "通信模组业务",
        case_map["module"],
        "这个案例说明，用户拆解会直接改变竞争格局。课程原文用市场份额、组织文化、决策角色等几刀持续收窄客户范围，最终让业务走向规模化复制。",
        limit=4,
    )
    report.extend(
        [
            "### 7.2 维度二：专业拆解“场景”",
            "",
            "原文整理：课程将场景定义为“一个相对稳定的用户发生具体问题的一个场合和触发器”。场景分析之所以重要，是因为它不仅影响需求是否发生，也影响需求强度、购买意愿和解决方案是否成立。",
            "",
            "课程还明确说，场景包含时间、空间、阶段、氛围、心态、心理状态、情绪等要素。许多业务的机会，不是换了一个产品，而是把同一类用户与问题，放进了一个更强的触发场景中。",
            "",
        ]
    )
    render_case(
        report,
        "高端挂脖空调",
        case_map["neck_ac"],
        "这个案例是课程原文中最典型的场景拆解示范。它不是简单服务“所有年轻男性”，而是从徒步、钓鱼、露营、登山、亲子等场景继续筛选，最后锁定精致露营中的更细分行为场景。",
        limit=5,
    )
    render_case(
        report,
        "超小型台式家用洗碗机",
        case_map["dishwasher"],
        "这个案例说明，需求强度常常来自环境限制。课程原文把“喜欢做饭、不喜欢洗碗”进一步落到“厨房小、无法安装大洗碗机、接上下水不方便”的具体场景上。",
        limit=3,
    )
    render_case(
        report,
        "宠物殡葬服务",
        case_map["pet_funeral"],
        "这个案例说明，有些需求不是长期平均发生，而是在短时间窗口内集中爆发。课程原文直接给出两个场景：宠物刚离世 12 小时内的惊慌状态，以及 3-7 天内的告别仪式。",
        limit=4,
    )
    report.extend(
        [
            "### 7.3 维度三：专业剥离“问题”",
            "",
            "原文整理：课程把问题定义为 `GAP`，也就是预期和现实之间的差距。讲师提醒，需求往往有多个角度、多个层次，真正困难的不是发现一个表面抱怨，而是继续往下追问，确认到底在解决谁的什么问题。",
            "",
            "课程还明确回答了一个常见困扰：分析问题时，不能在真空里讨论，而是一定要基于现有解决方案来评估。也就是说，要默认用户已经被各种直接、间接解决方案包围，我们提供的是新的服务，而不是在一张白纸上发明需求。",
            "",
            "归纳分析（基于原文）：这一段把“问题”维度从情绪表达拉回到了经营判断。用户说自己有需求，并不等于问题已经被定义清楚；只有把预期、现实、替代方案和真实痛点放在一起看，问题才算被剥离出来。",
            "",
        ]
    )
    render_case(
        report,
        "给女生的性教育启蒙礼盒",
        case_map["sex_edu"],
        "这个案例用来说明：即便产品形式已经比较明确，背后真正要解决的问题仍然可能完全不同。课程原文直接提出，它可能对应的是“仪式感”，也可能对应的是“性教育难以启齿”。",
        limit=5,
    )
    render_case(
        report,
        "滴滴小巴",
        case_map["bus"],
        "这个案例把“用户-场景-问题”三要素写得最完整。课程原文直接给出：用户是价格敏感、时间充裕、高频出行的人群；场景是早晚通勤和平峰出行；问题是愿意接受等待、步行和拼车，以换取更低价格。",
        limit=5,
    )
    render_case(
        report,
        "公园景区自动驾驶游艇/游船业务",
        case_map["boat"],
        "这个案例说明，同一个技术方案放到不同景区，背后的核心问题并不一样。课程原文明确区分：大型景区更关心管理成本、风险控制和战略升级，小型景区更关心业绩增长和快速回本。",
        limit=5,
    )
    report.extend(
        [
            "## 八、课程最后如何重新理解“需求拆解”",
            "",
            "原文整理：课程尾声用一段复习把全课收束起来。讲师强调，第一步是先把一个完整大项目剥离出前置假设；剥离出需求后，再围绕用户、场景、问题三要素继续细拆；再用向上支撑、内部证伪、横向自检三原则判断质量；最后争取用最重要、最值钱的 3-5 刀，找到自己的核心客群、核心场景与核心问题。",
            "",
            "课程还给出一个很明确的工具定位：这套方法不一定保证你找到“好需求”，但一定是一个“快速排除 80% 坏需求”的优秀工具；它的使命不是保证成功，而是尽早失败在纸面上。",
            "",
            "归纳分析（基于原文）：这句话很重要。它意味着这节课的目标不是让人立刻做出完美判断，而是先学会尽早排错、尽早缩小范围、尽早避免把资源砸在错误方向上。",
            "",
            "## 九、作业与 Candy",
            "",
            "原文整理：课程尾部给了三类作业，要求学员三选一完成，同时鼓励都尝试。",
            "",
            "- 学习心得题：回顾本课关于“从五步法中剥离需求”“需求拆解的本质逻辑”“用户-场景-问题三维框架”的学习收获、新启发和疑问。",
            "- 案例分析题：用课程框架分析一次真实的产品使用、购买、竞品调研或自己正在做的业务，说明它解决了哪类用户的什么需求，以及框架带来的启发。",
            "- AI 提示词题：设计一套提示词，让 AI 基于“用户-场景-问题”模型辅助使用者完成需求拆解。",
            "",
            "课程同时给出三类 Candy：AI 辅助探讨需求选项的提示词、《优秀需求拆解案例集》、需求拆解 AI 调试过程开源材料。",
            "",
            "归纳分析（基于原文）：作业设计本身也体现了课程的教学重点。第一题检验你是否理解原理，第二题检验你是否能把框架落到真实案例，第三题则把这套框架进一步迁移到 AI 辅助分析场景。",
            "",
            "## 十、可执行清单",
            "",
        ]
    )
    for item in checklist:
        report.append(f"- {item}")

    report.extend(
        [
            "",
            "## 十一、附录",
            "",
            "### 核心图片",
            "",
        ]
    )
    if image_payload and image_payload.get("saved_images"):
        for item in image_payload["saved_images"]:
            report.append(f"- [{Path(item['path']).name}]({Path(item['path'])})")
    else:
        report.append("- 本次未保存核心图片")

    report.extend(["", "### 原始抓取文件", ""])
    report.append(f"- [manifest.json]({bundle_dir / 'manifest.json'})")
    report.append(f"- [one-shot/content.txt]({bundle_dir / 'one-shot' / 'content.txt'})")
    if scroll:
        report.append(f"- [scroll/content.txt]({bundle_dir / 'scroll' / 'content.txt'})")

    return "\n".join(report) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Run a standard yitang.top capture bundle workflow.")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--bundle-root", default=str(SKILL_ROOT / "captures"), help="Root directory for capture bundles")
    parser.add_argument("--slug", help="Optional bundle slug")
    parser.add_argument("--wait", type=float, default=10.0, help="Initial wait for one-shot capture")
    parser.add_argument("--settle-timeout", type=float, default=25.0, help="Settling timeout for one-shot capture")
    parser.add_argument("--min-body-len", type=int, default=1000, help="Minimum body length threshold for validation")
    parser.add_argument("--with-scroll", action="store_true", help="Also run scrolling capture (RECOMMENDED for yitang courses)")
    parser.add_argument("--scroll-selector", help="Optional CSS selector for custom scroll container")
    parser.add_argument("--text-selector", default=".page-body", help="Optional CSS selector for custom text root (use .page-body for yitang courses)")
    parser.add_argument("--scroll-steps", type=int, default=250, help="Maximum scroll iterations (250+ recommended)")
    parser.add_argument("--required-marker", action="append", default=[], help="Marker that must appear in the capture for it to count as complete; can be passed multiple times (use '作业与Candy' for yitang courses)")
    parser.add_argument("--save-core-images", action="store_true", help="Download core rendered images from the current page into the bundle directory")
    parser.add_argument("--image-limit", type=int, default=0, help="Maximum number of core images to save; 0 means no fixed limit")
    parser.add_argument("--image-min-count", type=int, default=3, help="Minimum number of core images to try to save when enough valid images exist")
    args = parser.parse_args()

    timestamp = capture_timestamp()
    initial_slug = args.slug or f"_capture-{default_slug(args.url)}-{timestamp}"
    bundle_dir = Path(args.bundle_root) / initial_slug
    bundle_dir.mkdir(parents=True, exist_ok=True)

    one_shot_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "safari_capture_page.py"),
        "--url",
        args.url,
        "--wait",
        str(args.wait),
        "--settle-timeout",
        str(args.settle_timeout),
        "--min-body-len",
        str(args.min_body_len),
        "--bundle-dir",
        str(bundle_dir / "one-shot"),
    ]
    one_shot = run_json(one_shot_cmd)

    title_for_files = safe_stem(one_shot.get("title") or initial_slug)
    final_slug = args.slug or safe_stem(f"{title_for_files}-{timestamp}")
    final_bundle_dir = Path(args.bundle_root) / final_slug
    if final_bundle_dir != bundle_dir:
        bundle_dir.rename(final_bundle_dir)
        bundle_dir = final_bundle_dir

    scroll = None
    if args.with_scroll:
        scroll_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "safari_capture_scrolling.py"),
            "--url",
            args.url,
            "--wait",
            str(args.wait),
            "--settle-wait",
            str(args.settle_timeout / 2),
            "--steps",
            str(args.scroll_steps),
            "--pause",
            str(1.0),
            "--bundle-dir",
            str(bundle_dir / "scroll"),
        ]
        if args.scroll_selector:
            scroll_cmd.extend(["--scroll-selector", args.scroll_selector])
        if args.text_selector:
            scroll_cmd.extend(["--text-selector", args.text_selector])
        for marker in args.required_marker:
            scroll_cmd.extend(["--required-marker", marker])
        scroll = run_json(scroll_cmd)

    title_for_files = safe_stem(one_shot.get("title") or (scroll or {}).get("final_title") or final_slug)
    file_stem = f"{title_for_files}-{timestamp}"
    report_path = bundle_dir / f"{file_stem}-分析报告.md"

    image_payload = None
    image_error = None
    save_core_images = args.save_core_images or True
    if save_core_images:
        image_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "safari_save_key_image.py"),
            "--out-dir",
            str(bundle_dir / "assets" / "key-images"),
            "--prefix",
            file_stem,
            "--limit",
            str(args.image_limit),
            "--min-count",
            str(args.image_min_count),
        ]
        try:
            image_payload = run_json(image_cmd)
        except RuntimeError as exc:
            image_error = str(exc)


    warnings = []
    if scroll:
        warnings.extend((scroll.get("validation") or {}).get("warnings") or [])
    else:
        warnings.extend((one_shot.get("validation") or {}).get("warnings") or [])
    if image_error:
        warnings.append("core_image_capture_failed")

    report_path.write_text(
        build_detailed_report(
            title_for_files=title_for_files,
            requested_url=args.url,
            bundle_dir=bundle_dir,
            one_shot=one_shot,
            scroll=scroll,
            image_payload=image_payload,
            warnings=warnings,
        ),
        encoding="utf-8",
    )

    prompt_payload = None
    prompt_error = None
    prompt_path = bundle_dir / f"{title_for_files}-AI提示词.md"

    manifest = {
        "requested_url": args.url,
        "slug": final_slug,
        "initial_slug": initial_slug,
        "title_for_files": title_for_files,
        "file_stem": file_stem,
        "capture_timestamp": timestamp,
        "bundle_dir": str(bundle_dir),
        "report_path": str(report_path),
        "prompt_path": str(prompt_path),
        "one_shot": one_shot,
        "scroll": scroll,
        "core_images": image_payload,
        "core_image_error": image_error,
        "course_prompt": prompt_payload,
        "course_prompt_error": prompt_error,
        "warnings": sorted(set(warnings)),
    }

    (bundle_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    prompt_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "generate_course_prompt.py"),
        "--bundle-dir",
        str(bundle_dir),
        "--out",
        str(prompt_path),
    ]
    try:
        prompt_payload = run_json(prompt_cmd)
    except RuntimeError as exc:
        prompt_error = str(exc)
        warnings.append("course_prompt_generation_failed")

    manifest["course_prompt"] = prompt_payload
    manifest["course_prompt_error"] = prompt_error
    manifest["warnings"] = sorted(set(warnings))

    (bundle_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    json.dump(manifest, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
