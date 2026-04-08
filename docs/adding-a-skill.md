# Adding A Skill

## 目标

新增 skill 时，默认目标不是“把它塞进当前仓库”，而是：

1. 先把 skill 做成独立工作单元
2. 再把它登记到 `meta` 仓库

## 标准流程

1. 复制 `templates/skill-template/` 作为新 skill 的起点
2. 在独立目录中完成 `SKILL.md`、`agents/openai.yaml`、`references/`、`scripts/`
3. 增加该 skill 自己的 `README.md`、`tests/`、`examples/`
4. 在该 skill 目录里单独初始化 git 仓库
5. 单独连接 GitHub / Codeup 等远端
6. 验证这个 skill 能独立开发、独立测试、独立提交
7. 最后回到本仓库更新 [skills/README.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/README.md)

## 建议的独立 skill 仓库结构

```text
<skill-repo>/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
├── scripts/
├── tests/
├── examples/
└── .gitignore
```

## 本仓库中的职责

本仓库只负责：

1. 提供模板
2. 维护技能索引
3. 记录命名规范和开发约定

本仓库不负责：

1. 长期保存所有 skill 的完整实现
2. 为所有 skill 共用同一个 git 历史
3. 统一承载所有测试和依赖

## 质量门槛

一个可登记到 meta 仓库的 skill，至少应满足：

1. 触发条件明确
2. 输出目标明确
3. 有独立测试或样例验证
4. 有独立 git 仓库
5. 可以不依赖本仓库而独立工作

## 常见错误

1. 还没独立成仓库，就先把大量实现塞进 meta 仓库
2. 把人类文档和 AI 执行文档混在一起
3. 没有 `tests/` 或 `examples/` 就开始扩张
4. 用一个大仓库去承载多个不相关 skill 的实验提交
