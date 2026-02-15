---
name: backend-python-service
description: 面向多国会议数字人播报系统的 Python 后端技能。用于实现后端 API、内容导入、口播稿与亮点生成、审核发布状态流转，以及百度数字人 token 下发。
---

# 后端技能文档

## 目标
构建稳定可扩展的 Python 后端服务，支撑会议总结到数字人播报全流程。

## 技术栈
- Python 3.11+
- FastAPI（推荐）
- SQLAlchemy + Alembic
- MySQL 8.x
- Redis（可选，用于缓存/任务队列）

## 核心职责
1. 提供会议总结 CRUD 接口。
2. 支持单条/批量导入会议总结。
3. 根据原文生成口播稿草案。
4. 提取 1-2 条亮点草案。
5. 提供审核、发布状态流转。
6. 由后端签发百度数字人 token（前端不暴露密钥）。

## 最小数据契约
- title
- meeting_time
- speaker
- summary_raw
- script_draft
- script_final
- highlights_draft（数组）
- highlights_final（数组）
- status: draft | reviewed | published
- published_at

## API 边界
1. `POST /api/reports/import/file`
2. `POST /api/reports/import/source`（预留）
3. `POST /api/reports`
4. `GET /api/reports`
5. `GET /api/reports/{id}`
6. `PUT /api/reports/{id}`
7. `DELETE /api/reports/{id}`
8. `POST /api/reports/{id}/generate`
9. `POST /api/reports/{id}/publish`
10. `GET /api/reports/published/latest`
11. `POST /api/avatar/token`
12. `POST /api/reports/translate-script`
13. `GET /api/reports/playback/queue`
  - 支持可选查询：`include_audio`、`langs`

## 列表页接口约定（对应 News List）
1. `GET /api/reports`
- 请求参数：`page`、`page_size`、`status`（可选）
- 返回结构：
  - `items[]`: `id/title/speaker/meeting_time/status`
  - `total/page/page_size`
- 默认排序：`meeting_time desc` 或 `updated_at desc`

2. `DELETE /api/reports/{id}`
- 采用硬删除（物理删除）
- 删除后数据不保留，不提供回收站恢复

## 编辑页接口约定（对应 News Editor）
1. `POST /api/reports`
- 用于 `/editor` 新建
- 最小入参：`title/meeting_time/speaker/summary_raw`
- 初始状态：`draft`

2. `GET /api/reports/{id}`
- 用于 `/editor/:id` 回填表单
- 返回：输入区字段 + 输出区字段（草案与终稿）

3. `PUT /api/reports/{id}`
- 用于保存编辑结果（Save）
- 可更新：`title/meeting_time/speaker/summary_raw/script_final/highlights_final`
- 当前前端只保留“保存”动作，不区分“存草稿/发布”按钮

4. `POST /api/reports/{id}/generate`
- 根据 `summary_raw` 生成：
  - `script_draft`
  - `highlights_draft`（1-2 条）
- 可重复触发，默认只覆盖草案字段

5. `POST /api/reports/{id}/publish`
- 发布前强校验：
  - `title/meeting_time/speaker` 非空
  - `script_final` 非空
  - `highlights_final` 数量为 1-2
- 成功后：`status=published`，写入 `published_at`

## 业务规则
- 仅当 `script_final` 与 `highlights_final` 完整时允许发布。
- 最终亮点数量必须为 1 或 2。
- 草案与最终稿都要保留，便于审计追踪。
- 导入接口按外部来源 ID 做幂等（若有来源 ID）。
- `Generate` 与 `Save Draft` 解耦：生成不等于发布，保存不等于发布。
- 支持“新建页”和“编辑页”同构字段，避免前端分两套数据结构。
- 允许多条新闻同时处于 `published` 状态。
- 列表页支持 `auto_play_enabled` 开关字段，关闭后不进入自动播报队列。
- 系统时间统一使用中国时区 `Asia/Shanghai`。
- 生成失败只返回错误，不做模板降级策略。
- 多语言播报时，采用“预翻译 + 预音频”：
  - 保存时异步生成各语种翻译并入库
  - 中文/英文走文字驱动
  - 其它语种预合成 PCM 音频，播报时走音频流驱动

## 质量要求
- 为生成流程和发布校验编写单元测试。
- 为 CRUD 与发布流程编写集成测试。
- 生命周期与 token 下发过程输出结构化日志。
- 参数校验失败时返回明确错误码。

## 安全要求
- 百度凭据仅保存在后端环境变量。
- token 短期有效并支持服务端缓存刷新。
- 当前单人后台暂不实现权限系统。

## 部署要点（阿里云轻量服务器）
- 生产环境建议 `gunicorn + uvicorn`。
- 后端放在 Nginx 反向代理后。
- 提供 `/healthz` 健康检查接口。
- 严禁把密钥提交到仓库。

## 今日实现对齐（2026-02-11）
1. 已接入 Azure AI：
- 口播稿与亮点生成：`generate-preview`/`{id}/generate`
- 多语言翻译：`translate-script`

2. 已完成数据库持久化稳定性修复：
- SQLite 默认路径固定到 `backend/gmwavatar.db`
- 统一 `.env` 读取路径，避免不同启动目录导致“数据丢失错觉”

3. 新增多语言音频缓存（2026-02-11 晚）
- `meeting_report_translations` 新增 `audio_pcm_base64`
- 播放队列按语言返回 `render_mode`、`audio_ready`、`audio_pcm_base64`
- 调试页/沉浸式页不再做实时翻译，直接读取预处理结果
