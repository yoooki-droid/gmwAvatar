---
# gmwAvatar-fg3i
title: reports.py模块拆分重构
status: scrapped
type: task
priority: normal
created_at: 2026-02-15T08:18:40Z
updated_at: 2026-02-15T08:25:50Z
---

将 1636 行的 reports.py 按职责拆分：api/reports_crud.py、api/reports_import.py、api/reports_translation.py、api/reports_queue.py；提取共用工具到 utils/。
