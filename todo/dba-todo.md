# DBA Todo（系统架构版）

## 目标
为会议总结播报系统提供稳定、可追溯、可恢复的 MySQL 数据基础设施。

## 迭代 1（MVP）
1. 数据建模
- [ ] 建立 `meeting_reports` 主表
- [ ] 建立 `meeting_report_highlights` 子表
- [ ] 建立 `avatar_configs` 配置表
- [ ] 删除策略采用硬删除（不建回收站表）

2. 索引与约束
- [ ] `meeting_reports(status, updated_at)`
- [ ] `meeting_reports(status, published_at)`
- [ ] `meeting_reports(meeting_time)`
- [ ] `meeting_report_highlights(report_id, kind, seq)`
- [ ] 约束：final 亮点最多 2 条（服务层+数据库策略）

3. 时间与编码规范
- [ ] 全库统一中国时区 `Asia/Shanghai`
- [ ] 字符集统一 `utf8mb4`

4. 迁移规范
- [ ] Alembic 首版迁移脚本
- [ ] 回滚脚本验证
- [ ] 预发布环境演练迁移

5. 备份与恢复
- [ ] 每日全量备份
- [ ] binlog 增量备份
- [ ] 每月恢复演练

## 迭代 2（增强）
1. 审计与历史
- [ ] 增加审核日志表（字段变更快照）
- [ ] 增加发布版本表（可追溯每次发布内容）

2. 性能治理
- [ ] 慢查询分析与索引微调
- [ ] 高频查询缓存策略评估
- [ ] 大文本字段冷热分离评估

3. 生命周期治理
- [ ] 草稿与已发布数据保留策略落地
- [ ] 删除数据不保留（维持硬删除策略）
- [ ] 数据脱敏策略

## 架构评审补充（已对齐你的决策）
1. [ ] 不实现删除数据保留与回收站恢复
2. [ ] 保留 draft 与 published 数据
3. [ ] 发布模型支持多条新闻同时 published

## 今日进展（2026-02-11）
1. 已完成
- [x] 当前版本新闻数据已落库持久化
- [x] 删除策略为硬删除（不保留回收站）
- [x] 开发环境数据库路径固定至 `backend/gmwavatar.db`
- [x] 支持 `auto_play_enabled` 字段作为播报队列过滤依据

2. 待优化
- [ ] 从 SQLite 平滑迁移到 MySQL 8.x 的正式迁移脚本
- [ ] MySQL 索引与慢 SQL 基线压测
- [ ] 备份恢复演练文档与自动化脚本

3. 新增进展（2026-02-11 晚）
- [x] 翻译表增加 `audio_pcm_base64` 字段，支持多语言音频缓存
- [ ] MySQL 正式库需将该字段类型固化为 `LONGTEXT`

4. 新阶段任务（2026-02-13，统一生成与会后拉齐）
- [ ] 翻译表补充 `reflections_json` 字段（多语言反思缓存）
- [ ] 生成状态字段规划：`content_status` / `translation_status`（可选）
- [ ] 新建外部来源链接表（建议）：`external_meeting_links`
- [ ] 新建拉齐任务日志表（建议）：`sync_runs` / `sync_run_items`
- [ ] 索引补充：
  - `meeting_reports(source_minute_token)`
  - `meeting_reports(source_meeting_id)`
  - `meeting_reports(source_url(255))`（MySQL 前缀索引）
  - `meeting_report_translations(report_id, language_key)`
