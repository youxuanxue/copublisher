"""
验证 copublisher 模块安装和导入

用法:
    python verify_install.py
"""

import sys
from pathlib import Path

def main():
    print("="*60)
    print("验证 copublisher 模块")
    print("="*60)
    print()
    
    # 1. 检查 Python 版本
    print("1️⃣  检查 Python 版本...")
    python_version = sys.version_info
    print(f"   Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version < (3, 10):
        print("   ❌ 需要 Python 3.10 或更高版本")
        return False
    print("   ✅ Python 版本符合要求")
    print()
    
    # 2. 检查模块结构
    print("2️⃣  检查模块结构...")
    module_root = Path(__file__).parent / "src" / "copublisher"
    
    required_files = [
        "__init__.py",
        "__main__.py",
        "core/__init__.py",
        "core/base.py",
        "core/wechat.py",
        "core/youtube.py",
        "gui/__init__.py",
        "gui/app.py",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = module_root / file_path
        if full_path.exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} (不存在)")
            all_exist = False
    
    if not all_exist:
        print("\n   ❌ 模块结构不完整")
        return False
    print()
    
    # 3. 尝试导入核心模块
    print("3️⃣  导入核心模块...")
    try:
        sys.path.insert(0, str(module_root.parent))
        
        from copublisher import (
            Platform,
            Publisher,
            PublishTask,
            WeChatPublisher,
            YouTubePublisher,
            WeChatPublishTask,
            YouTubePublishTask,
        )
        print("   ✅ 成功导入所有核心类")
        
        # 显示版本信息
        from copublisher import __version__
        print(f"   📦 版本: {__version__}")
    except ImportError as e:
        print(f"   ❌ 导入失败: {e}")
        return False
    print()
    
    # 4. 检查依赖
    print("4️⃣  检查依赖...")
    dependencies = {
        "playwright": "playwright",
        "gradio": "gradio",
        "google.auth": "google-auth",
        "google_auth_oauthlib": "google-auth-oauthlib",
        "googleapiclient": "google-api-python-client",
    }
    
    missing_deps = []
    for module_name, package_name in dependencies.items():
        try:
            __import__(module_name)
            print(f"   ✅ {package_name}")
        except ImportError:
            print(f"   ⚠️  {package_name} (未安装)")
            missing_deps.append(package_name)
    
    if missing_deps:
        print(f"\n   ⚠️  缺少依赖: {', '.join(missing_deps)}")
        print("   运行以下命令安装:")
        print(f"   uv pip install {' '.join(missing_deps)}")
    print()
    
    # 5. 总结
    print("="*60)
    if not missing_deps:
        print("✅ 所有检查通过！copublisher 已准备就绪")
        print()
        print("下一步:")
        print("  • 使用 GUI: python -m copublisher")
        print("  • 命令行: python -m copublisher --video video.mp4 --script script.json")
        print("  • 查看示例: python examples/publish_lesson_example.py --help")
        return True
    else:
        print("⚠️  部分依赖缺失，请先安装依赖")
        print()
        print("安装方法:")
        print("  1. cd copublisher")
        print("  2. uv pip install -e .")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
