# Skills Registry

这个目录在 `meta` 仓库中的职责是“登记和索引”，不是长期承载所有 skill 的主代码仓库。

## Registered

### `yitang-course-capture`

本地路径：
[skills/yitang-course-capture](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/yitang-course-capture)

独立仓库工作区路径：
[/Users/ruiguo/Documents/0. AI/yitang-course-capture](/Users/ruiguo/Documents/0.%20AI/yitang-course-capture)

定位：
当前已经完成独立仓库拆分。`meta` 仓库里的同名目录只保留为只读占位符。

用途：
从 `yitang.top` 课程页面抓取内容，重组为结构化 Markdown、课程讲义风格文档，以及基于课程内容生成可复用 AI prompt/spec。

仓库：
1. GitHub: `git@github.com:RGu0/yitang-course-capture.git`
2. Codeup: `git@codeup.aliyun.com:69d5ce22ad0a337b92d94581/Agent-skills/yitang-course-capture.git`

建议下一步：
1. 后续开发只在独立仓库中进行
2. 为独立仓库补真实 `examples/` 和自动化 `tests/`
3. 新 skill 直接按独立仓库模式创建

## Planned

下面这些方向适合后续直接以“独立仓库”方式创建，而不是继续堆在本仓库里：

1. `yitang-demand-decomposition`
2. `yitang-method-executor`
3. `yitang-sales-script-builder`
4. `yitang-case-analysis-rewriter`
