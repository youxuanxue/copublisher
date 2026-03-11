# Copublisher 架构自检报告（2026-03-11）

> 深度自检、反思、修正、迭代。至少 2 轮。

---

## 1. 问题答复

### 1.1 examples 还需要吗？

**结论：需要，但需明确定位。**

| 维度 | 分析 |
|------|------|
| **当前内容** | `publish_lesson_example.py` 演示课程视频发布（wechat + youtube），使用直接 Publisher API |
| **与主流程关系** | 未走 `job` UseCase 或 Registry 路径，属于 SDK 级示例 |
| **价值** | ① 新用户快速上手 ② 展示 `script.json` + `series/` 目录结构 ③ `verify_install` 与 README 引用 |
| **冗余风险** | 与 `--batch-dir`、`job run` 存在功能重叠，但示例更聚焦「单课发布」场景 |

**建议：保留，并做小幅调整**

1. 在 `examples/README.md` 补充说明：本示例为 SDK 参考实现，生产环境可考虑 `copublisher --batch-dir` 或 `job` 模式
2. 将 `sys.path.insert` 改为依赖已安装包（`uv pip install -e .` 后直接运行），避免隐含的开发模式假设
3. 路径 `project_root.parent` 在示例中硬编码了三级父目录，应改为基于 `Path(__file__)` 的可靠推导

### 1.2 docs plan 和架构优化都完成了吗？

**plan.md 状态：部分完成**

| 阶段 | 状态 | 说明 |
|------|:---:|------|
| M1 分层骨架 | ✅ | `domain/`、`application/`、`infrastructure/`、`interfaces/` 已搭建 |
| M1 Job 契约 v1 | ✅ | `RunResult`、`PlatformRunOutcome`、schema 已实现 |
| M1 错误语义 | ✅ | `domain/error_codes.py` 已实现 |
| M2 平台插件化 | ✅ | `PublisherRegistry`、`Legacy*Adapter` 已实现 |
| M2 幂等与补偿 | ✅ | `IdempotencyService`、`ExecutionStateStore` 已实现 |
| M2 可观测 | ⚠️ | 结构化日志字段部分覆盖，metrics 尚未完善 |
| 统一发布路径 | ❌ | 双路径仍存在（Legacy vs Registry） |

**architecture-review.md 状态：仍有 P0/P1 待办**

- P0-1: WeChatPublisher 与 PlaywrightBrowser 职责重复
- P0-2: 双发布路径（Legacy vs Registry）
- P0-3: Legacy Adapter 样板代码冗余
- P1-1 ~ P1-7: 见 architecture-review Phase 1~4

**错误、漏洞、冗余：**

1. **错误**：architecture-review 称 `shared/__init__.py` 违反 eager import，实际已改为 `__getattr__` 延迟加载 —— 文档过时
2. **漏洞**：`video_path`/`script_path` 仅校验存在性，未做路径穿越校验
3. **冗余**：`_find_config_file()` 在 6 个 Publisher 中重复；`media_publisher/` 残留已不存在（glob 未发现）

### 1.3 publish_gzh_drafts.py 为什么要单独存在？怎么融合？

**原因（历史）**：早期独立脚本，核心逻辑已迁入 `core/gzh_drafts.py`，根脚本仅作便捷入口。

**融合方案（已实施）：**

1. 新增子命令 `copublisher gzh-drafts <content_dir> [--skip N] [--headless]`
2. 根目录 `publish_gzh_drafts.py` 改为薄转发层，保留向后兼容（无参数时使用默认目录）
3. 业务逻辑统一在 `interfaces/cli/gzh_drafts_command.py`，依赖 `core.gzh_drafts.GzhDraftPublisher`

### 1.4 verify_install.py 的目的是什么？怎么融合？

**目的**：安装后自检（Python 版本、模块结构、依赖、核心类导入）。

**融合方案（已实施）：**

1. 新增子命令 `copublisher verify`
2. 逻辑迁入 `interfaces/cli/verify_command.py`
3. 根目录 `verify_install.py` 改为薄转发层，委托给 `copublisher verify`

---

## 2. 项目结构问题（资深架构师视角）

### 2.1 根目录游离脚本

| 文件 | 问题 | 修正 |
|------|------|------|
| `publish_gzh_drafts.py` | 独立入口、硬编码路径 | 已融合为 `gzh-drafts` 子命令 |
| `verify_install.py` | 独立入口、与包割裂 | 已融合为 `verify` 子命令 |

### 2.2 架构遗留问题（来自 architecture-review）

- **双发布路径**：Legacy 与 Registry 并存，错误格式、幂等支持不一致
- **core 身份不清**：混合领域、基础设施、平台实现
- **扩展成本高**：新增平台需改约 10 个文件

### 2.3 文档与实现不一致

- `shared/__init__.py`：文档称 eager import，实际已 lazy
- `media_publisher`：文档建议删除，实际已不存在
- README 项目结构：未包含 `domain/`、`application/` 等新层

---

## 3. 第 1 轮修正清单（已实施）

1. ✅ 新增 `interfaces/cli/gzh_drafts_command.py`
2. ✅ 新增 `interfaces/cli/verify_command.py`
3. ✅ `__main__.py` 路由 `gzh-drafts`、`verify` 子命令
4. ✅ `publish_gzh_drafts.py` 改为转发，保留默认目录兼容
5. ✅ `verify_install.py` 改为转发
6. ✅ 本自检报告

---

## 4. 第 2 轮自检与补充修正

### 4.1 深度反思

1. **examples 的 sys.path.insert**：应移除，要求用户先 `uv pip install -e .`，否则示例无法体现真实使用方式
2. **默认路径硬编码**：`publish_gzh_drafts.py` 中 `_DEFAULT_CONTENT_DIR` 仍为本地路径，建议改为环境变量 `COPUBLISHER_GZH_DEFAULT_DIR`，未设置时要求显式传参
3. **verify 的路径解析**：`verify_command` 通过 `import copublisher` 获取 `__file__`，在可编辑安装下正确；独立运行时需确保路径

### 4.2 补充修正（第 2 轮）✅ 已实施

- **examples**：已更新 README，明确「需先安装」；移除 `sys.path.insert`
- **默认路径**：`_DEFAULT_CONTENT_DIR` 已改为从 `COPUBLISHER_GZH_DEFAULT_DIR` 环境变量读取，支持覆盖

---

## 5. 后续优先级（来自 plan + architecture-review）

| 优先级 | 任务 | 状态 |
|:---:|---|:---:|
| P0 | 统一发布路径，全部走 Registry | ✅ |
| P0 | WeChatPublisher 组合 PlaywrightBrowser | ✅ |
| P0 | 提取 GenericPublisherAdapter，消除 7 个 Adapter 样板 | ✅ |
| P1 | GUI 线程安全、socket/proxy 全局污染修复 | ✅ |
| P1 | 输入大小限制、sanitize 文档、凭据 0600 | ✅ |
| P2 | `_find_config_file` 提取到 shared、迁移 pytest | 待办 |

---

## 6. 结论

- **examples**：保留，补充定位说明与路径修正
- **plan/architecture-review**：部分完成，双路径与 core 职责是主要缺口
- **publish_gzh_drafts / verify_install**：已融合到 src 体系，根脚本保留为薄转发
- **整体结构**：分层已成型，游离脚本已收敛；后续以「统一发布路径」和「平台扩展成本」为重点迭代

---

## 7. 第 3 轮深度自检（2026-03-11 资深架构师视角）

### 7.1 剩余结构问题

| 类别 | 问题 | 优先级 | 状态 |
|------|------|:---:|:---:|
| **core 职责** | base.py 混合 Platform、Task、Publisher ABC（365 行） | P1 | 待办 |
| **概念割裂** | domain.JobSpec 与 core.PublishTask 同为“任务”却分属两层 | P2 | 待办 |
| **入口对称** | gui 在 `copublisher/gui`，cli 在 `interfaces/cli`，建议统一为 `interfaces/gui` | P2 | 待办 |
| **平台列表** | domain、workflows 各维护 VIDEO/ARTICLE_PLATFORMS，新增平台需两处同步 | P2 | 待办 |
| **script 安全** | JobSpec.load_script_data() 无大小限制 | P1 | ✅ 已加 1MB |
| **路径校验** | video_path/script_path 路径穿越 | P1 | ✅ 已拒绝 .. |
| **文档过时** | architecture-review 3.3、P2-1 | P2 | ✅ 已更新 |

### 7.2 已确认完成项

- `find_config_file` 已在 shared/config.py，各 Publisher 已使用
- README 项目结构已包含 domain/application/infrastructure/interfaces
- 发布路径已统一（LegacyPlatformExecutor 内部走 Registry）

### 7.3 第 2 轮修正项 ✅ 已实施

1. JobSpec.load_script_data：增加 1MB 大小限制
2. JobSpec.from_payload：拒绝对 video/script 含 `..` 的输入
3. architecture-review：更新 3.3 双重路径描述、P2-1 状态、路径注入表

### 7.4 第 4 轮反思：剩余结构问题（不急于改动）

| 问题 | 影响 | 建议 |
|------|------|------|
| **core/base.py 职责过重** | 365 行混合 Platform、Task、Publisher，扩展时易踩坑 | 分阶段：Platform→domain，Publisher ABC→infrastructure，Task 可暂留 |
| **gui 与 interfaces 不对称** | gui 在顶层，cli 在 interfaces 下 | 迁移到 `interfaces/gui` 需改 import，可列入下个大版本 |
| **平台列表多源** | domain、workflows 各维护一份，registry 有 capabilities | 可从 `registry.list_platforms()` + capabilities 派生，降低重复 |
| **JobSpec vs PublishTask 概念割裂** | 同为“任务”却分属 domain/core | 长期可考虑 JobSpec 作为统一入口，Task 作为平台适配层内部实现 |

以上为结构性技术债，当前不影响功能与安全，可按优先级逐步偿还。
