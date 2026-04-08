
# Yitang 技能修改总结

## 修改日期
2026年4月7日

## 修改原因
根据实际使用体验，原技能在处理一堂课程页面时存在以下问题：
1. Safari JavaScript 权限配置文档不够详细
2. 页面加载时间预估不足
3. 滚动步骤参数不够优化
4. 缺少对一堂课程页面类型的明确区分
5. 缺少完整的故障排查流程

## 修改内容

### 1. SKILL.md - 主文档优化

#### 新增内容
- **3.1 环境准备（关键！）**：详细的 Safari 配置说明
- **3.2 页面分类优化**：区分一堂课程页面和飞书文档页面
- **3.3 优化的参数建议**：针对一堂课程页面的最佳参数组合
- **3.4 失败排查步骤**：常见问题与解决方案
- **4.1 最佳实践：完整流程**：完整的分步捕获指南
- **4.2 使用 run_yitang_capture_bundle.py 优化版本**：推荐的综合命令
- **4.3 调试和验证**：检查和验证工具
- **4.4 常见问题修复**：问题快速修复指南

### 2. references/yitang-feishu-capture.md - 参考文档优化

#### 修改内容
- **Common Patterns**：拆分为两种页面类型的说明
  - 1. 一堂课程页面（Vue 渲染）
  - 2. 飞书文档嵌入页面

### 3. scripts/safari_capture_page.py - 基础捕获脚本优化

#### 默认参数调整
```python
--wait: 2.0 → 10.0
--settle-timeout: 20.0 → 30.0
--poll-interval: 1.0 → 1.5
--stable-rounds: 2 → 3
--min-body-len: 500 → 1000
```

### 4. scripts/safari_capture_scrolling.py - 滚动捕获脚本优化

#### 默认参数调整
```python
--wait: 3.0 → 10.0
--settle-wait: 2.0 → 8.0
--steps: 120 → 250
--text-selector: (无默认) → ".page-body"
--pause: 0.8 → 1.0
```

### 5. scripts/run_yitang_capture_bundle.py - 协调脚本优化

#### 默认参数调整
```python
--wait: 2.0 → 10.0
--settle-timeout: 20.0 → 25.0
--min-body-len: 500 → 1000
--text-selector: (无默认) → ".page-body"
--scroll-steps: 120 → 250
```

#### 滚动捕获命令参数传递优化
- 增加 `--wait` 和 `--settle-wait` 参数传递
- 增加 `--pause` 参数（1.0秒）

## 优化效果预期

### 成功率提升
- 原成功率：约 30%（基于本次体验）
- 优化后预期：约 90%+

### 主要提升点
1. **环境配置更清晰**：用户清楚知道需要做哪些配置
2. **参数更合理**：页面有足够时间加载
3. **滚动更完整**：增加了滚动步数和间隔
4. **目标更明确**：使用 `.page-body` 选择器精确定位内容
5. **故障排查更方便**：提供了完整的问题解决流程

## 推荐使用方式

### 快速开始（推荐）
```bash
cd '/Users/rui/Documents/0. AI/调研/yitang-top-course-skill' && 
python3 scripts/run_yitang_capture_bundle.py \
  --url "https://yitang.top/fs-doc/..." \
  --with-scroll \
  --save-core-images \
  --bundle-root ./captures \
  --slug lesson_name \
  --required-marker "作业与Candy"
```

### 高级使用（更灵活）
```bash
cd '/Users/rui/Documents/0. AI/调研/yitang-top-course-skill' && 
python3 scripts/safari_capture_scrolling.py \
  --url "https://yitang.top/fs-doc/..." \
  --wait 12 \
  --settle-wait 8 \
  --steps 250 \
  --pause 1 \
  --text-selector ".page-body" \
  --bundle-dir ./captures/lesson_name \
  --required-marker "作业与Candy"
```

## 注意事项

1. **首次使用前务必检查 Safari 配置**
   - 启用开发菜单
   - 允许 JavaScript from Apple Events

2. **确保网络连接稳定**
   - 页面加载需要网络支持
   - 内容较多时加载时间较长

3. **页面可能需要登录**
   - 确保 Safari 已登录 yitang.top 账号
   - 某些课程可能需要会员权限

4. **验证捕获完整性**
   - 检查是否包含"作业与Candy"标记
   - 确认内容长度 > 5000 字符（一堂课程通常如此）

## 后续优化建议

1. 考虑增加页面类型自动检测
2. 增加失败后自动重试机制
3. 支持增量捕获（只捕获未获取的内容）
4. 增加更智能的滚动策略（根据内容加载速度调整）
5. 提供进度条或实时反馈

---

本修改总结文档记录了对 yitang-top-course-skill 的优化过程，希望能提升后续使用的体验和成功率。
