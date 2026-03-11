# Copublisher 架构改造计划（目标不变版）

> 目标保持不变：将 `copublisher` 打造成可被 `blue-ocean` 稳定调度的独立发布执行单元；`blue-ocean` 只负责审批、治理、编排、回写，不复制发布器实现。

## 0. 结论先行（架构视角）

当前项目处于“**功能可用、架构半成型**”阶段。  
它已经完成了第一轮安全基线与仓库独立化（副作用治理、输入校验、原子写、基础 job 输出），但尚未形成可长期扩张的“稳定内核 + 可插拔平台 + 清晰分层”。

最核心的架构问题不是某一个 bug，而是三个结构性短板：
- **入口层过重**：`__main__.py` 同时承担参数解析、流程编排、结果聚合、错误决策、I/O 落盘。
- **应用层缺位**：GUI/CLI 直接驱动平台实现，缺统一 UseCase/Orchestrator，导致逻辑重复与策略漂移。
- **平台实现耦合高**：`core/` 混合领域模型、平台适配器、浏览器细节，扩平台成本高，测试难隔离。

---

## 1. 目标架构（To-Be）

采用“接口适配 + 用例编排 + 领域内核 + 共享基础设施”四层结构：

1. `interfaces`（入口层）
   - CLI (`copublisher job run`)、GUI、未来 RPC/worker。
   - 只做协议转换，不含业务决策。

2. `application`（用例层）
   - `RunJobUseCase`、`RunBatchUseCase`、`RunEpisodeUseCase`。
   - 负责平台路由、重试策略、幂等判断、结果聚合、错误映射。

3. `domain`（领域层）
   - `JobSpec`、`PlatformResult`、`RunResult`、`ErrorCode`、状态机。
   - 纯业务模型与规则，不依赖 Playwright/requests。

4. `infrastructure`（实现层）
   - 平台发布实现（wechat/youtube/...）与持久化实现（state store、atomic IO）。
   - 对外通过 `PublisherPort` 暴露能力。

5. `shared`（共享层）
   - 安全校验、原子写、时间/哈希/序列化等通用能力。
   - 禁止反向依赖业务层。

依赖方向强制：`interfaces -> application -> domain`，`application -> infrastructure(通过 port)`，`shared` 不引用业务层。

---

## 2. 现状深度检查（Architecture Review）

## 2.1 架构合理性

优点（已具备）：
- 已治理模块级副作用（lazy import、YouTube 代理移动到调用点）。
- 已有基础安全与稳态能力（`sanitize_identifier`、`atomic_write_*`）。
- 发布器抽象 `Publisher` 与任务对象已形成初步统一接口。

问题（需改造）：
- `__main__.py` 体量过大，承担过多职责，违反单一职责与分层原则。
- `gui/app.py` 直接依赖多个具体发布器，实现了重复编排逻辑（与 CLI 分叉）。
- `core/base.py` 同时容纳大量平台任务模型，领域边界不清晰。
- 错误处理仍以字符串日志为主，缺统一错误语义对象。

## 2.2 扩张性（平台扩展、能力扩展）

当前扩张阻力：
- 新增平台需要改动多处（`core/base.py`、CLI、GUI、adapter、文档、测试）。
- 缺插件注册机制，平台扩展属于“侵入式改动”。
- 缺稳定契约版本机制，blue-ocean 集成后变更风险高。

目标扩张能力：
- 新平台通过注册即可接入，不需要改动主流程。
- 新入口（worker/API）复用同一 UseCase，不复制编排逻辑。
- 支持按组织/账号策略扩展（限流、并发、配额）而不改平台代码。

## 2.3 全局性（可治理、可运维、可演进）

当前全局短板：
- 缺统一执行模型（Job 生命周期、阶段状态、恢复点）。
- 缺可观测体系（结构化指标不完整，平台耗时/重试难统一分析）。
- 缺正式兼容策略（schema 版本、弃用窗口、契约测试）。

目标全局能力：
- 每次运行可追踪（trace_id/job_id/platform_id）。
- 失败可分类、可重试、可人工接管。
- 对上层调度系统提供稳定、版本化契约。

---

## 3. 架构改造原则（执行时必须遵守）

- 禁止模块级副作用（入口或调用点显式触发）。
- 业务编排只能存在于 `application`，CLI/GUI 仅做适配。
- 平台实现通过 `PublisherPort` 接入，禁止入口层直接 new 具体平台类。
- 外部输入统一在入口层校验并转换为领域对象。
- 状态落盘必须原子写，且 schema 版本化。
- 平台粒度提交，不做跨平台事务回滚，只做补偿重试。

---

## 4. 分阶段改造计划（2.5~3 周）

### M1（第 1 周末）：分层落地 + 契约硬化

#### Phase A1：分层骨架搭建
- 新建目录：
  - `src/copublisher/interfaces/`
  - `src/copublisher/application/`
  - `src/copublisher/domain/`
  - `src/copublisher/infrastructure/`
- 从 `__main__.py` 提取：
  - 参数解析与 I/O 留在 `interfaces/cli`
  - 业务流程迁移到 `application/usecases`
  - 结果对象迁移到 `domain/result.py`

#### Phase A2：Job 契约 v1
- 统一输出 schema：
  - `status`: `success|failed|partial`
  - `retryable`: bool
  - `manual_takeover_required`: bool
  - `artifacts`: `[{type, path, platform}]`
  - `error`: `{code, message, platform, details}`
  - `metrics`: `{schema_version, duration_ms, retries, platform_durations}`
- 保留兼容：
  - 继续支持 `--job-file`
  - 新增 `copublisher job run`

#### Phase A3：错误语义统一
- 在 `domain/error_codes.py` 固化错误码集合与 retryable 策略：
  - `MP_INPUT_INVALID`
  - `MP_AUTH_REQUIRED`
  - `MP_PLATFORM_TIMEOUT`
  - `MP_PLATFORM_CHANGED`
  - `MP_RATE_LIMIT`
  - `MP_PLATFORM_ERROR`
  - `MP_INTERNAL_ERROR`

M1 验收：
- CLI/GUI 均通过 UseCase 调用，不直接编排平台逻辑。
- 结果契约稳定且可供调度系统直接解析。

### M2（第 2 周末）：扩张能力 + 可靠性

#### Phase B1：平台插件化
- 定义 `PublisherPort` + `PublisherRegistry`：
  - `register(platform, factory, capabilities)`
  - `get(platform)` 返回统一接口
- 将 `wechat/youtube/...` 移入 `infrastructure/publishers/`
- 新平台接入只需要注册，不改主流程。

#### Phase B2：幂等与补偿
- `idempotency_key = hash(job_id + platform + content_hash)`
- 新增 `ExecutionStateStore`（本地 JSON 原子写实现）：
  - 记录成功平台、失败平台、重试计数、最后错误
- `partial` 重试仅执行失败平台。

#### Phase B3：可观测与治理
- 结构化日志字段：
  - `trace_id`, `job_id`, `platform`, `attempt`, `stage`, `duration_ms`
- 指标统一落地到 `metrics`，并可被 blue-ocean 直接消费。

M2 验收：
- 同一任务重复触发不会重复发布已成功平台。
- 平台新增改动范围可控（目标：<= 3 个文件）。

### M3（第 3 周中）：blue-ocean 闭环接入

#### Phase C1：blue-ocean 适配层
- 新增 `copublisher_adapter`（在 blue-ocean）：
  - 输入：`action_id/job_id/platforms/materials/account/idempotency_key`
  - 调用：`copublisher job run ... --json`
  - 输出：映射组织状态机（成功/重试/人工接管）

#### Phase C2：审批与回写闭环
- 统一回写到 `reports/org-runs/<id>/`
- 飞书卡片支持：
  - 平台级状态
  - 失败平台重试
  - 人工接管入口

#### Phase C3：联调策略
- 先跑通 wechat 单平台，再扩展 youtube，再扩展其余平台。
- 回归矩阵：`success/failed/partial/timeout/auth_expired/duplicate`

M3 验收：
- 审批通过 -> 执行 -> 回写全链路稳定。
- 重试不会重复发布已成功平台。

---

## 5. 文件级改造清单（copublisher）

### 5.1 新增文件（核心）
- `src/copublisher/domain/models.py`
- `src/copublisher/domain/result.py`
- `src/copublisher/domain/error_codes.py`
- `src/copublisher/application/usecases/run_job.py`
- `src/copublisher/application/services/result_builder.py`
- `src/copublisher/application/services/idempotency_service.py`
- `src/copublisher/infrastructure/registry.py`
- `src/copublisher/infrastructure/state_store/json_store.py`

### 5.2 改造文件（关键）
- `src/copublisher/__main__.py`
  - 缩减为 CLI 入口与参数映射，移除业务编排细节。
- `src/copublisher/gui/app.py`
  - 通过 UseCase 调用，不直接依赖多平台具体实现。
- `src/copublisher/core/*`（逐步迁移）
  - 保留兼容导出，实际实现迁到 `infrastructure/publishers/`。

### 5.3 保持兼容
- `copublisher.core.*` 老导入路径保留 1 个版本窗口（内部转发）。
- `--job-file` 参数模式继续可用，新增命令模式不破坏旧调用。

---

## 6. 测试与质量门禁

测试金字塔（改造后）：
- `unit`（领域/应用层）：schema、错误映射、幂等、聚合策略。
- `contract`（CLI 结果契约）：JSON schema 与兼容测试。
- `integration`（平台接口）：mock 外部 API + 最小实网冒烟。
- `e2e`（组织联调）：blue-ocean 适配器到回写闭环。

必须新增：
- `test_run_result_schema_v1.py`
- `test_idempotency_service.py`
- `test_registry_extension.py`
- `test_cli_contract_backward_compat.py`

CI 分层：
- 默认只跑 `unit + contract`。
- `integration/e2e` 走手动或 nightly pipeline。

---

## 7. 风险、权衡与反脆弱设计

- 风险：一次性大迁移造成回归
  - 策略：分层迁移 + 兼容导出 + 功能开关（新旧路径可切换）。
- 风险：平台 API/UI 高频变化
  - 策略：平台适配器隔离、失败截图归档、错误码归一。
- 风险：契约漂移影响 blue-ocean
  - 策略：schema version + contract test + 弃用窗口。
- 风险：任务长时运行中断
  - 策略：阶段状态落盘 + 幂等恢复 + 平台粒度补偿。

---

## 8. DoD（Definition of Done）

- 架构：
  - 入口、应用、领域、基础设施分层清晰，依赖方向可验证。
- 契约：
  - `job result schema v1` 冻结并有兼容策略。
- 可靠性：
  - 幂等与补偿机制可用，`partial` 场景可恢复。
- 扩展性：
  - 新平台接入不改主流程（通过注册）。
- 治理：
  - blue-ocean 能按结构化结果自动决策重试/人工接管。

---

## 9. 完成状态（2026-03-11 更新）

| 阶段 | 完成度 | 备注 |
|------|:---:|---|
| M1 分层骨架 | ✅ | domain/application/infrastructure/interfaces 已搭建 |
| M1 Job 契约 v1 | ✅ | RunResult、PlatformRunOutcome、schema 已实现 |
| M1 错误语义 | ✅ | domain/error_codes.py 已实现 |
| M2 平台插件化 | ✅ | PublisherRegistry、Legacy*Adapter 已实现 |
| M2 幂等与补偿 | ✅ | IdempotencyService、ExecutionStateStore 已实现 |
| M2 可观测 | ⚠️ | 结构化日志部分覆盖 |
| 统一发布路径 | ✅ | LegacyPlatformExecutor 已走 Registry |
| 根脚本融合 | ✅ | publish_gzh_drafts、verify_install 已并入 CLI |
| P0/P1 架构问题 | ✅ | WeChatPublisher 组合、GenericAdapter、GUI 线程安全、输入限制、socket/proxy |

详见 `docs/architecture-self-review.md`。

---

## 10. 自检、反思、迭代记录（深度）

### 第 1 轮自检：架构合理性
- 问题：上版计划偏“功能任务清单”，缺明确分层蓝图。
- 修正：补充 To-Be 架构与依赖方向，明确每层职责和边界。

### 第 2 轮自检：扩张性
- 问题：若继续在 `core` 横向堆平台，新增平台成本会持续线性上升。
- 修正：加入 `PublisherRegistry + Port` 插件化方案，降低接入侵入性。

### 第 3 轮自检：全局性
- 问题：仅有 `--json` 不等于可治理，缺生命周期模型与结构化指标。
- 修正：引入统一 `RunResult`、`ExecutionStateStore`、metrics 字段规范。

### 第 4 轮自检：迁移风险
- 问题：大改有兼容风险，尤其 CLI 与导入路径。
- 修正：定义“兼容窗口 + 旧参数保留 + 老导入转发”策略。

### 第 5 轮自检：目标一致性（plan 原记）

- 检查：
  - 是否保持独立仓库执行能力：是。
  - 是否避免 blue-ocean 复制发布实现：是。
  - 是否增强可调度、可审计、可重试：是。
- 结论：与原计划目标一致，且架构可持续性更强。

---

## 11. 建议执行顺序（最小返工）

1. 先做分层骨架与契约冻结（M1），避免继续在重入口上加功能。
2. 再做插件化与幂等补偿（M2），解决扩张与稳定性。
3. 最后做 blue-ocean 闭环接入（M3），以稳定契约联调。

该顺序在“目标不变”的前提下，兼顾了架构合理性、扩张性和全局治理能力，能以最低返工成本落地首个长期可演进版本。
