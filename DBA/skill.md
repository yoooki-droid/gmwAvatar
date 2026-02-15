---
name: dba-mysql-governance
description: 面向多国会议数字人播报系统的 MySQL DBA 技能。用于数据库建模、索引设计、迁移规范、备份恢复和性能优化。
---

# 数据库技能文档

## 目标
设计并维护稳定的 MySQL 数据层，支撑导入、审核、发布、播报查询。

## 技术基线
- MySQL 8.x
- 字符集：utf8mb4
- 存储引擎：InnoDB
- 开发联调可使用 SQLite（本项目当前默认）

## 核心数据表
1. `meeting_reports`
- `id` bigint pk
- `title` varchar(255)
- `meeting_time` datetime
- `speaker` varchar(120)
- `summary_raw` longtext
- `script_draft` longtext
- `script_final` longtext
- `status` enum('draft','reviewed','published')
- `published_at` datetime null
- `created_at` datetime
- `updated_at` datetime

2. `meeting_report_highlights`
- `id` bigint pk
- `report_id` bigint fk -> meeting_reports.id
- `kind` enum('draft','final')
- `highlight_text` varchar(500)
- `seq` tinyint

3. `avatar_configs`
- `id` bigint pk
- `figure_id` varchar(64)
- `camera_id` varchar(64)
- `resolution_width` int
- `resolution_height` int
- `tts_per` varchar(64) null
- `tts_lan` varchar(32) null
- `is_active` tinyint(1)

4. `meeting_report_translations`
- `id` bigint pk
- `report_id` bigint fk -> meeting_reports.id
- `language_key` varchar(16)
- `title_text` longtext
- `script_text` longtext
- `highlights_json` longtext
- `audio_pcm_base64` longtext
- `updated_at` datetime

## 索引策略
- `meeting_reports(status, updated_at)`：后台列表查询。
- `meeting_reports(status, published_at)`：已发布内容检索。
- `meeting_reports(meeting_time)`：按会议时间筛选。
- `meeting_report_highlights(report_id, kind, seq)`：亮点有序读取。

## 数据规则
- `kind='final'` 的亮点数量必须是 1-2 条（服务层强校验）。
- 草案与终稿必须分离存储，保证可追溯。
- 发布前执行完整业务校验。

## 迁移规范
- 统一使用 Alembic，不手工改生产结构。
- 每个迁移脚本必须提供回滚路径。
- 大表加索引需安排在业务低峰期。

## 备份与恢复
- 每日全量备份 + binlog 增量备份。
- 建议保留 7-14 天备份。
- 每月至少一次预发布环境恢复演练。

## 性能与运维
- 每周查看慢查询日志并优化 Top SQL。
- 连接池参数与轻量服务器 CPU/RAM 匹配。
- 历史草稿数据量过大时执行归档策略。

## 安全规则
- 数据库账号遵循最小权限原则。
- 应用账号与运维账号分离。
- 远程访问尽量启用 TLS。

## 今日实现对齐（2026-02-11）
1. 当前开发库
- 默认数据库为 `backend/gmwavatar.db`（SQLite）。
- 目标生产数据库仍为 MySQL 8.x。

2. 持久化稳定性
- 相对数据库路径统一固定到 `backend` 目录，避免因启动目录不同连接到不同库。
- 该策略已用于修复“测试数据重启后看似丢失”的问题。

3. 多语言音频缓存
- 非中英文语种的预合成 PCM 音频以 `audio_pcm_base64` 落库。
- MySQL 建议字段类型使用 `LONGTEXT`，避免 64KB 上限截断。
