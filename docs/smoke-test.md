# 冒烟测试说明（按钮点击）

## 1. 目标
- 验证前后端服务可访问。
- 验证核心页面的主要按钮可点击且无前端报错。
- 生成可追溯的测试报告，便于回归比对。

## 2. 覆盖范围
- 列表页（`/`）
  - `绑定飞书会议`
  - `播放`
  - `+ New Item`
  - 每行 `编辑`
- 编辑页（`/editor/:id`）
  - `上一条`
  - `下一条`
  - `AI 生成口播稿、亮点与金融反思`
  - `保存`
  - `保存并开启播报`
- 数字人调试页（`/playback`）
  - 模式切换：`读取会议实时总结`、`轮播会议总结`、`会议反思`
  - 队列操作：`刷新队列`、`上一条`、`下一条`
  - 全局操作：`保存配置`、`保存并立即执行`、`打开沉浸式播报页`
  - 飞书弹层：`绑定飞书会议`、`取消`
  - 数字人调试：`从后端读取数字人配置`、`加载数字人`、`不加载数字人`
  - 高级参数区：`显示固定参数区`、`隐藏固定参数区`、`仅保存数字人参数`、`加载数字人（当前调试页）`、`清空手动配置`
- 沉浸式页（新窗口）
  - `返回调试页`（如果页面显示该按钮）

## 3. 前置条件
- Node.js 18+。
- Python 后端可启动，数据库已可连接。
- 已安装 Playwright Chromium：

```bash
cd /Users/yokichen/Documents/gmwAvatar/frontend
npx playwright install chromium
```

## 4. 执行步骤
1. 启动前后端：

```bash
cd /Users/yokichen/Documents/gmwAvatar
./scripts/dev-up.sh
```

2. 运行自动化冒烟脚本：

```bash
cd /Users/yokichen/Documents/gmwAvatar
node ./scripts/smoke-ui.mjs
```

3. 查看结果：
- Markdown 报告：`docs/smoke-test-report.md`
- JSON 报告：`docs/smoke-test-report.json`

## 5. 判定标准
- `FAIL` 为不通过，必须修复后重跑。
- `SKIP` 通常表示按钮被业务条件禁用（例如未配置 token 导致“打开沉浸式播报页”禁用），需按业务判断是否可接受。
- `PASS` 且无 `console.error/pageerror` 才可视为本轮冒烟通过。

## 6. 常见问题排查
- 前端未监听 `5174`：重新执行 `./scripts/dev-up.sh`，再用 `./scripts/dev-status.sh` 检查。
- 后端未监听 `8000`：检查 `.env`、数据库配置、后端启动日志。
- `Failed to fetch`：优先检查后端是否健康（`/healthz`）、跨域、网络代理。
