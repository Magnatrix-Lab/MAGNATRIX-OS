#!/usr/bin/env python3
"""
MAGNATRIX-OS — Layer 7: Browser Automation Engine
Native Python, zero external dependencies.
Based on browser-use/browser-use + playwright patterns — AMATI-PELAJARI-TIRU.
"""
from __future__ import annotations
import json, time, hashlib, threading, re, random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum


class BrowserState(Enum):
    IDLE = "idle"
    NAVIGATING = "navigating"
    INTERACTING = "interacting"
    WAITING = "waiting"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class Element:
    tag: str
    selector: str
    text: str
    attributes: Dict[str, str] = field(default_factory=dict)
    bbox: Dict[str, int] = field(default_factory=dict)  # x, y, width, height
    clickable: bool = False
    visible: bool = True


@dataclass
class Session:
    id: str
    url: str
    title: str
    cookies: List[Dict] = field(default_factory=list)
    local_storage: Dict[str, str] = field(default_factory=dict)
    tabs: List[str] = field(default_factory=list)
    active_tab: int = 0
    created_at: float = field(default_factory=time.time)


class BrowserEngine:
    """Headless browser stub: launch, close, page create, viewport config."""

    def __init__(self, headless: bool = True, viewport: Dict = None):
        self.headless = headless
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self._running = False
        self._pages: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def launch(self) -> bool:
        self._running = True
        print(f"[Browser] Launched (headless={self.headless}, viewport={self.viewport})")
        return True

    def close(self):
        with self._lock:
            self._pages.clear()
        self._running = False
        print("[Browser] Closed")

    def new_page(self, url: str = "about:blank") -> str:
        with self._lock:
            page_id = f"page_{hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:6]}"
            self._pages[page_id] = {
                "url": url,
                "title": "",
                "content": "",
                "elements": [],
                "state": BrowserState.IDLE,
            }
            return page_id

    def close_page(self, page_id: str):
        with self._lock:
            self._pages.pop(page_id, None)

    def get_page(self, page_id: str) -> Optional[Dict]:
        with self._lock:
            return self._pages.get(page_id)

    def set_viewport(self, width: int, height: int):
        self.viewport = {"width": width, "height": height}


class DOMNavigator:
    """CSS selector, XPath, text match, element find/click/type/wait."""

    def __init__(self, engine: BrowserEngine):
        self.engine = engine

    def find_by_selector(self, page_id: str, selector: str) -> Optional[Element]:
        page = self.engine.get_page(page_id)
        if not page:
            return None
        for el in page.get("elements", []):
            if selector in el.selector or selector in el.attributes.get("class", ""):
                return el
        return None

    def find_by_text(self, page_id: str, text: str) -> Optional[Element]:
        page = self.engine.get_page(page_id)
        if not page:
            return None
        for el in page.get("elements", []):
            if text.lower() in el.text.lower():
                return el
        return None

    def find_all(self, page_id: str, tag: str = "") -> List[Element]:
        page = self.engine.get_page(page_id)
        if not page:
            return []
        if tag:
            return [el for el in page.get("elements", []) if el.tag == tag]
        return page.get("elements", [])

    def wait_for(self, page_id: str, selector: str, timeout: float = 10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self.find_by_selector(page_id, selector):
                return True
            time.sleep(0.5)
        return False


class ActionExecutor:
    """Click, type, scroll, screenshot, download, upload, hover, drag."""

    def __init__(self, engine: BrowserEngine, navigator: DOMNavigator):
        self.engine = engine
        self.navigator = navigator
        self._action_log: List[Dict] = []
        self._lock = threading.Lock()

    def click(self, page_id: str, selector: str) -> bool:
        el = self.navigator.find_by_selector(page_id, selector)
        if el and el.clickable:
            self._log("click", page_id, selector, True)
            return True
        self._log("click", page_id, selector, False)
        return False

    def type_text(self, page_id: str, selector: str, text: str) -> bool:
        el = self.navigator.find_by_selector(page_id, selector)
        if el:
            el.text = text
            self._log("type", page_id, selector, True, text=text)
            return True
        self._log("type", page_id, selector, False)
        return False

    def scroll(self, page_id: str, direction: str = "down", amount: int = 300) -> bool:
        self._log("scroll", page_id, direction, True, amount=amount)
        return True

    def screenshot(self, page_id: str, path: str = "screenshot.png") -> str:
        self._log("screenshot", page_id, path, True)
        return path

    def hover(self, page_id: str, selector: str) -> bool:
        self._log("hover", page_id, selector, True)
        return True

    def _log(self, action: str, page: str, target: str, success: bool, **kwargs):
        with self._lock:
            self._action_log.append({
                "action": action,
                "page": page,
                "target": target,
                "success": success,
                "timestamp": time.time(),
                **kwargs,
            })

    def get_log(self) -> List[Dict]:
        with self._lock:
            return self._action_log[:]


class SessionManager:
    """Session persistence, cookies, localStorage, multi-tab."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def create_session(self, url: str = "about:blank") -> Session:
        with self._lock:
            sid = f"sess_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
            session = Session(id=sid, url=url, title="")
            self._sessions[sid] = session
            return session

    def restore_session(self, sid: str, data: Dict) -> Optional[Session]:
        with self._lock:
            session = Session(
                id=sid,
                url=data.get("url", ""),
                title=data.get("title", ""),
                cookies=data.get("cookies", []),
                local_storage=data.get("local_storage", {}),
                tabs=data.get("tabs", []),
                active_tab=data.get("active_tab", 0),
            )
            self._sessions[sid] = session
            return session

    def export_session(self, sid: str) -> Dict:
        with self._lock:
            s = self._sessions.get(sid)
            if not s:
                return {}
            return {
                "url": s.url,
                "title": s.title,
                "cookies": s.cookies,
                "local_storage": s.local_storage,
                "tabs": s.tabs,
                "active_tab": s.active_tab,
            }

    def add_tab(self, sid: str, tab_url: str):
        with self._lock:
            s = self._sessions.get(sid)
            if s:
                s.tabs.append(tab_url)


class JavaScriptInjector:
    """Inject JS, evaluate expression, extract data, modify DOM."""

    def __init__(self, engine: BrowserEngine):
        self.engine = engine

    def evaluate(self, page_id: str, script: str) -> Any:
        page = self.engine.get_page(page_id)
        if not page:
            return None
        # Stub: simulate common JS patterns
        if "document.title" in script:
            return page.get("title", "")
        if "document.URL" in script:
            return page.get("url", "")
        if "JSON.stringify" in script:
            return json.dumps({"url": page.get("url"), "title": page.get("title")})
        return {"result": "stub", "script": script[:50]}

    def extract_data(self, page_id: str, selector: str, attribute: str = "textContent") -> List[str]:
        page = self.engine.get_page(page_id)
        if not page:
            return []
        results = []
        for el in page.get("elements", []):
            if selector in el.selector or selector in el.tag:
                if attribute == "textContent":
                    results.append(el.text)
                else:
                    results.append(el.attributes.get(attribute, ""))
        return results


class ScreenshotEngine:
    """Full page, element, viewport capture, diff comparison stub."""

    def capture_full(self, page_id: str, path: str = "full.png") -> str:
        return path

    def capture_element(self, page_id: str, selector: str, path: str = "element.png") -> str:
        return path

    def capture_viewport(self, page_id: str, path: str = "viewport.png") -> str:
        return path

    def compare(self, path1: str, path2: str) -> float:
        # Stub: random similarity score
        return random.uniform(0.8, 1.0)


class FormFiller:
    """Auto-detect form, field mapping, validation, submit."""

    def __init__(self, navigator: DOMNavigator, executor: ActionExecutor):
        self.navigator = navigator
        self.executor = executor

    def detect_form(self, page_id: str) -> List[Element]:
        return self.navigator.find_all(page_id, "input") + self.navigator.find_all(page_id, "textarea")

    def fill_form(self, page_id: str, data: Dict) -> Dict:
        results = {"filled": [], "failed": []}
        for key, value in data.items():
            selector = f"input[name='{key}'], input[id='{key}'], textarea[name='{key}']"
            el = self.navigator.find_by_selector(page_id, selector)
            if el:
                if self.executor.type_text(page_id, selector, str(value)):
                    results["filled"].append(key)
                else:
                    results["failed"].append(key)
            else:
                results["failed"].append(key)
        return results

    def submit(self, page_id: str, selector: str = "button[type='submit']") -> bool:
        return self.executor.click(page_id, selector)


class CaptchaHandlerStub:
    """Detect captcha, pause for human, log challenge type."""

    CAPTCHA_KEYWORDS = ["captcha", "recaptcha", "hcaptcha", "g-recaptcha", "cf-turnstile"]

    def detect(self, page_content: str) -> Optional[str]:
        for keyword in self.CAPTCHA_KEYWORDS:
            if keyword.lower() in page_content.lower():
                return keyword
        return None

    def handle(self, challenge_type: str) -> Dict:
        return {
            "status": "paused_for_human",
            "challenge": challenge_type,
            "message": f"Captcha {challenge_type} detected. Manual intervention required.",
        }


class StealthMode:
    """User-agent rotation, fingerprint randomization, bot detection evasion."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        self._current_ua = random.choice(self.USER_AGENTS)

    def rotate_ua(self) -> str:
        self._current_ua = random.choice(self.USER_AGENTS)
        return self._current_ua

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self._current_ua,
            "Accept-Language": random.choice(["en-US", "en-GB", "en-CA"]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def randomize_fingerprint(self) -> Dict:
        return {
            "screen_width": random.choice([1920, 1366, 1440, 2560]),
            "screen_height": random.choice([1080, 768, 900, 1440]),
            "color_depth": random.choice([24, 32]),
            "timezone": random.choice(["America/New_York", "Europe/London", "Asia/Tokyo"]),
        }


class CookieManager:
    """Cookie jar, import/export, domain isolation, expiry handling."""

    def __init__(self):
        self._cookies: Dict[str, List[Dict]] = {}
        self._lock = threading.Lock()

    def set_cookie(self, domain: str, name: str, value: str, expiry: float = None):
        with self._lock:
            self._cookies.setdefault(domain, [])
            self._cookies[domain].append({
                "name": name, "value": value,
                "expiry": expiry or time.time() + 86400,
            })

    def get_cookies(self, domain: str) -> List[Dict]:
        with self._lock:
            return [c for c in self._cookies.get(domain, []) if c["expiry"] > time.time()]

    def export_all(self) -> Dict:
        with self._lock:
            return dict(self._cookies)

    def import_cookies(self, data: Dict):
        with self._lock:
            for domain, cookies in data.items():
                self._cookies[domain] = cookies


class ProxyRotatorStub:
    """Proxy list, rotation per request, health check."""

    def __init__(self):
        self._proxies: List[str] = []
        self._current = 0
        self._lock = threading.Lock()

    def add_proxy(self, proxy: str):
        self._proxies.append(proxy)

    def get_next(self) -> Optional[str]:
        with self._lock:
            if not self._proxies:
                return None
            proxy = self._proxies[self._current]
            self._current = (self._current + 1) % len(self._proxies)
            return proxy

    def health_check(self, proxy: str) -> bool:
        # Stub: 90% healthy
        return random.random() < 0.9


class BrowserKernelBridge:
    """Bridge to event_bus and service_registry."""

    def __init__(self, event_bus=None, service_registry=None):
        self.event_bus = event_bus
        self.service_registry = service_registry

    def publish(self, event_type: str, data: Dict):
        if self.event_bus:
            try:
                self.event_bus.publish(f"browser.{event_type}", data)
            except Exception:
                pass

    def register(self):
        if self.service_registry:
            try:
                self.service_registry.register("browser_engine", {"status": "running"})
            except Exception:
                pass


class BrowserAgent:
    """Main orchestrator — compose all, run automation task."""

    def __init__(self, headless: bool = True):
        self.engine = BrowserEngine(headless=headless)
        self.navigator = DOMNavigator(self.engine)
        self.executor = ActionExecutor(self.engine, self.navigator)
        self.sessions = SessionManager()
        self.js = JavaScriptInjector(self.engine)
        self.screenshots = ScreenshotEngine()
        self.form_filler = FormFiller(self.navigator, self.executor)
        self.captcha = CaptchaHandlerStub()
        self.stealth = StealthMode()
        self.cookies = CookieManager()
        self.proxy = ProxyRotatorStub()
        self.bridge = BrowserKernelBridge()

    def boot(self):
        self.engine.launch()
        self.bridge.register()
        print("[BrowserAgent] Booted")

    def navigate(self, url: str) -> str:
        page_id = self.engine.new_page(url)
        page = self.engine.get_page(page_id)
        if page:
            page["url"] = url
            page["title"] = f"Page at {url}"
            # Simulate DOM elements
            page["elements"] = [
                Element("input", "#search", "", {"name": "q", "type": "text"}, clickable=True),
                Element("button", "#submit", "Search", {"type": "submit"}, clickable=True),
                Element("a", "#link1", "Click me", {"href": "/page2"}, clickable=True),
                Element("div", ".content", "Some content here"),
            ]
        self.bridge.publish("navigate", {"url": url, "page_id": page_id})
        return page_id

    def run_task(self, task: Dict) -> Dict:
        url = task.get("url", "about:blank")
        actions = task.get("actions", [])

        page_id = self.navigate(url)
        results = []

        for action in actions:
            atype = action.get("type")
            if atype == "click":
                r = self.executor.click(page_id, action.get("selector"))
            elif atype == "type":
                r = self.executor.type_text(page_id, action.get("selector"), action.get("text", ""))
            elif atype == "screenshot":
                r = self.screenshots.capture_full(page_id, action.get("path", "shot.png"))
            elif atype == "fill_form":
                r = self.form_filler.fill_form(page_id, action.get("data", {}))
            elif atype == "submit":
                r = self.form_filler.submit(page_id)
            else:
                r = False
            results.append({"action": atype, "result": r})

        return {"page_id": page_id, "results": results, "url": url}

    def shutdown(self):
        self.engine.close()
        print("[BrowserAgent] Shutdown")


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS Browser Automation Engine Demo")
    print("=" * 60)

    agent = BrowserAgent(headless=True)
    agent.boot()

    # Navigate and interact
    print("\n--- Navigate to example.com ---")
    page_id = agent.navigate("https://example.com")
    print(f"Page ID: {page_id}")

    page = agent.engine.get_page(page_id)
    if page:
        print(f"Title: {page['title']}")
        print(f"Elements: {len(page['elements'])}")

    # Click
    print("\n--- Click Elements ---")
    for el in page.get("elements", []):
        if el.clickable:
            result = agent.executor.click(page_id, el.selector)
            print(f"  Click {el.selector}: {'OK' if result else 'FAIL'}")

    # Fill form
    print("\n--- Fill Form ---")
    fill_result = agent.form_filler.fill_form(page_id, {"q": "MAGNATRIX browser test"})
    print(f"  Filled: {fill_result['filled']}")

    # Screenshot
    print("\n--- Screenshot ---")
    path = agent.screenshots.capture_full(page_id, "demo_browser.png")
    print(f"  Saved to: {path}")

    # Stealth
    print("\n--- Stealth Mode ---")
    print(f"  User-Agent: {agent.stealth.rotate_ua()[:50]}...")
    fp = agent.stealth.randomize_fingerprint()
    print(f"  Fingerprint: {fp}")

    # Session
    print("\n--- Session ---")
    session = agent.sessions.create_session("https://example.com")
    agent.sessions.add_tab(session.id, "https://example.com/page2")
    print(f"  Session: {session.id}, Tabs: {session.tabs}")

    agent.shutdown()
    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
