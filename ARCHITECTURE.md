# Copublisher 架构契约

**Agent/维护者速览**：依赖方向 `shared ← domain ← core/infra ← application ← interfaces`；`__main__` 仅依赖 shared + interfaces。禁止：shared/domain 引用业务层、interfaces 直接 import core、模块级副作用、非原子写覆盖。Job 输入见 §4.1，输出与错误码见 `domain/result.py`、`domain/error_codes.py`。新增平台改 domain/platform + domain/tasks + core/xxx + infrastructure/registry + legacy。

## 1. 目录结构

```
src/copublisher/
├── __init__.py, __main__.py
├── domain/           # platform, tasks, models, result, error_codes（仅依赖 shared）
├── application/      # usecases (publish_content, run_job, gzh_drafts), services
├── infrastructure/    # registry, gzh_drafts_runner, publishers/, state_store/
├── core/              # base (Publisher ABC), adapter, browser, wechat, youtube, medium, twitter, devto, tiktok, instagram, gzh, gzh_video, gzh_drafts
├── interfaces/cli/    # job_command, job_runner, workflows, gzh_drafts_command, verify_command
├── interfaces/gui/    # app.py (Gradio)
├── gui/               # shim → interfaces.gui（兼容）
└── shared/            # io, security, config（仅标准库）
```

## 2. 依赖矩阵

| 引用方 \ 被引用方 | shared | domain | core | infra | app | interfaces |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| shared | — | ✗ | ✗ | ✗ | ✗ | ✗ |
| domain | ✓ | — | ✗ | ✗ | ✗ | ✗ |
| core | ✓ | ✓(类型) | — | ✗ | ✗ | ✗ |
| infrastructure | ✓ | ✓ | ✓ | — | ✗ | ✗ |
| application | ✓ | ✓ | ✗ | ✓ | — | ✗ |
| interfaces | ✓ | ✓ | ✗ | ✓ | ✓ | — |
| __main__ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |

infrastructure 的 Task 只从 domain 导入，Publisher 从 core 导入。interfaces 不直接 import core。

## 3. 禁止规则

- shared 不引用业务层；domain 不引用 infra/core/application
- core 不引用 application/infrastructure；application 不引用 interfaces
- interfaces 不直接 import core
- `__init__.py` 无 eager import（用 `__getattr__` 延迟）
- 状态文件原子写（先写临时再 rename）；路径/输入经 sanitize 或拒绝 `..`；Job/script ≤1MB，ep*.json ≤10MB

## 4. Job 契约

**输入 (job.json)**：`job_id`|`id`, `mode`(legacy), `platforms`|`platform`, `video`, `script`（路径禁 `..`，script ≤1MB）, `privacy`, `account`, `dry_run`。

**输出 (RunResult)**：`status`(success|failed|partial), `retryable`, `manual_takeover_required`, `artifacts`, `error`(code, message, platform, details), `metrics`。实现见 `domain/result.py`。

**错误码**：MP_INPUT_INVALID, MP_AUTH_REQUIRED, MP_PLATFORM_TIMEOUT, MP_PLATFORM_CHANGED, MP_RATE_LIMIT, MP_PLATFORM_ERROR, MP_INTERNAL_ERROR。策略见 `domain/error_codes.py`。

## 5. 新增平台

1. domain/platform.py 加枚举  
2. domain/tasks.py 加 Task（如需）  
3. core/xxx.py 实现 Publisher  
4. core/__init__.py 与 __init__.py 加 export  
5. infrastructure/publishers/legacy.py 加 task_factory + publisher_factory + make_xxx_adapter  
6. infrastructure/registry.py 中 register  
7. executor 若 Episode 需分支则加  
8. interfaces/gui/app.py 的 CheckboxGroup（可选）  

workflows 由 domain.platform 派生，无需改。

## 6. 项目文件

必须：README、本文件、pyproject.toml、uv.lock、.gitignore、src/、tests/、examples/、根脚本 verify_install.py 与 publish_gzh_drafts.py、gui/ shim、config/.gitignore、docs/README.md。.venv、__pycache__ 已 gitignore。两轮自检：逐项在用，无冗余可删，无关键遗漏。
