# Adding A Skill

## 目标

新增 skill 时，默认要做到两件事：

1. 让这个 skill 能独立工作
2. 让这个 skill 能无缝并入当前仓库

## 标准步骤

1. 复制 `templates/skill-template/` 到 `skills/<new-skill-name>/`
2. 修改 `SKILL.md.template` 为正式 `SKILL.md`
3. 修改 `agents/openai.yaml.template` 为正式 `agents/openai.yaml`
4. 补充 `references/` 中真正需要的参考资料
5. 只在确实需要稳定执行逻辑时添加 `scripts/`
6. 更新 [skills/README.md](/Users/ruiguo/Documents/0.%20AI/yitang-skills/skills/README.md)
7. 用真实任务验证一次输出质量

## 质量门槛

一个新 skill 至少应满足：

1. 触发描述明确，知道什么时候该用它
2. 工作流足够清楚，不依赖口头记忆
3. 参考资料按需加载，不把大段说明堆进 `SKILL.md`
4. 脚本只有在可重复、易出错或强依赖环境时才加入
5. 至少有一个真实使用场景验证过

## 常见错误

1. 把项目级说明写进 skill 内部
2. 在 skill 里堆很多对 AI 没帮助的 README 或 changelog
3. `SKILL.md` 过长，导致真正执行时上下文浪费
4. 目录命名、人类显示名、frontmatter 名称三者混乱
5. 还没验证真实案例就提交

## 建议节奏

先让 skill 能工作，再补模板化和抽象；不要一开始就把多个课程揉进一个巨型 skill。
