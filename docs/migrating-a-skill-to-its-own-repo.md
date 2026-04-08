# Migrating A Skill To Its Own Repo

## 目标

把一个孵化中的 skill 从 `meta` 仓库迁移成独立仓库，同时保持职责边界清晰。

## 推荐步骤

1. 在工作区创建新的独立目录，例如 `../yitang-course-capture`
2. 从本仓库复制 `skills/<skill-name>/` 的内容到新目录
3. 为新仓库补充：
   - `README.md`
   - `tests/`
   - `examples/`
4. 在新目录中初始化 git 并连接远端
5. 在新仓库中完成首次独立提交和推送
6. 回到本仓库，把该 skill 在 [skills/README.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/README.md) 中标记为独立仓库
7. 视情况删除本仓库中的孵化副本，或保留只读镜像一小段时间

## 判断是否该迁移

满足以下任意两条，就建议迁移：

1. 这个 skill 已经可以反复使用
2. 它开始有独立测试需求
3. 它需要自己的 issue 和分支节奏
4. 它将长期维护
5. 它可能被单独分享或安装

## 迁移后的边界

迁移后：

1. skill 的实现细节留在独立仓库
2. `meta` 仓库只保留索引、模板和规则
3. 不再把 skill 的日常开发提交混进 `meta` 仓库
