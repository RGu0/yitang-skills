# Yitang Skills

这个仓库用于沉淀“一堂课程 -> 可复用 Codex Skill”的全过程产物。

当前目标不是只维护单个 skill，而是建立一个可以持续扩展的技能源仓库：

1. 每门课程或方法论对应一个独立 skill
2. 每个 skill 保持自包含，便于单独迭代和迁移
3. 项目根目录负责统一规范、模板和索引

## 当前结构

```text
yitang-skills/
├── README.md
├── .gitignore
├── docs/
│   ├── project-architecture.md
│   └── adding-a-skill.md
├── skills/
│   ├── README.md
│   └── yitang-course-capture/
├── templates/
│   └── skill-template/
└── .contact/ .crops/ .pages/ ...
```

说明：

1. `skills/` 放实际可用的 skill
2. `templates/skill-template/` 放新 skill 的起始模板
3. `docs/` 放项目级说明，不把这类说明塞进 skill 本体
4. `.contact`、`.crops`、`.pages`、`.tmp_pdf_extract` 等目录视为本地工作产物，不纳入版本管理

## 当前 Skills

见 [skills/README.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/README.md)。

## 推荐工作流

1. 先在 `templates/skill-template/` 复制一份新目录到 `skills/<skill-name>/`
2. 编写该 skill 的 `SKILL.md`、`agents/openai.yaml`、`references/` 与必要脚本
3. 用真实课程页面验证 skill 是否能稳定产出
4. 更新 [skills/README.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/README.md) 和相关项目文档
5. 提交并同步到 GitHub

## 设计原则

1. Skill 内只放 AI 执行任务真正需要的文件
2. 项目级规范和协作说明放在仓库根目录
3. 优先让目录结构支持未来 5 个、10 个甚至更多课程 skill 并存
4. 每个 skill 都应该能被单独复制、安装、测试和迭代
