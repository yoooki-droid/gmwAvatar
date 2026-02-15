# 后端 Todo（系统架构版）

## 目标
构建可上线的 Python 后端，支撑“创建/生成/审核/发布/播报”全链路。

## 迭代 1（MVP）
1. 工程骨架与环境配置
- [ ] 初始化 FastAPI + SQLAlchemy + Alembic
- [ ] 配置多环境（dev/staging/prod）
- [ ] 增加 `/healthz` 与 `/readyz`

2. 核心数据与接口
- [ ] 完成 `meeting_reports`、`meeting_report_highlights`、`avatar_configs` 迁移
- [ ] 实现 `GET /api/reports`（分页、状态筛选、排序）
- [ ] 实现 `POST /api/reports`、`GET /api/reports/{id}`、`PUT /api/reports/{id}`
- [ ] 实现 `DELETE /api/reports/{id}`（硬删除）

3. 内容生成与发布
- [ ] 实现 `POST /api/reports/{id}/generate`
- [ ] 生成逻辑输出 `script_draft` + `highlights_draft(1-2)`
- [ ] 实现 `POST /api/reports/{id}/publish` 强校验
- [ ] 实现 `GET /api/reports/published/latest`

4. 百度曦灵接入后端能力
- [ ] 实现 `POST /api/avatar/token`
- [ ] token 短期缓存与过期刷新
- [ ] 记录 token 下发日志（敏感字段脱敏）

5. 导入能力
- [ ] 实现文件导入接口 `POST /api/reports/import/file`（CSV/Excel）
- [ ] 预留 API 导入接口 `POST /api/reports/import/source`
- [ ] 实现导入结果返回：成功/失败数量与错误明细

6. 测试与质量
- [ ] 单元测试：发布校验、亮点数量校验、删除逻辑
- [ ] 集成测试：列表/编辑/生成/发布链路
- [ ] 统一错误码与错误响应结构

## 迭代 2（增强）
1. 生成能力增强
- [ ] 接入 Azure LLM（`docs/aurze.llm`）并抽象模型服务层
- [ ] Prompt 版本化（口播稿与亮点分开模板）
- [ ] 生成重试与超时控制

2. API 导入落地
- [ ] 连接第三方来源并完成字段映射
- [ ] 导入幂等去重（source_id + hash）
- [ ] 导入任务状态查询接口（可异步化）

3. 审计与可观测性
- [ ] 审核/发布操作日志
- [ ] 结构化日志（trace_id/request_id）
- [ ] 指标上报与告警（5xx、生成失败率、token 失败率）

## 架构评审补充（已对齐你的决策）
1. [ ] 发布模型：允许多条新闻并行 `published`
2. [ ] 时区：统一 `Asia/Shanghai`
3. [ ] 权限：当前不实现权限系统
4. [ ] 降级：不做降级方案，仅 AI 生成

## 今日进展（2026-02-11）
1. 已完成
- [x] 新闻 CRUD 与列表接口可用
- [x] 列表字段新增 `auto_play_enabled`
- [x] 自动播报队列接口可按开关过滤
- [x] 生成接口可调用 Azure AI 生成口播稿与亮点
- [x] 新增翻译接口 `POST /api/reports/translate-script`
- [x] 百度数字人 token 下发接口可用
- [x] 修复数据库路径不一致导致的数据错连问题

2. 待优化
- [ ] 生成与翻译接口增加重试与限流
- [ ] 导入接口完善 Excel 模板校验与错误明细
- [ ] 增加自动化测试覆盖（生成/翻译/播报队列）

3. 新增进展（2026-02-11 晚）
- [x] 播报队列支持 `include_audio` 与 `langs` 参数
- [x] 播报队列支持 `report_id` 定向返回（按需拉音频）
- [x] `meeting_report_translations` 增加 `audio_pcm_base64` 音频缓存字段
- [x] 保存新闻后异步执行“多语言翻译 + 非中英文音频预合成”
- [x] Azure 请求统一超时控制，避免后台任务卡死
- [x] Azure Speech TTS 接入完成（westus2 资源，支持 key1/key2 轮换）

4. 新需求待办（2026-02-12）
- [ ] 新增 `GET /api/reports/{id}/translations`（返回多语言准备状态与内容）
- [ ] 新增 `POST /api/reports/{id}/translations/{lang}/prepare`（按语言触发预翻译）
- [ ] 新增调试模式配置接口（实时总结/轮播会议总结/会议反思提问）
- [ ] 预留飞书实时记录接口契约（实时总结模式）
- [ ] 预留会议反思问答接口契约（反思提问模式）

5. 新需求完成（2026-02-12）
- [x] `GET /api/reports/{id}/translations`
- [x] `POST /api/reports/{id}/translations/{lang}/prepare`
- [x] `PUT /api/reports/{id}/translations/{lang}`
- [x] `GET /api/playback/mode`、`PUT /api/playback/mode`
- [x] `GET /api/playback/live-records`（占位数据源）
- [x] `POST /api/reports/{id}/reflection`

6. 新增待办（飞书会议链接导入）
- [x] 新增 `POST /api/reports/import/feishu-meeting`
- [x] 新增 `POST /api/reports/import/feishu-meeting/diagnose`（分步骤权限诊断）
- [x] 新增 `POST /api/reports/import/feishu-meeting/inspect`（仅查询会议信息，不入库）
- [x] 兼容“会议进行中”场景：无录制时返回 `pending` 并可先绑定导入
- [x] 新增飞书导入服务层（token、list_by_no、recording、minutes、transcript）
- [x] `meeting_reports` 增加来源字段（source_type/source_meeting_no/source_meeting_id/source_minute_token/source_url）
- [x] 导入幂等：同 minute_token 重复导入走更新
- [x] 增加导入结果结构化返回（imported/updated/failed + items）
- [x] 更新 `backend/.env.example` 与 `backend/README.md` 的飞书配置说明

7. 新增进展（2026-02-12 晚，实时正式内容优先）
- [x] 飞书 minute 详情新增“正式章节总结/实时草稿”双轨抽取（正式优先）
- [x] 导入摘要拼装策略调整：先写入“会议章节总结（正式）”，再回退文字转写
- [x] `GET /api/playback/live-records` 回退解析优化：优先提取 `【会议章节总结（正式）】` 分段
- [x] 新增“逐字稿 -> Azure AI -> 章节纪要”兜底生成，写入 `【AI章节纪要】` 分段

8. 新阶段任务（2026-02-13，统一生成链路）
- [ ] 新增统一生成入口 `POST /api/reports/{id}/generate-pack`
- [ ] 统一产出：`script_final` + `highlights_final` + `reflections_final`
- [ ] 多语言预生成扩展为包含 `reflections`（与 summary/highlights 同步）
- [ ] 生成完成后统一触发翻译刷新任务，保证反思模式可直接读取缓存
- [ ] 失败状态标准化：`missing/generating/ready/failed`

9. 新阶段任务（2026-02-13，会后自动拉齐）
- [ ] 新增多维表拉取服务（每 5 分钟）：读取会议链接清单
- [ ] 新增飞书链接拉齐任务（每 5 分钟）：`diagnose -> inspect -> import`
- [ ] `pending/not_ready` 重试队列与退避策略
- [ ] 拉齐成功后自动触发 `generate-pack`
- [ ] 幂等保障：`minute_token` > `meeting_id` > `source_url`
