"""
CLI job subcommand implementation.
"""

from __future__ import annotations

import argparse
import json
import sys

from copublisher.application.services.blue_ocean_adapter import (
    build_job_payload_from_action,
    load_blue_ocean_request,
    map_run_result_to_org_state,
)
from copublisher.application.services.org_run_reporter import OrgRunReporter
from copublisher.interfaces.cli.job_runner import run_job_file, run_job_payload
from copublisher.shared.io import atomic_write_text


def run_job_subcommand(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="copublisher job")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="执行结构化 job")
    run_parser.add_argument("--job-file", type=str, default=None, help="job JSON 文件")
    run_parser.add_argument("--job-id", type=str, default=None, help="job id")
    run_parser.add_argument("--platform", type=str, default=None, help="单平台（兼容）")
    run_parser.add_argument("--platforms", type=str, default=None, help="多平台，逗号分隔")
    run_parser.add_argument("--video", type=str, default=None, help="视频路径")
    run_parser.add_argument("--script", type=str, default=None, help="脚本路径")
    run_parser.add_argument("--privacy", type=str, default="private", help="隐私设置")
    run_parser.add_argument("--account", type=str, default=None, help="账号标识")
    run_parser.add_argument("--trace-id", type=str, default=None, help="链路追踪 id")
    run_parser.add_argument("--org-run-id", type=str, default=None, help="组织运行 ID")
    run_parser.add_argument(
        "--report-root",
        type=str,
        default="reports/org-runs",
        help="组织运行报告根目录",
    )
    run_parser.add_argument(
        "--write-org-report",
        action="store_true",
        help="将执行结果写入 reports/org-runs/<id>/",
    )
    run_parser.add_argument(
        "--blue-ocean-input",
        type=str,
        default=None,
        help="blue-ocean action 输入 JSON",
    )
    run_parser.add_argument(
        "--org-state-json",
        action="store_true",
        help="输出 blue-ocean 组织状态映射",
    )
    run_parser.add_argument("--result-file", type=str, default=None, help="结果文件路径")
    run_parser.add_argument("--json", action="store_true", help="输出 JSON")
    run_parser.add_argument("--dry-run", action="store_true", help="只校验不执行")

    args = parser.parse_args(argv)
    if args.command != "run":
        parser.print_help()
        sys.exit(1)

    action_payload = None
    job_payload_for_report = None
    org_run_id = args.org_run_id

    if args.blue_ocean_input:
        action_payload = load_blue_ocean_request(args.blue_ocean_input)
        payload = build_job_payload_from_action(action_payload)
        job_payload_for_report = payload
        org_run_id = org_run_id or action_payload.get("action_id") or action_payload.get("job_id")
        result = run_job_payload(payload, dry_run=bool(args.dry_run))
    elif args.job_file:
        job_payload_for_report = {"job_file": args.job_file}
        result = run_job_file(args.job_file, dry_run=bool(args.dry_run))
    else:
        if not args.job_id or not args.video or not args.script:
            print("❌ 缺少必需参数：--job-id --video --script（或使用 --job-file）")
            sys.exit(1)
        platform_or_platforms = args.platforms or args.platform or "wechat"
        payload = {
            "job_id": args.job_id,
            "mode": "legacy",
            "platform": platform_or_platforms,
            "video": args.video,
            "script": args.script,
            "privacy": args.privacy,
            "account": args.account,
            "trace_id": args.trace_id,
        }
        job_payload_for_report = payload
        result = run_job_payload(payload, dry_run=bool(args.dry_run))

    org_state_payload = map_run_result_to_org_state(result)
    if args.write_org_report or bool(args.blue_ocean_input):
        if not org_run_id:
            print("❌ 缺少组织运行 ID（请传 --org-run-id 或 blue-ocean action_id）")
            sys.exit(1)
        reporter = OrgRunReporter(root_dir=args.report_root)
        reporter.write(
            org_run_id=org_run_id,
            action_payload=action_payload,
            job_payload=job_payload_for_report or {},
            run_result=result,
            org_state=org_state_payload,
        )

    output_payload = org_state_payload if args.org_state_json else result
    if args.json:
        print(json.dumps(output_payload, ensure_ascii=False))
    if args.result_file:
        atomic_write_text(
            args.result_file,
            json.dumps(output_payload, ensure_ascii=False, indent=2),
        )
    if result.get("status") != "success":
        sys.exit(1)

