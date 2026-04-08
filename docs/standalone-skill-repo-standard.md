# Standalone Skill Repo Standard

当一个 skill 进入独立仓库时，推荐至少包含：

```text
<skill-repo>/
├── README.md
├── SKILL.md
├── agents/openai.yaml
├── references/
├── scripts/
├── tests/
├── examples/
└── .gitignore
```

## 角色分工

### `README.md`

给人看，说明这个 skill 的用途、开发方式、测试方式和仓库约定。

### `SKILL.md`

给 Codex / AI 看，说明触发条件、工作流、目标输出和按需加载的资源。

### `tests/`

放最小可验证测试，不要求一开始就非常重，但必须有基本的回归验证能力。

### `examples/`

放真实样例输入、输出，帮助验证 skill 是否可复用。

## 最低要求

一个独立 skill 仓库至少要满足：

1. 可以脱离 `meta` 仓库单独使用
2. 有自己的 git 历史
3. 有基本验证手段
4. 有明确的人类说明文档
