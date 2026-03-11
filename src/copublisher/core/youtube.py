"""
YouTube Shorts 发布核心模块

使用 YouTube Data API v3 自动化发布视频到 YouTube Shorts。
"""

import logging
import os
import socket
import time
from pathlib import Path
from typing import Optional, Callable, Tuple

import httplib2
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from copublisher.domain.tasks import YouTubePublishTask

from .base import Publisher
from copublisher.shared.io import atomic_write_text
from copublisher.shared.config import find_config_file

logger = logging.getLogger(__name__)

DEFAULT_PROXY_HOST = "127.0.0.1"
DEFAULT_PROXY_PORT = 7890

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
]
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

_UPLOAD_TIMEOUT = 1800  # 30 minutes


def _resolve_proxy_url() -> str:
    """Return the proxy URL for YouTube if USE_PROXY is enabled, else ''."""
    use_proxy = os.environ.get('USE_PROXY', 'true').lower() == 'true'
    if not use_proxy:
        return ""
    host = os.environ.get('PROXY_HOST', DEFAULT_PROXY_HOST)
    port = os.environ.get('PROXY_PORT', str(DEFAULT_PROXY_PORT))
    return f"http://{host}:{port}"


class RequestsHttpAdapter:
    """
    httplib2.Http-compatible adapter backed by ``requests.Session``.

    All proxy and timeout configuration is scoped to the session —
    no global ``os.environ`` or ``socket.setdefaulttimeout`` mutation.
    """

    def __init__(self, credentials=None, timeout: int = _UPLOAD_TIMEOUT, proxy_url: str = ""):
        self.credentials = credentials
        self.timeout = timeout
        self.session = requests.Session()

        if proxy_url:
            self.session.proxies = {'http': proxy_url, 'https': proxy_url}

    def request(self, uri, method="GET", body=None, headers=None,
                redirections=5, connection_type=None):
        if headers is None:
            headers = {}

        if self.credentials:
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            headers['Authorization'] = f'Bearer {self.credentials.token}'

        try:
            response = self.session.request(
                method=method,
                url=uri,
                data=body,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=(redirections > 0),
            )

            resp = httplib2.Response(response.headers)
            resp.status = response.status_code
            resp['status'] = str(response.status_code)
            return resp, response.content

        except requests.exceptions.Timeout as e:
            raise socket.timeout(str(e))
        except requests.exceptions.RequestException as e:
            raise socket.error(str(e))


class YouTubePublisher(Publisher):
    """
    YouTube Shorts 自动发布器
    
    使用 YouTube Data API v3 完成视频上传和发布。
    """
    
    def __init__(
        self, 
        credentials_path: str = "config/youtube_credentials.json", 
        token_path: str = "config/youtube_token.json",
        log_callback: Optional[Callable[[str], None]] = None
    ):
        super().__init__(log_callback)
        self.credentials_path = find_config_file(credentials_path)
        self.token_path = self.credentials_path.parent / Path(token_path).name
        self.credentials: Optional[Credentials] = None
        self.youtube = None

    def authenticate(self):
        """
        使用 OAuth2 进行 YouTube API 认证
        
        如果令牌存在且有效，则使用它。否则运行 OAuth 流程。
        """
        proxy_url = _resolve_proxy_url()
        creds = None
        
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
                self._log("从令牌文件加载现有凭据")
            except Exception as e:
                self._log(f"从令牌文件加载凭据失败: {e}", "WARNING")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self._log("正在刷新过期的凭据...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self._log(f"刷新凭据失败: {e}", "ERROR")
                    creds = None

            if not creds:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"凭据文件未找到: {self.credentials_path}\n"
                        "请从 Google Cloud Console 下载 OAuth2 凭据:\n"
                        "1. 访问 https://console.cloud.google.com/\n"
                        "2. 创建/选择项目\n"
                        "3. 启用 YouTube Data API v3\n"
                        "4. 创建 OAuth 2.0 凭据（桌面应用）\n"
                        "5. 重要: 添加授权重定向 URI: http://localhost:8080/\n"
                        "   (进入 OAuth 2.0 客户端 ID > 编辑 > 已授权的重定向 URI)\n"
                        "6. 下载并保存为 config/youtube_credentials.json"
                    )
                
                self._log("开始 OAuth2 授权流程...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES)
                try:
                    creds = flow.run_local_server(port=8080, open_browser=True)
                except OSError as e:
                    if "Address already in use" in str(e):
                        self._log("端口 8080 已被占用。尝试使用随机端口...", "WARNING")
                        self._log("注意: 如果遇到 redirect_uri_mismatch 错误，你需要:", "WARNING")
                        self._log("1. 查看授权 URL 中显示的端口号", "WARNING")
                        self._log("2. 在 Google Cloud Console 中添加 http://localhost:<port>/ 到授权重定向 URI", "WARNING")
                        creds = flow.run_local_server(port=0, open_browser=True)
                    else:
                        raise
                except Exception as e:
                    error_str = str(e)
                    if "redirect_uri_mismatch" in error_str.lower() or "400" in error_str:
                        raise RuntimeError(
                            "OAuth redirect_uri_mismatch 错误！\n"
                            "解决方法：\n"
                            "1. 访问 Google Cloud Console: https://console.cloud.google.com/\n"
                            "2. 进入 APIs & Services > Credentials\n"
                            "3. 点击你的 OAuth 2.0 客户端 ID\n"
                            "4. 在 '已授权的重定向 URI' 中添加: http://localhost:8080/\n"
                            "5. 保存更改后重新运行脚本\n"
                            f"\n原始错误: {error_str}"
                        ) from e
                    raise
                self._log("OAuth2 认证成功")

            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self.token_path, creds.to_json(), mode=0o600)
            self._log(f"凭据已保存到 {self.token_path}")

        self.credentials = creds
        
        if proxy_url:
            self._log(f"使用代理: {proxy_url} (通过 requests 库)")
        else:
            self._log("直连模式（未使用代理）")
        
        http_adapter = RequestsHttpAdapter(
            credentials=creds, timeout=_UPLOAD_TIMEOUT, proxy_url=proxy_url,
        )
        
        self.youtube = build(
            API_SERVICE_NAME, 
            API_VERSION, 
            http=http_adapter,
        )
        self._log("YouTube API 客户端初始化完成（上传超时: 30分钟）")

    def find_or_create_playlist(self, playlist_title: str) -> str:
        if not self.youtube:
            raise RuntimeError("未认证。请先调用 authenticate()")
        
        try:
            self._log(f"搜索播放列表: {playlist_title}")
            request = self.youtube.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50
            )
            response = request.execute()
            
            for item in response.get('items', []):
                if item['snippet']['title'] == playlist_title:
                    playlist_id = item['id']
                    self._log(f"找到现有播放列表: {playlist_title} (ID: {playlist_id})")
                    return playlist_id
            
            self._log(f"播放列表未找到。创建新播放列表: {playlist_title}")
            request = self.youtube.playlists().insert(
                part="snippet,status",
                body={
                    'snippet': {
                        'title': playlist_title,
                        'description': f'自动创建的播放列表: {playlist_title}',
                    },
                    'status': {
                        'privacyStatus': 'public'
                    }
                }
            )
            response = request.execute()
            playlist_id = response['id']
            self._log(f"创建新播放列表: {playlist_title} (ID: {playlist_id})")
            return playlist_id
            
        except HttpError as e:
            self._log(f"查找/创建播放列表失败: {e}", "ERROR")
            raise

    def add_video_to_playlist(self, video_id: str, playlist_id: str):
        if not self.youtube:
            raise RuntimeError("未认证。请先调用 authenticate()")
        
        try:
            self._log(f"将视频 {video_id} 添加到播放列表 {playlist_id}")
            request = self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': video_id
                        }
                    }
                }
            )
            request.execute()
            self._log("成功将视频添加到播放列表")
            
        except HttpError as e:
            self._log(f"添加视频到播放列表失败: {e}", "ERROR")
            raise

    def publish(self, task: YouTubePublishTask) -> Tuple[bool, Optional[str]]:
        try:
            task.validate()
        except Exception as e:
            self._log(f"任务验证失败: {e}", "ERROR")
            return False, None

        if not self.youtube:
            self._log("未认证。请先调用 authenticate()", "ERROR")
            return False, None

        try:
            self._log(f"正在上传视频: {task.video_path}")
            
            body = {
                'snippet': {
                    'title': task.title,
                    'description': task.description,
                    'tags': task.tags or [],
                    'categoryId': task.category_id,
                },
                'status': {
                    'privacyStatus': task.privacy_status,
                    'selfDeclaredMadeForKids': task.made_for_kids,
                }
            }

            media = MediaFileUpload(
                str(task.video_path),
                chunksize=2 * 1024 * 1024,
                resumable=True,
                mimetype='video/*'
            )

            insert_request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            error = None
            retry = 0
            last_progress = -1
            
            file_size_mb = os.path.getsize(task.video_path) / (1024 * 1024)
            self._log(f"开始上传 {file_size_mb:.1f} MB 文件...")
            
            while response is None:
                try:
                    status, response = insert_request.next_chunk()
                    
                    if status:
                        progress = int(status.progress() * 100)
                        if progress != last_progress:
                            uploaded_mb = file_size_mb * status.progress()
                            self._log(f"上传进度: {progress}% ({uploaded_mb:.1f}/{file_size_mb:.1f} MB)")
                            last_progress = progress
                    
                    if response is not None:
                        if 'id' in response:
                            video_id = response['id']
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                            self._log("视频上传成功！")
                            self._log(f"视频 ID: {video_id}")
                            self._log(f"视频 URL: {video_url}")
                            
                            if task.playlist_title:
                                try:
                                    playlist_id = self.find_or_create_playlist(task.playlist_title)
                                    self.add_video_to_playlist(video_id, playlist_id)
                                    self._log(f"已将视频添加到播放列表: {task.playlist_title}")
                                except Exception as e:
                                    self._log(f"添加视频到播放列表失败: {e}", "WARNING")
                            
                            return True, video_url
                        else:
                            error_msg = f"上传失败: {response}"
                            self._log(error_msg, "ERROR")
                            return False, None
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        error = f"可重试的 HTTP 错误 {e.resp.status}:\n{e.content}"
                        self._log(error, "WARNING")
                        retry += 1
                        if retry > 5:
                            error_msg = f"上传失败，已重试 {retry} 次: {error}"
                            self._log(error_msg, "ERROR")
                            return False, None
                        self._log(f"等待 5 秒后重试 (第 {retry} 次)...")
                        time.sleep(5)
                    else:
                        error_msg = f"HTTP 错误 {e.resp.status}:\n{e.content}"
                        self._log(error_msg, "ERROR")
                        return False, None
                except (socket.timeout, socket.error, TimeoutError, OSError) as e:
                    error = f"网络错误: {e}"
                    self._log(error, "WARNING")
                    retry += 1
                    
                    error_str = str(e).lower()
                    if "timed out" in error_str or "operation timed out" in error_str:
                        if retry == 1:
                            self._log("提示: 如果持续超时，请检查：", "WARNING")
                            self._log("   1. 是否需要开启 VPN/代理访问 YouTube", "WARNING")
                            self._log("   2. 检查网络连接是否稳定", "WARNING")
                            self._log("   3. 环境变量 HTTP_PROXY/HTTPS_PROXY 是否正确设置", "WARNING")
                    
                    if retry > 10:
                        error_msg = f"上传失败，已重试 {retry} 次: {error}"
                        self._log(error_msg, "ERROR")
                        self._log("建议：请确认 VPN/代理已开启并能访问 YouTube", "ERROR")
                        return False, None
                    
                    wait_time = min(5 * retry, 30)
                    self._log(f"等待 {wait_time} 秒后重试 (第 {retry}/10 次)...")
                    time.sleep(wait_time)

        except HttpError as e:
            error_msg = f"HTTP 错误 {e.resp.status}:\n{e.content}"
            self._log(error_msg, "ERROR")
            return False, None
        except Exception as e:
            error_msg = f"上传过程中出错: {e}"
            self._log(error_msg, "ERROR")
            return False, None

    def __enter__(self):
        self.authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
