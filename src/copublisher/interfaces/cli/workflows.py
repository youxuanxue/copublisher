"""
CLI workflow implementations extracted from __main__.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from copublisher.application.usecases.publish_content import PublishContentUseCase
from copublisher.shared.io import atomic_write_text, read_json_with_size_limit

ALL_PLATFORMS = ["wechat", "youtube", "medium", "twitter", "devto", "tiktok", "instagram"]
_MAX_CONFIG_SIZE = 1 * 1024 * 1024  # 1 MB


def _read_json_with_size_limit(path: Path, label: str = "配置文件") -> dict:
    """读取 JSON 文件，限制大小防止 DoS。"""
    return read_json_with_size_limit(path, _MAX_CONFIG_SIZE, label)


ARTICLE_PLATFORMS = ["medium", "twitter", "devto"]
VIDEO_PLATFORMS = ["wechat", "youtube", "tiktok", "instagram"]


def parse_platform_arg(platform_str: str) -> list[str]:
    if not platform_str:
        return []
    if platform_str == "all-articles":
        return ARTICLE_PLATFORMS
    if platform_str == "all-videos":
        return VIDEO_PLATFORMS
    if platform_str == "all":
        return ALL_PLATFORMS
    if platform_str == "both":
        return ["wechat", "youtube"]

    platforms = [p.strip().lower() for p in platform_str.split(",")]
    invalid = [p for p in platforms if p not in ALL_PLATFORMS]
    if invalid:
        print(f"❌ 未知平台: {', '.join(invalid)}")
        print(f"   支持的平台: {', '.join(ALL_PLATFORMS)}")
        sys.exit(1)
    return platforms


def scan_batch_dir(batch_dir: Path) -> list[tuple[Path, Path]]:
    output_dir = batch_dir / "output"
    config_dir = batch_dir / "config"
    if not output_dir.exists():
        print(f"❌ 未找到 output 目录: {output_dir}")
        sys.exit(1)
    if not config_dir.exists():
        print(f"❌ 未找到 config 目录: {config_dir}")
        sys.exit(1)

    videos = sorted(output_dir.glob("*-Clip.mp4"))
    if not videos:
        print(f"❌ 未找到视频文件 (*-Clip.mp4): {output_dir}")
        sys.exit(1)

    pairs: list[tuple[Path, Path]] = []
    for video in videos:
        stem = video.stem.replace("-Clip", "-Strategy")
        config = config_dir / f"{stem}.json"
        if not config.exists():
            print(f"⚠️  跳过 {video.name}：未找到配置 {config.name}")
            continue
        pairs.append((video, config))
    return pairs


def run_episode_cli(args, log_callback: Callable[[str], None] = print) -> None:
    ep_path = Path(args.episode)
    if not ep_path.exists():
        print(f"❌ ep*.json 文件不存在: {ep_path}")
        sys.exit(1)
    if not args.platform:
        print("❌ Episode 模式需要 --platform 参数")
        print("   例: --platform medium,twitter")
        sys.exit(1)

    platforms = parse_platform_arg(args.platform)
    video_platforms_requested = [p for p in platforms if p in VIDEO_PLATFORMS]
    video_path = Path(args.video) if args.video else None
    if video_platforms_requested and not video_path:
        print(f"❌ 平台 {', '.join(video_platforms_requested)} 需要 --video 参数")
        sys.exit(1)
    if video_path and not video_path.exists():
        print(f"❌ 视频文件不存在: {video_path}")
        sys.exit(1)

    usecase = PublishContentUseCase(log_callback=log_callback)
    results = usecase.run_episode_adapter(
        episode_path=ep_path,
        platforms=platforms,
        video_path=video_path,
        privacy=args.privacy,
        account=getattr(args, "account", None),
        keep_wechat_browser_open=False,
    )
    print(f"\n{'='*50}")
    print("📊 发布结果汇总")
    print(f"{'='*50}")
    for platform, (success, detail) in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {platform}: {detail or '(无详情)'}")


def run_legacy_cli(args, log_callback: Callable[[str], None] = print) -> dict[str, dict[str, Any]]:
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ 视频文件不存在: {video_path}")
        sys.exit(1)

    if not args.script:
        print("⚠️  未指定脚本文件，请使用 --script 参数指定")
        sys.exit(1)
    script_path = Path(args.script)
    if not script_path.exists():
        print(f"❌ 脚本文件不存在: {script_path}")
        sys.exit(1)
    try:
        script_data = _read_json_with_size_limit(script_path, "脚本文件")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"❌ JSON 格式错误: {exc}")
        sys.exit(1)

    usecase = PublishContentUseCase(log_callback=log_callback)
    raw_results = usecase.run_legacy_script(
        video_path=video_path,
        script_data=script_data,
        platform=args.platform or "wechat",
        privacy=args.privacy,
        account=args.account,
        keep_wechat_browser_open=False,
    )
    return {
        platform_name: {"success": success, "message": message}
        for platform_name, (success, message) in raw_results.items()
    }


def run_list_drafts(args, log_callback: Callable[[str], None] = print) -> None:
    batch_dir_str = args.batch_dir.strip()
    batch_dirs = [Path(p.strip()) for p in batch_dir_str.split(",") if p.strip()]
    if not batch_dirs:
        print("❌ 请指定 --batch-dir（可逗号分隔多个目录）")
        sys.exit(1)
    for d in batch_dirs:
        if not d.exists():
            print(f"❌ 目录不存在: {d}")
            sys.exit(1)

    usecase = PublishContentUseCase(log_callback=log_callback)
    draft_full_text, expected, dump_dir = usecase.run_list_drafts(
        batch_dirs=batch_dirs,
        account=getattr(args, "account", None),
    )
    if not expected:
        print("❌ 未找到任何预期视频配置")
        sys.exit(1)

    if dump_dir:
        dump_path = dump_dir / "draft_page_dump.txt"
        try:
            atomic_write_text(dump_path, draft_full_text, encoding="utf-8")
            print(f"📄 草稿箱全文已保存至: {dump_path}（可人工核查）")
        except Exception:
            pass

    def matched(title: str, desc: str) -> bool:
        title = (title or "").strip()
        desc = (desc or "").strip()[:50]
        return (title and len(title) >= 4 and title in draft_full_text) or (
            desc and len(desc) >= 10 and desc in draft_full_text
        )

    missing = []
    for series_name, video_name, title, desc in expected:
        if not matched(title, desc):
            missing.append((series_name, video_name, title or desc[:30]))

    print("📊 草稿箱对比结果")
    print("=" * 50)
    if not missing:
        print("✅ 预期草稿均在草稿箱中，无缺失。")
        return
    print(f"❌ 以下 {len(missing)} 条未在草稿箱中找到（可能上传/保存失败）：\n")
    for series_name, video_name, label in missing:
        print(f"  [{series_name}] {video_name}  — {label}")


def run_batch_cli(args, log_callback: Callable[[str], None] = print) -> None:
    batch_dir = Path(args.batch_dir)
    if not batch_dir.exists():
        print(f"❌ 目录不存在: {batch_dir}")
        sys.exit(1)

    platform = args.platform or "wechat"
    if platform != "wechat":
        print(f"❌ 批量模式目前仅支持 wechat 平台，收到: {platform}")
        sys.exit(1)

    pairs = scan_batch_dir(batch_dir)
    if not pairs:
        print("❌ 未找到可发布的视频-配置对")
        sys.exit(1)

    only_arg = getattr(args, "only", None)
    if only_arg:
        only_tokens = [t.strip() for t in only_arg.split(",") if t.strip()]
        if only_tokens:
            original_count = len(pairs)
            pairs = [(v, c) for v, c in pairs if any(t in v.stem for t in only_tokens)]
            if not pairs:
                print(f"❌ --only {only_arg} 未匹配到任何视频")
                sys.exit(1)
            print(f"📌 仅发布指定集数: {only_tokens}（共 {len(pairs)} 条，已过滤 {original_count - len(pairs)} 条）")

    print(f"\n📂 系列目录: {batch_dir}")
    print(f"📊 共发现 {len(pairs)} 个视频\n")
    for i, (video, config) in enumerate(pairs, 1):
        try:
            script_data = _read_json_with_size_limit(config, f"配置 {config.name}")
        except ValueError as e:
            print(f"❌ {config.name}: {e}")
            sys.exit(1)
        wechat_data = script_data.get("wechat", {})
        title = (wechat_data.get("title") or "").strip()
        print(f"  {i:2d}. {video.name}  ->  {title}")
    print()

    account = getattr(args, "account", None)
    if account:
        print(f"📌 账号: {account}")

    usecase = PublishContentUseCase(log_callback=log_callback)
    results = usecase.run_wechat_batch(
        batch_dir=batch_dir,
        pairs=pairs,
        account=account,
    )

    print(f"\n{'='*50}")
    print("📊 批量发布结果汇总")
    print(f"{'='*50}")
    success_count = 0
    failed_list = []
    for (video, _), (success, msg) in zip(pairs, results):
        status = "✅" if success else "❌"
        if success:
            success_count += 1
        else:
            failed_list.append((video.name, msg))
        print(f"  {status} {video.name}: {msg}")

    report_name = f"wechat_batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = batch_dir / report_name
    lines = [
        "# 微信视频号批量发布报告",
        f"# 时间: {datetime.now().isoformat(timespec='seconds')}",
        f"# 目录: {batch_dir}",
        f"# 成功: {success_count}  失败: {len(pairs) - success_count}",
        "",
    ]
    for (video, _), (success, msg) in zip(pairs, results):
        line = "OK\t" if success else "FAIL\t"
        lines.append(line + f"{video.name}\t{msg}")
    if failed_list:
        lines.append("")
        lines.append("# 失败列表（可据此重试）")
        for name, msg in failed_list:
            lines.append(f"{name}\t{msg}")
    atomic_write_text(report_path, "\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n📄 结果已写入: {report_path}")

