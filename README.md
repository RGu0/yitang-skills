# Yitang Skills Meta

这个仓库现在作为 `meta` 仓库使用，用来管理“一堂课程 -> 独立 skill 仓库”的体系，而不是长期承载所有 skill 的实现代码。

## 这个仓库负责什么

1. 维护整体架构和约定
2. 提供新 skill 的起始模板
3. 记录技能索引和仓库链接
4. 承载少量过渡期孵化内容

## 这个仓库不负责什么

1. 不建议长期存放所有 skill 的完整代码
2. 不建议让所有 skill 共用一个 git 历史
3. 不建议在这里统一跑所有 skill 的测试和依赖

## 推荐结构

```text
yitang-skills/
├── README.md
├── docs/
├── templates/
└── skills/
    └── README.md
```

建议在工作区中这样组织：

```text
workspace/
├── yitang-skills/               # meta 仓库
├── yitang-course-capture/       # skill 独立仓库
├── yitang-demand-decomposition/ # skill 独立仓库
└── ...
```

## 当前状态

当前仓库里仍保留了一个过渡期目录：

- [skills/yitang-course-capture](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/yitang-course-capture)

它现在应被视为：

1. 第一个 skill 的孵化副本
2. 后续拆分为独立仓库前的过渡内容

不是长期推荐的最终形态。

## 下一步推荐

1. 把 `yitang-course-capture` 拆成独立仓库
2. 在当前仓库里只保留索引、模板和规范
3. 后续每个新 skill 都直接按独立仓库方式创建

## 相关文档

1. [docs/project-architecture.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/docs/project-architecture.md)
2. [docs/adding-a-skill.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/docs/adding-a-skill.md)
3. [skills/README.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/README.md)
4. [templates/skill-template](/Users/ruiguo/Documents/0.%20AI/yitang-skills/templates/skill-template)
