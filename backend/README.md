# 后端服务（FastAPI）

## 运行步骤
1. 安装依赖
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp .env.example .env
```

关键变量：
- `AZURE_ENDPOINT_URL`
- `AZURE_OPENAI_API_KEY`
- `AZURE_DEPLOYMENT_NAME`
- `AZURE_TTS_DEPLOYMENT_NAME`（用于非中英文音频预合成，建议配置为可用的 TTS 部署）
- `AZURE_SPEECH_KEY`（已支持 Azure Speech 直连 TTS，优先于 OpenAI TTS）
- `AZURE_SPEECH_REGION`（示例：`westus2`）
- `AZURE_SPEECH_ENDPOINT`（示例：`https://westus2.api.cognitive.microsoft.com/`）
- `FEISHU_APP_ID`（飞书自建应用 app id）
- `FEISHU_APP_SECRET`（飞书自建应用 app secret）
- `FEISHU_API_BASE`（默认 `https://open.feishu.cn`）
- `FEISHU_TIMEOUT_SEC`（飞书接口超时秒数，默认 20）
- `FEISHU_VERIFY_SSL`（是否校验证书，默认 `true`）

3. 启动服务
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 关键接口（当前实现）
1. 新闻管理
- `GET /api/reports`
- `POST /api/reports`
- `GET /api/reports/{id}`
- `PUT /api/reports/{id}`
- `DELETE /api/reports/{id}`

2. AI 生成与翻译
- `POST /api/reports/generate-preview`
- `POST /api/reports/{id}/generate`
- `POST /api/reports/translate-script`

3. 播报相关
- `GET /api/reports/playback/queue`
- `GET /api/reports/published/latest`
- `POST /api/reports/{id}/publish`（保留兼容）
- `POST /api/avatar/token`

4. 导入
- `POST /api/reports/import/file`
- `POST /api/reports/import/source`（预留）
- `POST /api/reports/import/feishu-meeting/diagnose`（诊断权限链路，定位权限缺口）
- `POST /api/reports/import/feishu-meeting/inspect`（仅查询飞书会议全量信息，不入库）
- `POST /api/reports/import/feishu-meeting`（绑定飞书会议链接并导入）

## 飞书导入调试示例
1. 仅查询会议全量信息（不入库）
```bash
curl -X POST 'http://127.0.0.1:8000/api/reports/import/feishu-meeting/inspect' \
  -H 'Content-Type: application/json' \
  -d '{
    "meeting_url": "https://vc.feishu.cn/j/151322082",
    "lookback_days": 30
  }'
```

2. 诊断飞书权限链路（推荐先跑）
```bash
curl -X POST 'http://127.0.0.1:8000/api/reports/import/feishu-meeting/diagnose' \
  -H 'Content-Type: application/json' \
  -d '{
    "meeting_url": "https://vc.feishu.cn/j/151322082",
    "lookback_days": 30
  }'
```

3. 导入会议到新闻列表（入库）
```bash
curl -X POST 'http://127.0.0.1:8000/api/reports/import/feishu-meeting' \
  -H 'Content-Type: application/json' \
  -d '{
    "meeting_url": "https://vc.feishu.cn/j/151322082",
    "lookback_days": 30,
    "auto_generate": true,
    "auto_enable_playback": false
  }'
```

支持链接类型：
- 会议链接：`https://vc.feishu.cn/j/151322082`
- 妙记链接：`https://tpc.feishu.cn/minutes/obcnpo5u16v6e3zhb7y5x59y`

## 今日后端改动摘要（2026-02-11）
1. 新增多语言翻译接口
- 路由：`POST /api/reports/translate-script`
- 用途：沉浸式/调试页在非中文播报前先调用 AI 翻译。

2. 新增翻译持久化表
- 表：`meeting_report_translations`
- 字段：`report_id`、`language_key`、`title_text`、`script_text`、`highlights_json`、`audio_pcm_base64`
- 作用：保存预翻译内容，播放时直接读取，减少实时翻译延迟。
- 生成方式：保存成功后通过后台任务异步生成，避免阻塞保存接口。
- 非中英文语种会尝试预合成 PCM 音频缓存，供百度 `AUDIO_STREAM_RENDER` 使用。

3. 数据持久化修复
- `.env` 固定从 `backend/.env` 读取。
- SQLite 相对路径统一解析到 `backend/` 目录。
- 默认库文件固定为 `backend/gmwavatar.db`。

4. 列表联动字段
- `meeting_reports` 支持 `auto_play_enabled` 开关。
- 播报队列仅返回 `auto_play_enabled=true` 且 `script_final` 非空的新闻。
- 新建/导入新闻默认 `auto_play_enabled=false`，需手动开启后才进入播报队列。

5. 播放队列扩展
- `GET /api/reports/playback/queue` 支持参数：
  - `include_audio=true|false`
  - `langs=zh,en,yue,...`
  - `report_id=<id>`（按单条新闻返回，便于按需拉取音频）
- 返回 `localized` 结构中增加：
  - `render_mode`（text/audio）
  - `audio_ready`
  - `audio_pcm_base64`（按需返回）

6. 稳定性增强
- Azure 请求增加统一超时：`AZURE_REQUEST_TIMEOUT_SEC`（默认 45 秒）
- 防止翻译/语音任务长时间卡死，降低保存与后台任务阻塞风险
- 支持 `AZURE_SSL_SKIP_VERIFY`（默认 `false`，本地证书链异常时可临时设为 `true`）

7. Azure Speech TTS 路由
- 当前实现使用：`{AZURE_SPEECH_ENDPOINT}/tts/cognitiveservices/v1`
- 输出格式：`raw-16khz-16bit-mono-pcm`
- 语言声线映射已内置：中文、英文、粤语、日语、印尼语、马来语、印地语

## 新需求规划（2026-02-12，待开发）
1. 编辑页多语言预审接口
- `GET /api/reports/{id}/translations`
  - 返回每语言状态：`ready/preparing/failed/not_found`
  - 返回已准备语言的 `title/script/highlights`
- `POST /api/reports/{id}/translations/{lang}/prepare`
  - 按语言触发翻译准备任务

2. 调试页模式配置接口
- `GET /api/playback/mode`
- `PUT /api/playback/mode`
- 枚举：`realtime_summary`、`carousel_summary`、`reflection_qa`

3. 预留业务接口
- `GET /api/feishu/live-records`（实时总结模式数据源，先契约后实现）
- `POST /api/reports/{id}/reflection`（反思问答模式，先契约后实现）

## 新需求落地（2026-02-12）
1. 多语言预翻译接口已落地
- `GET /api/reports/{id}/translations`
- `POST /api/reports/{id}/translations/{lang}/prepare`
- `PUT /api/reports/{id}/translations/{lang}`

2. 调试模式接口已落地
- `GET /api/playback/mode`
- `PUT /api/playback/mode`

3. 业务模式接口已落地
- `GET /api/playback/live-records`（当前为占位数据源，后续接飞书）
- `POST /api/reports/{id}/reflection`（基于新闻内容生成反思问答）

4. 数据模型新增
- `playback_runtime_settings`：保存当前调试模式、轮播策略、反思目标新闻。
- `meeting_report_translations` 新增 `reviewed/reviewed_at` 字段。

## 说明
- 当前开发环境使用 SQLite 便于本地联调。
- 生产建议切换为 MySQL 8.x，并通过 `DATABASE_URL` 注入连接串。
