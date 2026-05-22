"""
MAGNATRIX — Browser Automation Layer
══════════════════════════════════════
Layer 7: Browser — agent-controlled web browsing, scraping, extraction.

Features:
- Playwright-based browser pool
- DOM extraction, screenshot, PDF generation
- Stealth mode (anti-bot detection)
- Cookie/session persistence
- Proxy rotation
- Form filling & submission
- JavaScript execution

Author: MAGNATRIX-OS
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class BrowserSession:
    session_id: str
    proxy: Optional[str] = None
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    headless: bool = True
    stealth: bool = True
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=__import__("time").time)

    @classmethod
    def default(cls) -> "BrowserSession":
        return cls(session_id=f"browser-{uuid.uuid4().hex[:12]}")


class BrowserPool:
    """Pool browser instances untuk reuse — efisien untuk multi-task scraping."""

    def __init__(self, max_sessions: int = 5, playwright_dir: Optional[str] = None):
        self.max_sessions = max_sessions
        self._sessions: Dict[str, Any] = {}  # session_id -> playwright objects
        self._config: Dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()
        self._available: asyncio.Queue = asyncio.Queue()
        self._playwright_dir = playwright_dir
        self._pw = None

    async def _ensure_pw(self):
        if self._pw is None:
            try:
                from playwright.async_api import async_playwright
                self._pw = await async_playwright().start()
            except ImportError:
                raise RuntimeError("playwright not installed: pip install playwright")

    async def create_session(self, config: Optional[BrowserSession] = None) -> str:
        await self._ensure_pw()
        cfg = config or BrowserSession.default()

        browser = await self._pw.chromium.launch(
            headless=cfg.headless,
            proxy={"server": cfg.proxy} if cfg.proxy else None,
            args=["--disable-blink-features=AutomationControlled"] if cfg.stealth else [],
        )
        context = await browser.new_context(
            user_agent=cfg.user_agent,
            viewport=cfg.viewport,
        )
        page = await context.new_page()

        if cfg.stealth:
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)

        if cfg.cookies:
            await context.add_cookies(cfg.cookies)

        sid = cfg.session_id
        async with self._lock:
            self._sessions[sid] = {"browser": browser, "context": context, "page": page}
            self._config[sid] = cfg

        await self._available.put(sid)
        return sid

    async def get_page(self, timeout: Optional[float] = None) -> Tuple[str, Any]:
        """Acquire session dari pool — blocking jika semua busy."""
        sid = await asyncio.wait_for(self._available.get(), timeout=timeout)
        page = self._sessions[sid]["page"]
        return sid, page

    async def release(self, sid: str) -> None:
        """Return session ke pool."""
        await self._available.put(sid)

    async def close_session(self, sid: str) -> None:
        async with self._lock:
            sess = self._sessions.pop(sid, None)
            self._config.pop(sid, None)
        if sess:
            await sess["context"].close()
            await sess["browser"].close()

    async def close_all(self) -> None:
        for sid in list(self._sessions.keys()):
            await self.close_session(sid)
        if self._pw:
            await self._pw.stop()
            self._pw = None


class BrowserLayer:
    """High-level browser layer untuk agent consumption."""

    def __init__(self, pool: Optional[BrowserPool] = None):
        self.pool = pool or BrowserPool()

    async def navigate(self, url: str, session_id: Optional[str] = None, wait_until: str = "networkidle") -> Dict[str, Any]:
        sid = session_id
        if not sid:
            sid = await self.pool.create_session()
        else:
            if sid not in self.pool._sessions:
                return {"success": False, "error": f"Session {sid} not found"}

        page = self.pool._sessions[sid]["page"]
        try:
            resp = await page.goto(url, wait_until=wait_until)
            title = await page.title()
            return {
                "success": True,
                "session_id": sid,
                "url": url,
                "title": title,
                "status": resp.status if resp else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    async def extract_text(self, selector: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid, page = await self._get_page(session_id)
        try:
            if selector:
                elements = await page.query_selector_all(selector)
                texts = []
                for el in elements:
                    text = await el.text_content()
                    if text:
                        texts.append(text.strip())
            else:
                texts = [await page.evaluate("() => document.body.innerText")]
            await self.pool.release(sid)
            return {"success": True, "texts": texts, "count": len(texts)}
        except Exception as e:
            await self.pool.release(sid)
            return {"success": False, "error": str(e)}

    async def extract_links(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid, page = await self._get_page(session_id)
        try:
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.innerText?.trim(),
                    href: a.href,
                    title: a.title
                }))
            """)
            await self.pool.release(sid)
            return {"success": True, "links": links, "count": len(links)}
        except Exception as e:
            await self.pool.release(sid)
            return {"success": False, "error": str(e)}

    async def screenshot(self, path: Optional[str] = None, full_page: bool = True, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid, page = await self._get_page(session_id)
        try:
            path = path or f"/tmp/magnatrix_screenshot_{uuid.uuid4().hex[:8]}.png"
            await page.screenshot(path=path, full_page=full_page)
            await self.pool.release(sid)
            return {"success": True, "path": path}
        except Exception as e:
            await self.pool.release(sid)
            return {"success": False, "error": str(e)}

    async def pdf(self, path: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid, page = await self._get_page(session_id)
        try:
            path = path or f"/tmp/magnatrix_page_{uuid.uuid4().hex[:8]}.pdf"
            await page.pdf(path=path, format="A4")
            await self.pool.release(sid)
            return {"success": True, "path": path}
        except Exception as e:
            await self.pool.release(sid)
            return {"success": False, "error": str(e)}

    async def fill_form(self, fields: Dict[str, str], session_id: Optional[str] = None) -> Dict[str, Any]:
        sid, page = await self._get_page(session_id)
        try:
            for selector, value in fields.items():
                await page.fill(selector, value)
            await self.pool.release(sid)
            return {"success": True, "fields_filled": len(fields)}
        except Exception as e:
            await self.pool.release(sid)
            return {"success": False, "error": str(e)}

    async def click(self, selector: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid, page = await self._get_page(session_id)
        try:
            await page.click(selector)
            await self.pool.release(sid)
            return {"success": True, "clicked": selector}
        except Exception as e:
            await self.pool.release(sid)
            return {"success": False, "error": str(e)}

    async def execute_js(self, script: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid, page = await self._get_page(session_id)
        try:
            result = await page.evaluate(script)
            await self.pool.release(sid)
            return {"success": True, "result": result}
        except Exception as e:
            await self.pool.release(sid)
            return {"success": False, "error": str(e)}

    async def get_cookies(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or list(self.pool._sessions.keys())[0]
        if sid not in self.pool._sessions:
            return {"success": False, "error": "No session"}
        context = self.pool._sessions[sid]["context"]
        cookies = await context.cookies()
        return {"success": True, "cookies": cookies}

    async def _get_page(self, sid: Optional[str]) -> Tuple[str, Any]:
        if sid and sid in self.pool._sessions:
            return sid, self.pool._sessions[sid]["page"]
        return await self.pool.get_page()

    async def healthcheck(self) -> bool:
        return True
