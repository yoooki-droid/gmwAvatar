# gmwAvatar

多国会议数字人播报系统。

## 项目简介
本项目用于将会议总结内容转换为口播稿，并通过百度曦灵数字人进行前端播报。

核心链路：
1. 运营导入或手动创建会议总结
2. 系统生成口播稿和 1-2 条 Highlight
3. 运营在 Review 区修改并发布
4. 前端调用数字人播报并展示 Highlight

## 技术栈
- 前端：Vue 3 + Vite + TypeScript
- 后端：Python + FastAPI
- 数据库：MySQL 8.x
- 数字人：百度曦灵实时互动数字人（iframe）
- 服务器：阿里云轻量应用服务器（Ubuntu 22.04）

## 仓库结构
- `backend/`：后端技能文档与后端代码目录
- `frontend/`：前端工程目录与前端技能文档
- `DBA/`：数据库技能文档
- `docs/require.md`：需求文档
- `todo/sprint-todo.md`：Sprint 待办清单
- `baiduavatar.skills`：百度数字人接入说明
- `ref/`：参考图片与 UI 资料

## 当前服务器基线
- 主机：`47.100.20.107`
- 地域：华东2（上海）
- 配置：2 vCPU / 2 GiB / 40 GiB ESSD
- 系统：Ubuntu 22.04
- 域名：`adty.octaveliving.com`
- SSH 别名：`yoki-aliyun`

## 关键文档
- 需求文档：`docs/require.md`
- Sprint 计划：`todo/sprint-todo.md`
- 百度曦灵文档：https://cloud.baidu.com/doc/AI_DH/s/ylywx77oh

## 部署说明
详细部署记录请参考：[部署文档](docs/deploy.md)

### 生产环境信息
- **访问地址**：https://adty.octaveliving.com
- **服务器**：阿里云 (47.100.20.107)
- **部署状态**：已完成 (2026-02-15)
- **HTTPS**：已启用 (Let's Encrypt)

### 快速常用命令
**同步代码并重启服务**：
```bash
# 假设已配置 ssh config alias 'yoki-aliyun'
# 1. 更新前端
cd frontend && npm run build
rsync -avz dist/ yoki-aliyun:/var/www/gmwAvatar/frontend/

# 2. 更新后端
cd ../backend
rsync -avz --exclude '__pycache__' --exclude 'venv' --exclude '.git' . yoki-aliyun:/var/www/gmwAvatar/backend/
ssh yoki-aliyun "sudo systemctl restart gmwavatar"
```

## 下一步
1. 初始化后端 FastAPI 工程与迁移体系。
2. 初始化前端 Vue 工程与运营页面。
3. 打通发布到数字人播报全链路。
4. 部署到阿里云服务器并完成联调。

## 今日完成（2026-02-11）
1. 列表页
- 增加每条新闻 `自动播报开关`（关闭后不进入播报队列）。
- 操作列仅保留 `编辑`、`删除`，去掉查看入口。
- 顶部 `播放` 按钮直接进入调试页。

2. 编辑页
- 字段改为：标题/内容必填，时间/发言人非必填。
- 仅保留 `保存` 按钮。
- 接入 Azure AI 生成口播稿与 2 条 Highlights。

3. 调试页与沉浸式页
- 调试页默认不加载数字人，新增手动加载/卸载按钮。
- 支持多语言勾选播报（中/英/粤/日/印尼/马来/印地）。
- 打开沉浸式页自动继承语言配置，按“同新闻多语言 -> 下一条新闻”循环。
- 沉浸式页 UI 固定 16:9，仅保留数字人与 Highlights，水印为 `TPCNEWS`。

4. 后端与数据
- 新增翻译接口：`POST /api/reports/translate-script`。
- 修复数据库持久化路径：固定到 `backend/gmwavatar.db`，避免数据“看起来丢失”。
- `.env` 固定读取 `backend/.env`，避免从不同目录启动时配置不生效。

5. 多语言播报链路（新增）
- 后端保存新闻后异步生成多语言翻译，并缓存非中英文语种的 PCM 音频。
- 播放队列按语言返回渲染模式：中文/英文走文字驱动，其它语种走音频流驱动。
- 调试页与沉浸式页统一读取预处理结果，避免实时翻译带来的延迟和语言回退。
- 若要启用非中英文真实播报，请在 `backend/.env` 配置 `AZURE_SPEECH_KEY`（或 `AZURE_TTS_DEPLOYMENT_NAME` 作为回退）。
- 已接入 Azure Speech 服务直连 TTS（`westus2`），优先用于粤语等语种发音。

## 前端播放页（已落地）
播放页代码位于 `frontend/`，已实现：
1. 使用百度曦灵 iframe 替换静态人物形象。
2. 从后端拉取最新已发布内容并展示口播稿。
3. 展示发布内容的 `Highlights` 列表。
4. 支持开始播报、静音切换、重载数字人。

本地运行：
```bash
cd frontend
npm install
npm run dev
```

## 一键启动（前后端）
```bash
cd /Users/yokichen/Documents/gmwAvatar
./scripts/dev-up.sh
```

停止服务：
```bash
cd /Users/yokichen/Documents/gmwAvatar
./scripts/dev-down.sh
```

历史新闻多语言翻译回填（建议执行一次）：
```bash
cd /Users/yokichen/Documents/gmwAvatar
./scripts/rebuild-translations.sh
```

## 冒烟测试（按钮点击）
执行说明见：`docs/smoke-test.md`

一键执行：
```bash
cd /Users/yokichen/Documents/gmwAvatar
node ./scripts/smoke-ui.mjs
```

测试报告输出：
- `docs/smoke-test-report.md`
- `docs/smoke-test-report.json`

## 今日完成（2026-02-12）
1. 编辑页
- 新增多语言预翻译勾选与语言切换。
- 勾选语言时自动准备翻译，支持人工校对后保存。

2. 调试页
- 新增三种顶层模式：实时总结、轮播会议总结、会议反思提问。
- 新增轮播范围切换：仅当前新闻 / 循环已开启新闻。
- 会议主题字号已下调。

3. 沉浸式页
- 按后端模式自动展示对应内容并驱动播报。
- 轮播模式继续支持多语言顺序循环。

4. 后端接口
- 新增翻译查询/准备/更新接口。
- 新增播放模式查询/更新接口。
- 新增实时总结占位接口与反思问答接口。

## 新增能力（2026-02-12）
1. 飞书会议链接导入
- 支持在列表页绑定会议链接（如 `https://vc.feishu.cn/j/151322082`）并调用后端导入。
- 后端自动执行：`meeting_no -> meeting_id -> 录制 -> 妙记 -> 文字记录`。
- 导入结果会返回“新增/更新/失败”统计。
- 支持先调用 `POST /api/reports/import/feishu-meeting/inspect` 仅查询会议全量信息（不入库）。
