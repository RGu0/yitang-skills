# Project Architecture

## 定位

`yitang-skills` 现在是一个 `meta` 仓库，不再承担“长期保存所有 skill 实体代码”的职责。

这个仓库主要负责四类内容：

1. 技能体系的总说明与路线图
2. 新 skill 的模板与规范
3. 各独立 skill 仓库的索引
4. 尚未拆分完成的本地孵化内容

## 推荐仓库模型

推荐使用：

1. 一个 `meta` 仓库
2. 多个独立 skill 仓库

建议工作区形态：

```text
workspace/
├── yitang-skills/                  # meta 仓库
├── yitang-course-capture/          # 独立 repo
├── yitang-demand-decomposition/    # 独立 repo
└── yitang-sales-script-builder/    # 独立 repo
```

## 这个 meta 仓库里应该有什么

### `docs/`

项目级文档，只服务于维护者和未来的协作者。

### `templates/`

独立 skill 仓库的起始模板。

### `skills/README.md`

技能索引，不是长期承载所有 skill 代码的主目录。

### `skills/<skill-name>/`

默认不再承载真实实现。若存在，通常只作为只读占位目录，指向已经拆分出去的独立 repo。

## 为什么要改成 meta 仓库

### 1. 独立开发边界更清楚

每个 skill 都应该有自己的：

1. git 历史
2. 分支策略
3. 测试目录
4. 发布节奏
5. 依赖约束

### 2. 避免 monorepo 式耦合

如果把所有 skill 长期放在一个仓库里，后面很容易出现：

1. 实验性提交互相污染
2. 测试脚本互相干扰
3. 发布和同步边界不清
4. 一个 skill 的重构拖累其他 skill

### 3. 让 meta 仓库保持轻量

`meta` 仓库最重要的是规范、模板、索引，而不是承载大量运行时代码和样例产物。

## 演进规则

后续新增 skill 时，按下面顺序做：

1. 先在 `templates/skill-template/` 基础上搭建新 skill
2. 在独立目录中开发和测试
3. 单独初始化 git 仓库并连接远端
4. 只在本仓库的 [skills/README.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/README.md) 中登记

## 当前状态

`yitang-course-capture` 已经拆分为独立仓库。`meta` 仓库中仅保留一个只读占位目录，用于索引和迁移提示。
