"""
微信公众号草稿发布模块

从 Markdown 文件创建公众号图文草稿。
流程：
1. Playwright 打开 mp.weixin.qq.com 并登录
2. 读取 MD 文件，用类 Doocs 内联样式渲染为 HTML
3. 把 styled HTML 写入浏览器剪贴板（通过 execCommand('copy')）
4. 聚焦 ProseMirror，粘贴富文本
5. 点击存草稿
"""

from __future__ import annotations

import re
import time
import logging
from pathlib import Path
from typing import Optional, Callable

from .browser import PlaywrightBrowser
from .gzh import authenticate_gzh

logger = logging.getLogger(__name__)

# ── 配色方案 ──────────────────────────────────────────────────────
BLUE = "#2B6CB0"
ORANGE = "#E8773A"
TEXT_COLOR = "#3f3f3f"
_T = "background: transparent;"
H_ICON = "📐 "

TAG_STYLES: dict[str, str] = {
    "h1": (
        f"{_T} font-size: 1.6em; font-weight: bold; text-align: center;"
        " color: #1a1a1a; margin: 32px 0 20px; letter-spacing: 0.06em;"
    ),
    "h2": (
        f"font-size: 1.25em; font-weight: bold; color: #fff;"
        f" text-align: center; margin: 36px 0 16px; letter-spacing: 0.06em;"
        f" padding: 8px 16px; background: {BLUE}; border-radius: 6px;"
    ),
    "h3": (
        f"{_T} font-size: 1.1em; font-weight: bold; color: {BLUE};"
        " text-align: center; margin: 24px 0 12px; letter-spacing: 0.05em;"
    ),
    "h4": (
        f"{_T} font-size: 1em; font-weight: bold; color: {BLUE};"
        " text-align: center; margin: 18px 0 10px;"
    ),
    "p": (
        f"{_T} font-size: 16px; line-height: 2; color: {TEXT_COLOR};"
        " margin: 12px 0; letter-spacing: 0.05em;"
    ),
    "blockquote": (
        f"{_T} border-left: 4px solid {BLUE}; margin: 20px 0;"
        " padding: 10px 16px; color: #666; font-size: 15px;"
        " line-height: 1.9; font-style: italic;"
    ),
    "ul": (
        f"{_T} margin: 12px 0 12px 20px; padding-left: 20px;"
        f" list-style-type: disc; color: {TEXT_COLOR}; font-size: 16px; line-height: 2;"
    ),
    "ol": (
        f"{_T} margin: 12px 0 12px 20px; padding-left: 20px;"
        f" list-style-type: decimal; color: {TEXT_COLOR}; font-size: 16px; line-height: 2;"
    ),
    "li": f"{_T} margin-bottom: 10px; font-size: 16px; line-height: 2; color: {TEXT_COLOR};",
    "code": f"color: {ORANGE}; font-family: Consolas, 'Courier New', monospace; font-size: 14px;",
    "pre": (
        "background: #1e293b; border-radius: 8px; padding: 16px; margin: 16px 0;"
        " overflow-x: auto; font-size: 14px; line-height: 1.6;"
    ),
    "table": f"{_T} width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 15px;",
    "th": (
        f"border: 1px solid #dfe2e5; padding: 8px 14px;"
        f" font-weight: bold; color: #fff; background: {BLUE}; text-align: left;"
    ),
    "td": f"{_T} border: 1px solid #dfe2e5; padding: 8px 14px; color: {TEXT_COLOR};",
    "strong": f"font-weight: bold; color: {ORANGE};",
    "em": "font-style: italic; color: #888;",
    "a": f"color: {BLUE}; text-decoration: none;",
    "hr": f"{_T} border: none; border-top: 1px dashed #c0c8d0; margin: 28px 0;",
    "img": "max-width: 100%; height: auto; display: block; margin: 20px auto; border-radius: 6px;",
}

PROFILE_CARD_RE = re.compile(r"<!--\s*公众号名片[：:]\s*(.+?)\s*-->")

CLIPBOARD_JS = """
(html) => {
    const div = document.createElement('div');
    div.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0;';
    div.innerHTML = html;
    document.body.appendChild(div);
    const range = document.createRange();
    range.selectNodeContents(div);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    const ok = document.execCommand('copy');
    sel.removeAllRanges();
    document.body.removeChild(div);
    return ok;
}
"""


def render_wechat_html(md_text: str) -> str:
    """把 Markdown 渲染成微信公众号兼容的内联样式 HTML。

    需要 ``markdown`` 和 ``beautifulsoup4`` 包（仅在调用时导入）。
    """
    import markdown as _md
    from bs4 import BeautifulSoup

    raw_html = _md.markdown(
        md_text,
        extensions=["extra", "tables", "fenced_code"],
    )
    soup = BeautifulSoup(raw_html, "html.parser")

    for tag, style in TAG_STYLES.items():
        for el in soup.find_all(tag):
            if tag == "code" and el.parent and el.parent.name == "pre":
                el["style"] = (
                    "color: #f8f8f2; font-family: Consolas, 'Courier New', monospace;"
                    " font-size: 14px;"
                )
            else:
                el["style"] = style

    for h in soup.find_all(["h2", "h3"]):
        h.insert(0, H_ICON)

    return str(soup)


def extract_profile_cards(md_text: str) -> tuple[str, list[str]]:
    """提取 ``<!-- 公众号名片：xxx -->`` 指令，替换为占位符。"""
    cards: list[str] = []

    def _repl(m: re.Match) -> str:
        name = m.group(1).strip()
        idx = len(cards)
        cards.append(name)
        return f"〔公众号名片占位{idx}〕"

    return PROFILE_CARD_RE.sub(_repl, md_text), cards


def parse_md_article(content: str, default_title: str = "") -> tuple[str, str]:
    """从 Markdown 全文提取标题（首行 #）和正文。用于目录批量与单篇发布统一解析。"""
    title = default_title
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        content = content.replace(m.group(0), "", 1).strip()
    return title, content


class GzhDraftPublisher:
    """微信公众号图文草稿发布器。

    浏览器管理委托给 ``PlaywrightBrowser``。
    account 用于区分多账号登录状态，对应认证目录 ~/.copublisher/{account}/。
    """

    BASE_URL = "https://mp.weixin.qq.com"

    def __init__(
        self,
        headless: bool = False,
        log_callback: Optional[Callable[[str], None]] = None,
        account: Optional[str] = None,
    ):
        self._log_fn = log_callback or (lambda msg, *_: print(msg))
        self.session = PlaywrightBrowser(
            "gzh_article", account, headless, self._log_fn,
        )

    def start(self):
        self.session.start()

    def close(self):
        self.session.close()

    @property
    def page(self):
        return self.session.page

    def authenticate(self, timeout: int = 120):
        if not self.page:
            self.start()
        authenticate_gzh(
            page=self.page,
            base_url=self.BASE_URL,
            log_fn=self._log_fn,
            save_fn=self.session.save_auth_state,
            timeout=timeout,
            has_stored_auth=self.session.has_stored_auth,
        )

    def _extract_token(self) -> str | None:
        url = self.page.url
        m = re.search(r"token=(\d+)", url)
        if m:
            return m.group(1)
        return self.page.evaluate(
            """() => {
                const links = document.querySelectorAll('a[href*="token="]');
                for (const a of links) {
                    const m = a.href.match(/token=(\\d+)/);
                    if (m) return m[1];
                }
                try {
                    if (window.wx?.commonData?.token)
                        return String(window.wx.commonData.token);
                } catch (_) {}
                return null;
            }"""
        )

    def _insert_profile_card(self, ep, account_name: str, placeholder: str) -> bool:
        """在占位符位置插入公众号名片。"""
        ep.locator('.ProseMirror[contenteditable="true"]').first.click()
        time.sleep(0.3)

        found = ep.evaluate(
            """(placeholder) => {
                const editor = document.querySelector('.ProseMirror[contenteditable="true"]');
                if (!editor) return false;
                const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
                let node;
                while ((node = walker.nextNode())) {
                    const idx = node.textContent.indexOf(placeholder);
                    if (idx !== -1) {
                        const range = document.createRange();
                        range.setStart(node, idx);
                        range.setEnd(node, idx + placeholder.length);
                        const sel = window.getSelection();
                        sel.removeAllRanges();
                        sel.addRange(range);
                        return true;
                    }
                }
                return false;
            }""",
            placeholder,
        )
        if not found:
            logger.warning("未找到占位符: %s", placeholder)
            return False

        ep.keyboard.press("Backspace")
        time.sleep(0.5)

        ep.evaluate(
            """() => {
                const item = document.getElementById('js_editor_insertProfile');
                if (!item) return;
                let el = item.parentElement;
                while (el && el !== document.body) {
                    if (el.classList.contains('tpl_dropdown')) {
                        el.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
                        el.classList.add('tpl_dropdown_show');
                        const menu = el.querySelector('.tpl_dropdown_menu');
                        if (menu) menu.style.display = 'block';
                        break;
                    }
                    el = el.parentElement;
                }
            }"""
        )
        time.sleep(0.5)

        try:
            ep.locator("#js_editor_insertProfile").click(timeout=2000)
        except Exception:
            ep.locator("#js_editor_insertProfile").click(force=True)
        time.sleep(1.5)

        search_input = ep.locator('input[placeholder*="账号名称"]').first
        search_input.wait_for(state="visible", timeout=5000)
        search_input.fill(account_name)
        time.sleep(0.3)

        ep.locator(".weui-desktop-search__btn").first.click()
        time.sleep(2)

        result = ep.locator(
            f'.wx_profile_nickname_wrp:has-text("{account_name}")'
        ).first
        result.wait_for(state="visible", timeout=5000)
        result.click()
        time.sleep(0.5)

        insert_btn = ep.locator(
            'button.weui-desktop-btn_primary:has-text("插入")'
        ).first
        insert_btn.wait_for(state="visible", timeout=3000)
        insert_btn.click()
        time.sleep(1.5)

        logger.info("公众号名片已插入: %s", account_name)
        return True

    def create_draft(self, title: str, markdown_content: str) -> bool:
        """创建一篇图文草稿。"""
        token = self._extract_token()
        if not token:
            logger.warning("token 未找到，尝试重载首页...")
            self.page.goto(
                f"{self.BASE_URL}/cgi-bin/home?t=home/index&lang=zh_CN",
                timeout=60000,
            )
            self.page.wait_for_load_state("domcontentloaded")
            token = self._extract_token()
        if not token:
            logger.error("无法获取 token，跳过此篇")
            return False

        draft_url = (
            f"{self.BASE_URL}/cgi-bin/appmsg"
            f"?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10"
            f"&createType=0&token={token}&lang=zh_CN"
        )

        with self.session.context.expect_page() as new_page_info:
            self.page.evaluate(f"window.open('{draft_url}', '_blank')")
        ep = new_page_info.value
        ep.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        try:
            title_el = ep.locator("textarea#title").first
            title_el.wait_for(state="visible", timeout=15000)
            title_el.click()
            time.sleep(0.2)
            ep.keyboard.press("Meta+A")
            ep.keyboard.type(title, delay=20)

            content_for_render, profile_cards = extract_profile_cards(markdown_content)
            styled_html = render_wechat_html(content_for_render)

            ep.evaluate(CLIPBOARD_JS, styled_html)

            editor_sel = '.ProseMirror[contenteditable="true"]'
            ep.wait_for_selector(editor_sel, timeout=15000)
            editor = ep.locator(editor_sel).first
            editor.click()
            time.sleep(0.5)
            ep.keyboard.press("Meta+A")
            ep.keyboard.press("Backspace")
            time.sleep(0.3)
            ep.keyboard.press("Meta+V")
            time.sleep(1.5)

            if profile_cards:
                for idx, name in enumerate(profile_cards):
                    placeholder = f"〔公众号名片占位{idx}〕"
                    self._insert_profile_card(ep, name, placeholder)

            time.sleep(1)
            saved = ep.evaluate(
                """() => {
                    for (const btn of document.querySelectorAll('button, a, span')) {
                        const txt = (btn.textContent || '').trim();
                        if (txt === '存草稿' || txt.includes('存草稿')) {
                            btn.click();
                            return btn.tagName + ':' + txt;
                        }
                    }
                    return null;
                }"""
            )
            if not saved:
                for sel in [
                    'button:text("存草稿")',
                    'button:has-text("草稿")',
                    ".js_save_draft",
                    "#js_save",
                ]:
                    try:
                        btn = ep.locator(sel).first
                        if btn.count() > 0 and btn.is_visible(timeout=1500):
                            btn.click()
                            saved = True
                            break
                    except Exception:
                        pass
                if not saved:
                    logger.warning("未找到存草稿按钮")

            time.sleep(3)
            return True

        except Exception as e:
            logger.error("创建草稿出错: %s", e)
            return False
        finally:
            ep.close()
            time.sleep(1)
