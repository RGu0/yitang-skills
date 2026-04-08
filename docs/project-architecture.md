# Project Architecture

## 定位

`yitang-skills` 是一个多 skill 源仓库，不是某一个单独 skill 的工作目录。

它解决三个问题：

1. 如何把不同课程拆成独立 skill
2. 如何让这些 skill 共享一致的组织方式
3. 如何让后续维护、同步和扩展成本保持可控

## 顶层分层

### `skills/`

放实际 skill，每个子目录都应该是一个可独立维护的技能单元。

单个 skill 内建议固定为：

```text
<skill-name>/
├── SKILL.md
├── agents/openai.yaml
├── references/
├── scripts/
└── assets/
```

### `templates/`

放新的 skill 起始模板，避免重复从零搭建。

### `docs/`

放项目层面的规范、架构说明、操作约定。这里的内容服务于“维护这个仓库的人”，不是服务于 skill 运行时本身。

## 为什么采用这种结构

### 1. 避免单个 skill 绑架整个仓库结构

最初仓库只有 `yitang-course-capture/`，并且 `.git` 也初始化在该目录中。这个结构只适合单 skill 阶段，不适合继续扩展。

### 2. 让 skill 成为清晰的一级对象

未来你要做的是：

1. 某门课程的网页抓取 skill
2. 某门课程的提示词拆解 skill
3. 某门课程的方法论执行 skill
4. 某个专题的分析或生成 skill

把它们统一放在 `skills/` 下，后续维护成本最低。

### 3. 分离“运行文件”和“项目说明”

Skill 本体应该保持精简，只放 AI 真正要加载、执行、参考的内容。项目规则、架构说明、贡献流程应该留在仓库根目录。

## 命名约定

1. skill 目录统一用 kebab-case，例如 `yitang-course-capture`
2. `SKILL.md` frontmatter 的 `name` 用 snake_case，例如 `yitang_course_capture`
3. `agents/openai.yaml` 的 `display_name` 用面向人的标题

## 演进建议

后续新增 skill 时，优先按“能力边界”拆，而不是按文件类型拆。

好的拆分方式：

1. `yitang-course-capture`
2. `yitang-demand-decomposition`
3. `yitang-sales-script-builder`

不建议的拆分方式：

1. `all-prompts`
2. `all-scripts`
3. `all-course-notes`

前者更便于安装、测试、迭代和复用。
