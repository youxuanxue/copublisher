"""
课程视频发布示例

演示如何使用 copublisher 模块发布课程视频到多个平台。
需先安装: uv pip install -e .

用法:
    python examples/publish_lesson_example.py book_sunzibingfa/lesson02 --platform both
"""

import argparse
import json
import sys
from pathlib import Path

from copublisher import (
    WeChatPublisher,
    YouTubePublisher,
    WeChatPublishTask,
    YouTubePublishTask,
)


def main():
    parser = argparse.ArgumentParser(description="发布课程视频到多个平台")
    parser.add_argument(
        "lesson_path",
        help="课程路径 (例如: book_sunzibingfa/lesson02)"
    )
    parser.add_argument(
        "--platform",
        choices=["wechat", "youtube", "both"],
        default="both",
        help="发布平台 (默认: both)"
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default="private",
        help="YouTube 隐私设置 (默认: private)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    args = parser.parse_args()

    # 解析课程路径
    lesson_path_str = args.lesson_path.strip()
    parts = lesson_path_str.split('/')
    
    if len(parts) != 2:
        print(f"❌ 无效的课程路径格式。期望: book_sunzibingfa/lesson02, 实际: {lesson_path_str}")
        return 1
    
    series_name, lesson_dir_name = parts
    
    # 构建路径（假设从项目根目录运行）
    project_root = Path(__file__).resolve().parent.parent.parent
    lesson_source_dir = project_root / "series" / series_name / lesson_dir_name
    
    if not lesson_source_dir.exists():
        print(f"❌ 课程目录不存在: {lesson_source_dir}")
        return 1

    # 查找视频文件
    lesson_media_dir = lesson_source_dir / "media"
    if not lesson_media_dir.exists():
        print(f"❌ 媒体目录不存在: {lesson_media_dir}")
        return 1

    video_dir = lesson_media_dir / "videos/animate/1920p60"
    video_path = None
    
    if video_dir.exists():
        video_files = list(video_dir.glob("*Vertical.mp4"))
        if not video_files:
            video_files = list(video_dir.glob("*.mp4"))
        
        if video_files:
            video_path = video_files[0]
            print(f"📹 找到视频: {video_path.name}")
    
    if not video_path:
        print(f"❌ 未找到视频文件")
        return 1

    # 读取脚本文件
    script_json_path = lesson_source_dir / "script.json"
    if not script_json_path.exists():
        print(f"❌ 脚本文件不存在: {script_json_path}")
        return 1
    
    try:
        with open(script_json_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
        print(f"📄 已加载脚本文件")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式错误: {e}")
        return 1

    # 发布到微信
    if args.platform in ["wechat", "both"]:
        success = publish_to_wechat(video_path, script_data, args.debug)
        if not success and args.platform == "wechat":
            return 1

    # 发布到YouTube
    if args.platform in ["youtube", "both"]:
        success = publish_to_youtube(video_path, script_data, args.privacy)
        if not success and args.platform == "youtube":
            return 1

    return 0


def publish_to_wechat(video_path: Path, script_data: dict, debug: bool = False) -> bool:
    """发布到微信视频号"""
    print("\n" + "="*60)
    print("📱 发布到微信视频号")
    print("="*60)
    
    try:
        # 创建发布任务
        task = WeChatPublishTask.from_json(video_path, script_data)
        
        print(f"📝 标题: {task.title or '(未设置)'}")
        print(f"📦 合集: {task.heji or '(未设置)'}")
        print(f"🎯 活动: {task.huodong or '(未设置)'}")
        print()
        
        # 执行发布
        with WeChatPublisher(headless=False, debug=debug) as publisher:
            publisher.authenticate()
            success, message = publisher.publish(task)
            
            if success:
                print("\n✅ 微信视频号发布准备完成！")
                print("💡 请在浏览器中确认信息并点击发布按钮")
                try:
                    input("按回车键继续...")
                except EOFError:
                    import time
                    print("检测到非交互式环境，等待 5 分钟...")
                    time.sleep(300)
                return True
            else:
                print(f"\n❌ 发布失败: {message}")
                return False
                
    except KeyboardInterrupt:
        print("\n⚠️  用户取消操作")
        return False
    except Exception as e:
        print(f"\n❌ 发布失败: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return False


def publish_to_youtube(video_path: Path, script_data: dict, privacy: str = "private") -> bool:
    """发布到YouTube"""
    print("\n" + "="*60)
    print("📺 发布到 YouTube Shorts")
    print("="*60)
    
    try:
        # 创建发布任务
        task = YouTubePublishTask.from_json(video_path, script_data)
        task.privacy_status = privacy
        
        print(f"📝 标题: {task.title}")
        print(f"🔒 隐私: {task.privacy_status}")
        if task.playlist_title:
            print(f"📋 播放列表: {task.playlist_title}")
        print()
        
        # 执行发布
        with YouTubePublisher() as publisher:
            success, video_url = publisher.publish(task)
            
            if success:
                print(f"\n✅ YouTube Shorts 上传成功！")
                print(f"🔗 视频链接: {video_url}")
                print(f"🎬 YouTube Studio: https://studio.youtube.com/")
                return True
            else:
                print(f"\n❌ 上传失败")
                return False
                
    except FileNotFoundError as e:
        print(f"\n❌ YouTube 认证文件未找到")
        print("\n请按照以下步骤设置 YouTube API：")
        print("1. 访问 https://console.cloud.google.com/")
        print("2. 创建或选择项目")
        print("3. 启用 YouTube Data API v3")
        print("4. 创建 OAuth 2.0 凭据（桌面应用）")
        print("5. ⚠️  重要：添加授权重定向 URI: http://localhost:8080/")
        print("6. 下载并保存为: config/youtube_credentials.json")
        return False
    except Exception as e:
        error_msg = str(e)
        if "redirect_uri_mismatch" in error_msg.lower():
            print("\n❌ OAuth 重定向 URI 不匹配")
            print("请在 Google Cloud Console 中添加: http://localhost:8080/")
        else:
            print(f"\n❌ 发布失败: {e}")
        return False


if __name__ == "__main__":
    sys.exit(main())
