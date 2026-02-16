# gmwAvatar 代码优化任务清单

## 任务概览
基于代码 review，创建了以下代码级优化任务（运维级任务如数据库迁移暂不执行）。

## 🔥 高优先级任务 (P0 - 立即执行)

### 1. 后端错误处理与重试优化 (gmwAvatar-t0ox)
**目标**: 为 Azure AI/TTS/飞书 API 调用添加完善的错误处理、重试机制和错误分类；统一异常处理中间件；改进错误响应格式。

**改进点**:
- Azure OpenAI 调用已有重试，但需要更精细的错误分类（网络错误/配额错误/参数错误）
- 飞书 API 调用缺少完整的错误处理
- 统一异常响应格式

**验收标准**:
- 所有外部 API 调用都有重试机制
- 错误日志包含完整上下文
- 前端能收到明确的错误提示

---

### 2. 前端错误边界与状态管理 (gmwAvatar-c192)
**目标**: 完善前端所有页面的空态/加载态/错误态展示；添加全局错误边界；优化 API 调用失败提示；添加骨架屏。

**改进点**:
- ListPage/EditorPage/PlaybackPage 缺少加载态
- API 错误提示不够友好
- 缺少全局错误捕获

**验收标准**:
- 所有页面都有 Loading Skeleton
- API 调用失败有明确提示
- 空数据有友好的空态页面

---

### 3. 结构化日志体系建立 (gmwAvatar-u1uk)
**目标**: 引入结构化日志库（loguru）；为关键业务流程添加日志埋点；统一日志格式；添加请求追踪ID；日志分级输出。

**改进点**:
- 当前缺少系统化的日志记录
- 无法追踪请求链路
- 错误排查困难

**验收标准**:
- 所有 API 请求都有日志记录
- 关键业务节点有埋点
- 支持日志查询和过滤

---

### 4. 输入验证与安全加固 (gmwAvatar-n6ew)
**目标**: 完善 Pydantic Schema 验证；添加 SQL 注入防护检查；配置合理的 CORS 策略；敏感信息脱敏（日志/响应）；添加请求限流。

**改进点**:
- Schema 验证不完整
- CORS 配置过于宽松 (`*`)
- 日志可能包含敏感信息

**验收标准**:
- 所有输入都经过 Schema 验证
- CORS 配置为具体域名
- 日志中敏感字段已脱敏

---

## 📦 中优先级任务 (P1 - 近期执行)

### 5. reports.py模块拆分重构 (gmwAvatar-fg3i)
**目标**: 将 1636 行的 reports.py 按职责拆分为多个模块。

**拆分方案**:
```
backend/app/api/
├── reports_crud.py       # CRUD 操作
├── reports_import.py     # 导入逻辑（文件/飞书）
├── reports_translation.py # 翻译管理
└── reports_queue.py      # 播放队列
```

---

### 6. Azure服务抽象层 (gmwAvatar-tww0)
**目标**: 为 Azure OpenAI/TTS/Speech 服务创建抽象层；支持 Prompt 版本化管理；统一配置验证；支持降级与回退策略。

**改进方案**:
```
backend/app/services/
├── azure_service.py      # 服务抽象层
├── prompts/
│   ├── generate_script_v1.txt
│   └── translate_v1.txt
```

---

### 7. 前端TypeScript类型完善 (gmwAvatar-f9zr)
**目标**: 完善所有 API 响应类型定义；启用严格的 TypeScript 检查；消除 any 类型；统一错误类型；添加类型守卫。

---

### 8. 核心业务单元测试 (gmwAvatar-8rm0)
**目标**: 为核心服务添加 pytest 单元测试；添加测试数据 fixtures；配置测试覆盖率报告。

**测试范围**:
- `generator.py` - AI 生成逻辑
- `feishu_import.py` - 飞书导入
- 关键 API 端点

---

### 9. 配置管理优化 (gmwAvatar-icw1)
**目标**: 添加配置验证中间件；环境变量文档化；添加配置健康检查接口。

---

## 🔧 低优先级任务 (P2 - 长期优化)

### 10. API文档自动生成优化 (gmwAvatar-zt45)
**目标**: 完善 FastAPI OpenAPI 文档；添加详细 docstring、请求/响应示例；配置 Swagger UI 主题。

---

## 任务执行顺序建议

### Week 1: 稳定性基础
1. 后端错误处理与重试优化 (gmwAvatar-t0ox)
2. 结构化日志体系建立 (gmwAvatar-u1uk)
3. 输入验证与安全加固 (gmwAvatar-n6ew)

### Week 2: 用户体验
4. 前端错误边界与状态管理 (gmwAvatar-c192)
5. 前端TypeScript类型完善 (gmwAvatar-f9zr)

### Week 3-4: 代码质量
6. reports.py模块拆分重构 (gmwAvatar-fg3i)
7. Azure服务抽象层 (gmwAvatar-tww0)
8. 核心业务单元测试 (gmwAvatar-8rm0)

### Week 5: 运维支持
9. 配置管理优化 (gmwAvatar-icw1)
10. API文档自动生成优化 (gmwAvatar-zt45)

---

## 当前任务状态

查看所有任务：
```bash
beans list
```

查看高优先级任务：
```bash
beans list --priority high
```

开始某个任务：
```bash
beans start gmwAvatar-t0ox
```
