#!/usr/bin/env python3
"""
微信公众号草稿批量发布入口脚本。

核心逻辑已迁入 copublisher.core.gzh_drafts 模块，
本文件仅作为便捷 CLI 入口保留。

用法：
    python publish_gzh_drafts.py <content_dir> [--skip N]

若不传参数则使用默认目录（向后兼容）。
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from copublisher.core.gzh_drafts import GzhDraftPublisher


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        content_dir = Path(sys.argv[1])
    else:
        content_dir = Path(
            "/Users/xuejiao/Desktop/History/inspur/cowork/transcript/ppt_gen/content-series"
        )

    if not content_dir.exists():
        print(f"❌ 目录不存在: {content_dir}")
        return

    md_files = sorted(content_dir.glob("*.md"))
    if not md_files:
        print("❌ 没有找到 .md 文件")
        return

    skip = 0
    if "--skip" in sys.argv:
        idx = sys.argv.index("--skip")
        if idx + 1 < len(sys.argv):
            skip = int(sys.argv[idx + 1])

    files_to_run = md_files[skip:]
    total = len(files_to_run)
    print(f"找到 {len(md_files)} 个文件，跳过前 {skip} 篇，本次处理 {total} 篇\n")

    pub = GzhDraftPublisher(headless=False)
    try:
        pub.authenticate()
        for i, md_file in enumerate(files_to_run, 1):
            print(f"\n[{i}/{total}] {md_file.name}")
            content = md_file.read_text(encoding="utf-8")

            title = md_file.stem
            m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if m:
                title = m.group(1).strip()
                content = content.replace(m.group(0), "", 1).strip()

            pub.create_draft(title=title, markdown_content=content)

            if i < total:
                print("  等待 4 秒...")
                time.sleep(4)
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pub.close()


if __name__ == "__main__":
    main()
