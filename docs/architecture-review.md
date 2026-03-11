# Copublisher 架构深度体检报告

> 版本：v3.0.0 | 审查日期：2026-03-10 | 审查范围：全量源码 + 测试 + 文档

---

## 目录

1. [项目概览](#1-项目概览)
2. [架构全景](#2-架构全景)
3. [分层依赖分析](#3-分层依赖分析)
4. [架构优势](#4-架构优势)
5. [架构问题与风险](#5-架构问题与风险)
6. [代码质量审查](#6-代码质量审查)
7. [安全性审查](#7-安全性审查)
8. [测试体系评估](#8-测试体系评估)
9. [扩展性评估](#9-扩展性评估)
10. [改进路线图](#10-改进路线图)

---

## 1. 项目概览

Copublisher 是一个多平台内容一键发布工具，支持 7 个平台：

| 类型 | 平台 | 发布方式 |
|------|------|---------|
| 视频 | 微信视频号 | Playwright 浏览器自动化 |
| 视频 | YouTube Shorts | YouTube Data API v3 |
| 视频 | TikTok | Content Posting API |
| 视频 | Instagram Reels | Facebook Graph API |
| 文章 | Medium | REST API |
| 文章 | Twitter/X | X API v2 |
| 文章 | Dev.to | REST API |

**入口方式**：CLI（直接发布 / 批量发布 / Job 子命令）、Gradio GUI、Python SDK。

**技术栈**：Python 3.10+、Playwright、Gradio、Google API Client、requests、hatchling 构建。

---

## 2. 架构全景

### 2.1 目录结构

```
src/copublisher/
├── __init__.py              # 包入口（lazy export）
├── __main__.py              # CLI 入口 + 参数解析
├── domain/                  # 领域模型
│   ├── models.py            # JobSpec
│   ├── result.py            # RunResult / PlatformRunOutcome
│   └── error_codes.py       # ErrorCode 枚举 + 重试策略
├── application/             # 应用层
│   ├── usecases/
│   │   ├── publish_content.py  # PublishContentUseCase
│   │   └── run_job.py          # RunJobUseCase
│   └── services/
│       ├── idempotency_service.py
│       ├── result_builder.py
│       ├── org_run_reporter.py
│       └── blue_ocean_adapter.py
├── infrastructure/          # 基础设施层
│   ├── registry.py          # PublisherRegistry + build_default_registry
│   ├── publishers/
│   │   ├── executor.py      # LegacyPlatformExecutor
│   │   └── legacy.py        # 7 个 Legacy*PublisherAdapter
│   └── state_store/
│       └── json_store.py    # ExecutionStateStore
├── core/                    # 核心发布模块
│   ├── base.py              # Platform 枚举 + 8 个 PublishTask + Publisher ABC
│   ├── adapter.py           # EpisodeAdapter
│   ├── browser.py           # PlaywrightBrowser
│   ├── wechat.py            # WeChatPublisher
│   ├── youtube.py           # YouTubePublisher
│   ├── medium.py            # MediumPublisher
│   ├── twitter.py           # TwitterPublisher
│   ├── devto.py             # DevToPublisher
│   ├── tiktok.py            # TikTokPublisher
│   ├── instagram.py         # InstagramPublisher
│   ├── gzh.py               # 公众号认证逻辑
│   └── gzh_video.py         # GzhVideoUploader
├── interfaces/cli/          # CLI 接口层
│   ├── job_command.py       # job 子命令实现
│   ├── job_runner.py        # job UseCase 组装
│   └── workflows.py         # 批量/Episode/传统 CLI 流程
├── gui/                     # GUI 层
│   └── app.py               # Gradio Web 界面
└── shared/                  # 共享工具
    ├── io.py                # atomic_write_text / atomic_write_json
    └── security.py          # sanitize_identifier
```

### 2.2 数据流概要

```
                    ┌──────────────────────────────────────────┐
                    │          入口层 (__main__.py)              │
                    │  CLI args → 路由到 GUI/Batch/Episode/Job  │
                    └───────┬─────────┬───────────┬────────────┘
                            │         │           │
              ┌─────────────▼──┐  ┌───▼────┐  ┌──▼───────────┐
              │ workflows.py   │  │ GUI    │  │ job_command  │
              │ (batch/legacy  │  │ app.py │  │ job_runner   │
              │  /episode CLI) │  └───┬────┘  └──┬───────────┘
              └───────┬────────┘      │          │
                      │               │          │
              ┌───────▼───────────────▼──┐  ┌───▼──────────┐
              │ PublishContentUseCase     │  │ RunJobUseCase│
              │ (application/usecases)   │  │ + Registry   │
              └───────┬──────────────────┘  └──┬───────────┘
                      │                        │
              ┌───────▼────────┐  ┌────────────▼───────────┐
              │ LegacyPlatform │  │ Legacy*PublisherAdapter │
              │   Executor     │  │ (PublisherPort impls)   │
              └───────┬────────┘  └────────────┬───────────┘
                      │                        │
              ┌───────▼────────────────────────▼───────────┐
              │           core/ 发布器实现层                 │
              │  WeChatPublisher / YouTubePublisher / ...   │
              └────────────────────────────────────────────┘
```

---

## 3. 分层依赖分析

### 3.1 依赖矩阵

|  引用方 ↓  / 被引用方 → | shared | domain | core | infrastructure | application | interfaces | gui | \_\_main\_\_ |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **shared**        | —  | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **domain**        | ✓  | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **core**          | ✓  | ✗ | — | ✗ | ✗ | ✗ | ✗ | ✗ |
| **infrastructure**| ✓  | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ |
| **application**   | ✗  | ✓ | ✗ | ✓ | — | ✗ | ✗ | ✗ |
| **interfaces**    | ✓  | ✗ | ✗ | ✓ | ✓ | — | ✗ | ✗ |
| **gui**           | ✗  | ✗ | ✗ | ✗ | ✓ | ✗ | — | ✗ |
| **\_\_main\_\_**  | ✓  | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | — |

### 3.2 合规性判定

| 规则 | 状态 | 说明 |
|------|------|------|
| shared 不引用业务层 | ✅ 合规 | `shared/` 仅依赖标准库 |
| domain 不引用 infrastructure | ✅ 合规 | `domain/` 仅依赖 `shared` |
| core 不引用 application | ✅ 合规 | `core/` 仅依赖 `shared` |
| application 不引用 interfaces | ✅ 合规 | 通过 Protocol 解耦 |
| gui 不直接 import core | ✅ 合规 | gui 通过 application UseCase 间接访问 |
| `__init__.py` 无 eager import | ✅ 合规 | `shared/__init__.py` 已改为 `__getattr__` 延迟加载 |
| 无模块级副作用 | ✅ 合规 | `load_dotenv()` 和代理设置均在调用点执行 |

### 3.3 依赖异常

**问题 ①：`core/` 层身份不清**

`core/base.py` 同时包含：
- 领域概念：`Platform` 枚举、`PublishTask` / `ArticlePublishTask` 抽象类、7 个具体 Task 类
- 基础设施接口：`Publisher` ABC（含 `log_callback`、日志实现）

这导致 `domain/models.py` 中的 `JobSpec` 和 `core/base.py` 中的 `PublishTask` 之间存在概念割裂——两者都是"任务定义"，却分属不同层。

**问题 ②：双重发布调度路径** ✅ 已统一

入口仍分两类（GUI/workflows vs job），但**底层均通过 Registry 分发**：
- `PublishContentUseCase` → `LegacyPlatformExecutor._publish_via_registry` → Registry
- `RunJobUseCase` → Registry 直接

输出格式统一为 `(success, message)` / `PlatformRunOutcome`。

---

## 4. 架构优势

### 4.1 延迟导入（Lazy Import）

`__init__.py` 和 `core/__init__.py` 采用 `__getattr__` 延迟加载，避免导入时触发 Playwright 安装检查、Google API 初始化等重量级依赖。

```python
def __getattr__(name):
    if name in _EXPORTS:
        module_name, symbol_name = _EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, symbol_name)
        globals()[name] = value
        return value
```

**评价**：✅ 优秀。遵守"禁止模块级副作用"规则，`import copublisher` 的代价接近零。

### 4.2 原子写入

所有状态文件（认证 JSON、执行状态、报告）统一通过 `atomic_write_text` / `atomic_write_json` 写入：

```python
fd, tmp_name = tempfile.mkstemp(...)
# 写入临时文件 → fsync → os.replace 原子替换
```

**评价**：✅ 优秀。严格遵守"先写临时文件再 rename"规则，防止崩溃产生空文件。

### 4.3 路径安全校验

`sanitize_identifier()` 在所有路径拼接前校验外部输入：

```python
if ".." in normalized or "/" in normalized or "\\" in normalized:
    raise ValueError(f"{field_name} contains forbidden path characters")
```

覆盖点：`job_id`、`account`、`user_name`、`org_run_id`。

**评价**：✅ 良好。覆盖了主要路径注入风险。

### 4.4 领域错误码体系

```python
class ErrorCode(str, Enum):
    MP_INPUT_INVALID = "MP_INPUT_INVALID"
    MP_AUTH_REQUIRED = "MP_AUTH_REQUIRED"
    MP_PLATFORM_TIMEOUT = "MP_PLATFORM_TIMEOUT"
    ...

_POLICIES: dict[ErrorCode, ErrorPolicy] = {
    ErrorCode.MP_INPUT_INVALID: ErrorPolicy(retryable=False, manual_takeover=False),
    ErrorCode.MP_AUTH_REQUIRED: ErrorPolicy(retryable=False, manual_takeover=True),
    ...
}
```

**评价**：✅ 优秀。错误码与重试/人工接管策略解耦，调度层只需查表。

### 4.5 幂等性机制

`IdempotencyService` 基于内容哈希（video SHA-256 + script JSON）生成幂等键，结合 `ExecutionStateStore` 持久化状态，实现：
- 已成功的平台自动跳过
- 失败平台可安全重试
- 重试计数持久化

**评价**：✅ 优秀。为调度系统集成（Blue Ocean）提供了可靠的幂等保障。

### 4.6 Protocol 解耦

```python
class PublisherPort(Protocol):
    def publish(self, *, video_path, script_data, privacy, account) -> PlatformRunOutcome: ...

class PublishExecutorPort(Protocol):
    def run_legacy_script(self, ...) -> dict[str, tuple[bool, str]]: ...
```

**评价**：✅ 良好。Application 层不直接依赖 Infrastructure 实现，支持测试替换。

---

## 5. 架构问题与风险

### 5.1 严重问题（P0）

#### P0-1：WeChatPublisher 与 PlaywrightBrowser 的职责重复 ✅ 已修复

`WeChatPublisher` 已改为组合 `PlaywrightBrowser`，与 `GzhVideoUploader` 一致。浏览器生命周期管理委托给 `_session`。

#### P0-2：双重发布调度路径 ✅ 已统一

`LegacyPlatformExecutor` 已重构为 Registry 消费者，`_publish_via_registry` 统一处理所有平台。`_publish_wechat_keep_browser` 为批量微信场景的特殊优化（复用浏览器），输出格式一致为 `(success, message)`。

#### P0-3：Legacy Adapter 大量样板代码 ✅ 已提取

已实现 `GenericPublisherAdapter(platform, task_factory, publisher_factory)` 模板，7 个平台通过 `make_*_adapter()` 工厂注册，消除重复样板。

### 5.2 中等问题（P1）

#### P1-1：`core/base.py` 职责过重（365 行）

混合了：
- 领域枚举（`Platform`）
- 领域数据（8 个 `PublishTask` 子类）
- 基础设施抽象（`Publisher` ABC + 日志）
- 验证逻辑（`validate()` 方法）

**建议**：
- `Platform` 枚举 → `domain/`
- `Publisher` ABC → `infrastructure/` 或提升为独立端口
- 各 Task 类迁移到 `domain/`

#### P1-2：GUI 线程安全缺陷 ✅ 已修复

`PublisherApp` 已使用 `threading.Lock` 保护 `logs` 和 `is_publishing`：`add_log`、`get_logs`、`clear_logs` 及 `is_publishing` 的读写均在锁内。

#### P1-3：`shared/__init__.py` ~~违反 eager import 规则~~ ✅ 已修复

`shared/__init__.py` 已改为 `__getattr__` 延迟加载，与 `core/__init__.py` 一致。

#### P1-4：`socket.setdefaulttimeout(1800)` 全局污染 ✅ 已修复

YouTube 已使用 `RequestsHttpAdapter` 封装 `requests.Session`，超时与代理均限定在 Session 内，不再修改全局 `socket` 或 `os.environ`。

#### P1-5：环境变量全局突变 ✅ 已修复

YouTube 代理通过 `RequestsHttpAdapter` 的 `session.proxies` 配置，不修改 `os.environ`。

#### P1-6：`publish_gzh_drafts.py` 游离于架构之外 ✅ 已融合

- 核心逻辑已在 `core/gzh_drafts.py`
- 已新增子命令 `copublisher gzh-drafts <content_dir> [--skip N]`
- 根脚本保留为薄转发层（向后兼容）

#### P1-7：`src/media_publisher/` 残留

已确认该目录不存在（glob 未发现），无需操作。

### 5.3 改进建议（P2）

#### P2-1：`_find_config_file()` ~~在每个 Publisher 中重复~~ ✅ 已提取

已提取到 `shared/config.py` 的 `find_config_file()`，各 Publisher 已统一使用。

#### P2-2：返回值类型不统一

| 层 | 返回类型 |
|---|---------|
| `Publisher.publish()` | `Tuple[bool, Optional[str]]` |
| `LegacyPlatformExecutor` | `dict[str, tuple[bool, str]]` |
| `Legacy*PublisherAdapter` | `PlatformRunOutcome` |
| `RunJobUseCase` | `dict[str, Any]` (RunResult.as_dict()) |

四种不同的结果表示在不同层之间传递。

**建议**：统一使用 `PlatformRunOutcome`（或其 dict 序列化形式）作为标准发布结果。

#### P2-3：`import` 语句位置不规范

`youtube.py` 中：
```python
def _setup_proxy(logger_obj):
    ...

import httplib2            # ← 在函数定义之后
import requests
from google.auth.transport.requests import Request
```

以及 `publish()` 方法内部：
```python
import os           # ← 方法内 import
import time         # ← 方法内 import
```

**建议**：模块级 import 统一放在文件顶部。对 `youtube.py` 的 google 相关 import，如确需延迟可使用函数内导入但应添加注释说明原因。

#### P2-4：README 项目结构过时

README 中的项目结构图仍是早期版本，未包含 `domain/`、`application/`、`infrastructure/`、`interfaces/` 等新增层。

#### P2-5：缺少 `conftest.py` 和 pytest 配置

测试全部使用 `unittest.TestCase`，未配置 pytest fixture、参数化测试、覆盖率收集等。

---

## 6. 代码质量审查

### 6.1 代码量统计

| 模块 | Python 文件数 | 总行数 (约) | 说明 |
|------|:---:|:---:|------|
| `core/` | 12 | ~2,800 | 发布器实现（wechat.py 最长 ~770 行，gzh_video.py ~960 行） |
| `domain/` | 3 | ~190 | 精简的领域模型 |
| `application/` | 4 | ~300 | UseCase + 服务 |
| `infrastructure/` | 4 | ~510 | Registry + Adapter + StateStore |
| `interfaces/cli/` | 3 | ~410 | CLI 命令实现 |
| `gui/` | 1 | ~690 | Gradio UI |
| `shared/` | 2 | ~60 | 工具函数 |
| `__main__.py` | 1 | ~255 | 入口 |
| **合计** | **30** | **~7,700** | — |

### 6.2 复杂度热点

| 文件 | 方法 | 圈复杂度（估） | 问题 |
|------|------|:---:|------|
| `gzh_video.py` | `_click_save_and_wait()` | 15+ | 多层嵌套循环 + JS evaluate + 多种完成信号判断 |
| `gzh_video.py` | `_select_cover_from_local()` | 12+ | 多步对话框交互 + JS 事件分发 |
| `wechat.py` | `get_draft_page_text()` | 12+ | 嵌套回调 + iframe 滚动分页 |
| `wechat.py` | `_wait_for_upload_complete()` | 10+ | 三种完成信号轮询 |
| `gui/app.py` | `publish_legacy()` | 8 | 参数过多（13 个） |

### 6.3 函数参数过多

| 函数 | 参数数量 |
|------|:---:|
| `PublisherApp.publish_legacy()` | 13 |
| `LegacyPlatformExecutor.run_legacy_script()` | 6 |
| `LegacyPlatformExecutor.run_episode_adapter()` | 6 |
| `RunJobUseCase._event()` | 6 |

超过 5 个参数时应考虑引入参数对象。

---

## 7. 安全性审查

### 7.1 路径注入防护

| 检查点 | 状态 | 备注 |
|--------|:---:|------|
| `job_id` 文件路径拼接 | ✅ | `sanitize_identifier` 校验 |
| `account` 认证文件路径 | ✅ | `sanitize_identifier` 校验 |
| `user_name` 浏览器状态路径 | ✅ | `sanitize_identifier` 校验 |
| `org_run_id` 报告路径 | ✅ | `sanitize_identifier` 校验 |
| `video_path` / `script_path` | ✅ | `JobSpec.from_payload` 拒绝含 `..` 的路径；`load_script_data` 1MB 限制 |

### 7.2 输入大小限制

| 输入源 | 限制 | 状态 |
|--------|------|:---:|
| Job 文件 (`RunJobUseCase`) | 1MB | ✅ |
| Blue Ocean 输入 | 1MB | ✅ |
| ep*.json (`EpisodeAdapter`) | 10 MB | ✅ |
| script.json (CLI workflows) | 1 MB | ✅ |
| GUI JSON 脚本输入 | 1 MB | ✅ |

### 7.3 `sanitize_identifier` 实现与文档 ✅ 已对齐

`shared/security.py` 模块与函数文档已明确说明：有意允许非 ASCII 字符（如中文账号名），不限于 ASCII letters/digits/_/-。

### 7.4 凭据安全

| 凭据类型 | 存储位置 | 加密 | 权限 |
|---------|---------|:---:|:---:|
| 微信认证状态 | `~/.copublisher/wechat_auth*.json` | ✗ | 0o600 ✅ |
| YouTube Token | `config/youtube_token.json` | ✗ | 0o600 ✅ |
| Medium Token | `config/medium_token.txt` | ✗ | 明文 |
| Twitter 凭据 | `config/twitter_credentials.json` | ✗ | 明文 |
| TikTok 凭据 | `config/tiktok_credentials.json` | ✗ | 明文 |
| Instagram 凭据 | `config/instagram_credentials.json` | ✗ | 明文 |

所有凭据以明文存储且无 `0600` 权限保护。对于个人工具可接受，但如果多人共用或部署到服务器，需加强。

---

## 8. 测试体系评估

### 8.1 测试覆盖概况

| 测试维度 | 文件数 | 用例数 | 覆盖区域 |
|---------|:---:|:---:|------|
| 领域模型 | 2 | 5 | JobSpec、RunResult schema |
| 应用服务 | 3 | 7 | IdempotencyService、PublishContentUseCase、BlueOceanAdapter |
| 基础设施 | 2 | 5 | Registry、OrgRunReporter |
| CLI 合约 | 3 | 7 | job 子命令、向后兼容 |
| 安全 | 1 | 5 | sanitize_identifier、auth 路径 |
| 架构守卫 | 2 | 4 | 无副作用导入、层间隔离 |
| **合计** | **16** | **41** | — |

### 8.2 未覆盖区域

| 区域 | 风险 |
|------|------|
| 7 个平台发布器实际行为 | 高（需外部 API，可 mock 测试） |
| GUI 交互逻辑 | 中（`PublisherApp` 状态管理、线程安全） |
| `EpisodeAdapter` 适配逻辑 | 中（多平台 task 构建） |
| 批量发布流程 (`run_batch_cli`) | 中（文件扫描 + 批量执行） |
| `publish_gzh_drafts.py` | 低（独立脚本，非核心路径） |
| 错误恢复路径（网络超时、重试） | 中（仅 YouTube 有重试，其余未测） |

### 8.3 测试基础设施建议

1. **迁移到 pytest**：支持 fixture、参数化、插件生态
2. **添加 `conftest.py`**：提供共用的 `tmp_path`、fake publisher 等 fixture
3. **引入 `pytest-cov`**：量化覆盖率
4. **Mock 测试发布器**：使用 `unittest.mock.patch` 测试 `Publisher.publish()` 的调用链
5. **添加集成测试标记**：`@pytest.mark.integration` 区分需要真实 API 的测试

---

## 9. 扩展性评估

### 9.1 新增平台

**当前流程**（添加一个新平台需要修改的文件）：

| 步骤 | 文件 | 修改内容 |
|------|------|---------|
| 1 | `core/base.py` | 新增 `Platform` 枚举值 + `NewPlatformPublishTask` |
| 2 | `core/new_platform.py` | 实现 `NewPlatformPublisher` |
| 3 | `core/__init__.py` | 添加 lazy export 条目 |
| 4 | `__init__.py` | 添加 lazy export 条目 |
| 5 | `infrastructure/publishers/legacy.py` | 新增 `LegacyNewPlatformAdapter` |
| 6 | `infrastructure/registry.py` | 在 `build_default_registry()` 中注册 |
| 7 | `infrastructure/publishers/executor.py` | 在 `run_episode_adapter()` 添加分支 |
| 8 | `interfaces/cli/workflows.py` | 更新 `ALL_PLATFORMS` 列表 |
| 9 | `domain/models.py` | 更新 `VIDEO_PLATFORMS` 或 `ARTICLE_PLATFORMS` |
| 10 | `gui/app.py` | 更新 `CheckboxGroup` choices |

**需要修改 10 个文件**——这是扩展性的主要短板。

### 9.2 改进方案

先给结论：**新增平台不应只放在 `domain` 或 `core` 单层，而应按职责拆分**。

- `domain`：放**平台语义**（平台标识、任务 schema、能力声明）
- `core`（目标态为 `publishers/`）：放**平台实现**（认证、API/浏览器调用、重试细节）
- `infrastructure`：放注册与装配（Registry、Adapter）

换句话说，`domain` 决定“是什么”，`core/publishers` 决定“怎么做”。

#### 推荐边界（新增平台时）

1. 在 `domain` 增加平台定义  
   - `Platform` 枚举值  
   - 对应 `Task`（视频或文章）  
   - `capabilities` 元数据（如 `supports_video`、`supports_article`、`supports_schedule`）
2. 在 `core`（或未来 `publishers/`）新增 `NewPlatformPublisher` 实现  
3. 在 `infrastructure/registry.py` 注册映射（`Platform -> Publisher/Adapter`）

CLI / GUI / workflow 不再维护平台硬编码列表，而是统一读取 Registry + capabilities。

#### 为什么不建议“只在 core 新增”

- 会把平台语义和实现细节耦合在一起，继续放大 `core/base.py` 的 God Object 倾向
- `domain` 无法成为稳定契约层，应用层会被迫依赖实现细节
- 与目标态分层（附录 A）冲突，后续拆分成本更高

#### 为什么也不建议“只在 domain 新增”

- `domain` 只能定义规则，不能承担实际发布（外部 API、浏览器自动化）
- 缺少 Publisher 实现，Registry 无法完成可运行装配

#### 过渡期落地（当前仓库）

在尚未完成 `core -> publishers/` 拆分前，可采用“`domain + core + registry` 三步”：
1. `domain` 先收敛平台定义与 capabilities  
2. `core/new_platform.py` 放发布实现  
3. `registry` 统一注册，逐步移除 `if-elif` 与手工 export

### 9.3 调度系统集成

当前通过 `job` 子命令 + Blue Ocean adapter 支持外部调度。架构良好：

```
外部调度 → blue_ocean_adapter → RunJobUseCase → Registry → Adapters
                                      ↓
                              IdempotencyService
                                      ↓
                              ExecutionStateStore
```

`org_state` 映射（`SUCCESS` / `RETRY_PENDING` / `MANUAL_TAKEOVER` / `FAILED`）为上游调度提供了清晰的决策信号。

---

## 10. 改进路线图

### Phase 1：消除冗余（1-2 周）

| 编号 | 任务 | 优先级 | 影响文件 |
|:---:|------|:---:|------|
| 1.1 | `WeChatPublisher` 组合 `PlaywrightBrowser` | P0 | `core/wechat.py`, `core/browser.py` |
| 1.2 | 提取通用 `GenericPublisherAdapter`，消除 7 个 Adapter 的样板 | P0 | `infrastructure/publishers/legacy.py` |
| 1.3 | 提取公共 `_find_config_file()` 到 `shared/` 或基类 | P2 | 6 个 Publisher 文件 |
| 1.4 | 删除 `src/media_publisher/` 残留 | P1 | 文件系统 |
| 1.5 | `shared/__init__.py` 改为 lazy import | P1 | `shared/__init__.py` |

### Phase 2：统一发布路径（2-3 周）

| 编号 | 任务 | 优先级 | 影响文件 |
|:---:|------|:---:|------|
| 2.1 | 统一结果类型为 `PlatformRunOutcome` | P0 | 全链路 |
| 2.2 | `PublishContentUseCase` 改为 Registry 驱动 | P0 | `application/usecases/publish_content.py`, `infrastructure/publishers/executor.py` |
| 2.3 | 废弃 `LegacyPlatformExecutor`，逻辑合并到 Registry 路径 | P0 | `executor.py`, `gui/app.py`, `workflows.py` |
| 2.4 | GUI/CLI 统一消费 `RunResult` 格式 | P1 | `gui/app.py`, `workflows.py` |

### Phase 3：增强健壮性（持续）

| 编号 | 任务 | 优先级 | 影响文件 |
|:---:|------|:---:|------|
| 3.1 | 修复 `socket.setdefaulttimeout` 全局污染 | P1 | `core/youtube.py` |
| 3.2 | 修复 `_setup_proxy` 全局 `os.environ` 突变 | P1 | `core/youtube.py` |
| 3.3 | GUI 线程安全（Lock 或 Queue） | P1 | `gui/app.py` |
| 3.4 | `EpisodeAdapter` 和 CLI script 读取添加大小限制 | P1 | `core/adapter.py`, `workflows.py` |
| 3.5 | `sanitize_identifier` 文档对齐实现 | P2 | `shared/security.py` |
| 3.6 | 凭据文件创建时设置 `0600` 权限 | P2 | `shared/io.py` |

### Phase 4：测试 & 可观测性（持续）

| 编号 | 任务 | 优先级 |
|:---:|------|:---:|
| 4.1 | 迁移到 pytest + 添加 `conftest.py` | P2 |
| 4.2 | Publisher Mock 测试（验证调用链） | P1 |
| 4.3 | GUI 组件测试 | P2 |
| 4.4 | 引入 `pytest-cov`，目标 80% domain/application | P2 |
| 4.5 | 更新 README 项目结构 | P2 |

### Phase 5：平台扩展性优化（未来）

| 编号 | 任务 | 说明 |
|:---:|------|------|
| 5.1 | 平台自注册机制 | 基于 entry_points 或 Registry 自动扫描 |
| 5.2 | 平台 capabilities 驱动 UI | CheckboxGroup 从 Registry 动态生成 |
| 5.3 | `base.py` 拆分 | Task 类、Publisher ABC、Platform 枚举各自独立 |

---

## 附录 A：分层架构目标态

```
src/copublisher/
├── domain/                      # 纯领域（无外部依赖）
│   ├── platform.py              #   Platform 枚举
│   ├── tasks.py                 #   PublishTask / ArticlePublishTask + 具体 Task
│   ├── models.py                #   JobSpec
│   ├── result.py                #   RunResult / PlatformRunOutcome
│   └── error_codes.py           #   ErrorCode + ErrorPolicy
├── application/                 # 用例编排
│   ├── ports.py                 #   PublisherPort / StateStorePort (Protocol)
│   ├── usecases/
│   │   ├── publish_content.py   #   统一发布 UseCase（Registry 驱动）
│   │   └── run_job.py           #   Job 执行 UseCase
│   └── services/
│       ├── idempotency.py
│       ├── result_builder.py
│       └── org_run_reporter.py
├── infrastructure/              # 外部集成
│   ├── registry.py              #   PublisherRegistry + 自动注册
│   ├── adapters/                #   GenericPublisherAdapter
│   ├── state_store/
│   └── blue_ocean/
├── publishers/                  # 各平台实现（替代 core/）
│   ├── base.py                  #   Publisher ABC
│   ├── browser.py               #   PlaywrightBrowser
│   ├── wechat.py
│   ├── youtube.py
│   ├── ...
│   └── gzh_video.py
├── interfaces/
│   ├── cli/
│   └── gui/
└── shared/
    ├── io.py
    ├── security.py
    └── config.py                #   _find_config_file 等公用函数
```

---

## 附录 B：关键指标对照

| 指标 | 现状 | 目标 |
|------|:---:|:---:|
| 新增平台需修改文件数 | 10 | 2-3 |
| Legacy Adapter 样板行数 | ~390 | <50 |
| 发布调度路径数 | 2 | 1 |
| 结果类型数 | 4 | 1 |
| 测试用例数 | 41 | 80+ |
| domain/application 覆盖率 | ~60% | 80%+ |
| 全局状态突变点 | 2 | 0 |
| `_find_config_file` 重复次数 | 6 | 1 |
