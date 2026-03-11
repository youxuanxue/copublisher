"""
媒体发布工具 - 入口文件

支持命令行参数启动 GUI 或直接发布到多个平台。
支持三种模式:
  - 传统模式: --video + --script (微信/YouTube)
  - Episode 模式: --episode ep*.json --platform medium,twitter (多平台)
  - 批量模式: --batch-dir <series_dir> --platform wechat (批量发布系列视频)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from copublisher.shared.io import atomic_write_text


def main():
    """主入口函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "job":
        run_job_subcommand(sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "gzh-drafts":
        from copublisher.interfaces.cli.gzh_drafts_command import run_gzh_drafts_cli
        run_gzh_drafts_cli(sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        run_verify_cli(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(
        description="火箭发射 - 多平台内容一键发布工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动 GUI 界面
  copublisher

  # 批量模式: 将系列目录下所有视频批量保存到微信视频号草稿箱
  copublisher --batch-dir /path/to/series/yingxiongernv --platform wechat --account 奶奶讲故事

  # Episode 模式: 从 ep*.json 发布到 Medium + Twitter
  copublisher --episode ep01.json --platform medium,twitter

  # Episode 模式: 发布到所有文章平台 (Medium + Twitter + Dev.to)
  copublisher --episode ep01.json --platform all-articles

  # Episode 模式: 发布到 TikTok (需要视频文件)
  copublisher --episode ep01.json --platform tiktok --video /path/to/video.mp4

  # 传统模式: 发布到微信视频号
  copublisher --video /path/to/video.mp4 --platform wechat --script /path/to/script.json

  # 传统模式: 发布到 YouTube Shorts
  copublisher --video /path/to/video.mp4 --platform youtube --script /path/to/script.json
        """
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=7860,
        help="GUI 服务端口 (默认: 7860)"
    )
    
    parser.add_argument(
        "--share",
        action="store_true",
        help="生成公开分享链接"
    )
    
    parser.add_argument(
        "--batch-dir",
        type=str,
        help="系列目录路径（批量模式），自动匹配 output/*-Clip.mp4 和 config/*-Strategy.json"
    )
    
    parser.add_argument(
        "--episode",
        type=str,
        help="ep*.json 素材文件路径（Episode 模式）"
    )
    
    parser.add_argument(
        "--video",
        type=str,
        help="视频文件路径（视频平台必需）"
    )
    
    parser.add_argument(
        "--platform",
        type=str,
        default=None,
        help=(
            "发布平台，逗号分隔。可选: "
            "medium, twitter, devto, tiktok, instagram, wechat, youtube, "
            "all-articles, all-videos, both (传统兼容)"
        )
    )
    
    parser.add_argument(
        "--script",
        type=str,
        help="JSON 脚本文件路径（传统模式）"
    )
    
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default="private",
        help="视频隐私设置 (默认: private)"
    )
    
    parser.add_argument(
        "--account",
        type=str,
        default=None,
        help="微信视频号账号名称，用于区分多账号登录状态（如 '奶奶讲故事'）"
    )
    
    parser.add_argument(
        "--list-drafts",
        action="store_true",
        help="与 --batch-dir 同用：打开草稿箱列表，与预期列表对比，输出可能未保存成功的视频"
    )
    
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="批量模式仅发布指定集数，逗号分隔，如 04,09,10,12,17,20（匹配文件名中含该编号的视频）"
    )
    parser.add_argument(
        "--job-file",
        type=str,
        default=None,
        help="结构化任务文件路径（job 模式）"
    )
    parser.add_argument(
        "--result-file",
        type=str,
        default=None,
        help="结构化结果输出路径（job 模式）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出结构化 JSON 结果（用于调度系统）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅校验任务，不执行实际发布（job 模式）"
    )
    
    args = parser.parse_args()
    
    if args.job_file:
        result = run_job_cli(args)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        if args.result_file:
            atomic_write_text(
                args.result_file,
                json.dumps(result, ensure_ascii=False, indent=2),
            )
        if result.get("status") == "success":
            return
        sys.exit(1)

    # 查看草稿箱并对比（找出未成功保存的）
    if args.list_drafts and args.batch_dir:
        run_list_drafts(args)
    # 批量模式
    elif args.batch_dir:
        run_batch_cli(args)
    # Episode 模式
    elif args.episode:
        run_episode_cli(args)
    # 传统命令行模式
    elif args.video:
        run_legacy_cli(args)
    else:
        # GUI 模式
        run_gui(args)


def run_gui(args):
    """启动 GUI 界面"""
    try:
        from .gui import launch_app
        print("🚀 正在启动火箭发射...")
        print(f"📍 访问地址: http://localhost:{args.port}")
        launch_app(share=args.share, server_port=args.port)
    except ImportError as e:
        print(f"❌ 启动失败: {e}")
        print("请确保已安装依赖: uv pip install -e .")
        sys.exit(1)


def run_job_subcommand(argv: list[str]) -> None:
    from copublisher.interfaces.cli.job_command import run_job_subcommand as _impl

    return _impl(argv)


def run_verify_cli(argv: list[str]) -> None:
    from copublisher.interfaces.cli.verify_command import run_verify_cli as _impl

    _impl(argv)


def scan_batch_dir(batch_dir: Path) -> list:
    from copublisher.interfaces.cli.workflows import scan_batch_dir as _impl

    return _impl(batch_dir)


def run_list_drafts(args):
    from copublisher.interfaces.cli.workflows import run_list_drafts as _impl

    return _impl(args, log_callback=_print_log)


def run_batch_cli(args):
    from copublisher.interfaces.cli.workflows import run_batch_cli as _impl

    return _impl(args, log_callback=_print_log)


def parse_platform_arg(platform_str: str) -> list:
    from copublisher.interfaces.cli.workflows import parse_platform_arg as _impl

    return _impl(platform_str)


def run_episode_cli(args):
    from copublisher.interfaces.cli.workflows import run_episode_cli as _impl

    return _impl(args, log_callback=_print_log)


def run_job_cli(args) -> dict[str, Any]:
    """Job-file compatibility adapter (delegates to layered use case)."""
    from copublisher.interfaces.cli.job_runner import run_job_file

    return run_job_file(job_file=args.job_file, dry_run=bool(args.dry_run))


def _print_log(message: str):
    """CLI 日志回调"""
    print(message)


# ============================================================
# 传统模式（兼容已有的 --video + --script 用法）
# ============================================================

def run_legacy_cli(args):
    from copublisher.interfaces.cli.workflows import run_legacy_cli as _impl

    return _impl(args, log_callback=_print_log)


if __name__ == "__main__":
    main()
