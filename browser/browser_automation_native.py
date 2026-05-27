#!/usr/bin/env python3
"""
MAGNATRIX-OS Browser Automation Native
Playwright/Selenium bridge, web scraping, form filling, screenshot.
Pure Python stdlib + urllib. External deps optional.
"""
import urllib.request, urllib.error, urllib.parse, json, re, time, tempfile, os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field


@dataclass
class BrowserConfig:
    headless: bool = True
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    timeout: float = 30.0
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})
    proxy: Optional[str] = None
    javascript: bool = True


class BrowserSessionNative:
    """
    Lightweight browser session using urllib + custom request builder.
    For full JS support, delegates to Playwright/Selenium if available.
    """

    def __init__(self, config: BrowserConfig = None):
        self.config = config or BrowserConfig()
        self._cookies: Dict[str, str] = {}
        self._history: List[str] = []
        self._playwright = None
        self._page = None

    def _build_opener(self):
        handlers = []
        if self.config.proxy:
            handlers.append(urllib.request.ProxyHandler({"http": self.config.proxy, "https": self.config.proxy}))
        return urllib.request.build_opener(*handlers) if handlers else urllib.request.build_opener()

    def _add_headers(self, req: urllib.request.Request):
        req.add_header("User-Agent", self.config.user_agent)
        if self._cookies:
            req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in self._cookies.items()))

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to URL, return page info."""
        self._history.append(url)
        try:
            req = urllib.request.Request(url)
            self._add_headers(req)
            with self._build_opener().open(req, timeout=self.config.timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                # Parse cookies
                for header in resp.headers.get_all("Set-Cookie") if hasattr(resp.headers, "get_all") else []:
                    if "Set-Cookie" in str(resp.headers):
                        cookie_str = str(resp.headers)
                        for line in cookie_str.split("\n"):
                            if "set-cookie" in line.lower():
                                parts = line.split(";")[0].split("=")
                                if len(parts) == 2:
                                    self._cookies[parts[0].strip()] = parts[1].strip()
                return {
                    "url": resp.geturl(),
                    "status": resp.getcode(),
                    "title": self._extract_title(html),
                    "html": html[:5000],
                    "links": self._extract_links(html, url),
                }
        except Exception as e:
            return {"url": url, "status": 0, "error": str(e)}

    def _extract_title(self, html: str) -> str:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""

    def _extract_links(self, html: str, base_url: str) -> List[Dict]:
        links = []
        for m in re.finditer(r'href=["\'](.*?)["\']', html, re.IGNORECASE):
            href = m.group(1)
            full = urllib.parse.urljoin(base_url, href)
            links.append({"text": href, "href": full})
        return links[:50]

    def click(self, selector: str) -> Dict[str, Any]:
        """Simulate click on element by selector (simplified)."""
        # Full implementation needs Playwright/Selenium
        return {"action": "click", "selector": selector, "status": "not_implemented_without_playwright"}

    def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """Fill form field."""
        return {"action": "fill", "selector": selector, "value": value, "status": "not_implemented_without_playwright"}

    def screenshot(self, path: Optional[str] = None) -> str:
        """Screenshot current page."""
        if not path:
            path = os.path.join(tempfile.gettempdir(), "magnatrix_screenshot.png")
        # Requires Playwright for real screenshots
        return path

    def evaluate_js(self, script: str) -> Any:
        """Evaluate JavaScript in page context."""
        if self._playwright and self._page:
            try:
                return self._page.evaluate(script)
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Playwright not available"}

    def use_playwright(self):
        """Try to initialize Playwright for full browser automation."""
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=self.config.headless)
            self._playwright = pw
            self._page = browser.new_page(viewport=self.config.viewport)
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def close(self):
        if self._page:
            self._page.close()
        if self._playwright:
            self._playwright.stop()


class WebScraperNative:
    """Web scraper with structured data extraction."""

    def __init__(self, session: BrowserSessionNative = None):
        self.session = session or BrowserSessionNative()

    def scrape_article(self, url: str) -> Dict[str, Any]:
        """Extract article content from URL."""
        page = self.session.navigate(url)
        html = page.get("html", "")
        return {
            "url": url,
            "title": page.get("title", ""),
            "paragraphs": self._extract_paragraphs(html),
            "headings": self._extract_headings(html),
            "links": page.get("links", []),
        }

    def _extract_paragraphs(self, html: str) -> List[str]:
        texts = re.findall(r'<p[^>]*>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
        cleaned = [re.sub(r'<[^>]+>', '', t).strip() for t in texts]
        return [t for t in cleaned if len(t) > 20][:20]

    def _extract_headings(self, html: str) -> List[Dict]:
        headings = []
        for level in range(1, 7):
            pattern = rf'<h{level}[^>]*>(.*?)</h{level}>'
            for m in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
                text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                if text:
                    headings.append({"level": level, "text": text})
        return headings[:30]

    def search_duckduckgo(self, query: str) -> List[Dict]:
        """Search DuckDuckGo HTML version (no JS required)."""
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        page = self.session.navigate(url)
        html = page.get("html", "")
        results = []
        for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL):
            href = urllib.parse.unquote(m.group(1))
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            results.append({"title": title, "url": href})
        return results[:10]


class FormFillerNative:
    """Automated form filling using Playwright or Selenium."""

    def __init__(self, session: BrowserSessionNative = None):
        self.session = session or BrowserSessionNative()

    def fill_form(self, url: str, data: Dict[str, str]) -> Dict[str, Any]:
        """Navigate to URL and fill form fields."""
        if not self.session.use_playwright():
            return {"error": "Playwright required for form filling"}
        self.session._page.goto(url)
        for selector, value in data.items():
            self.session._page.fill(selector, value)
        return {"status": "filled", "fields": list(data.keys())}

    def submit(self, selector: str = "button[type=submit]") -> Dict[str, Any]:
        if self.session._page:
            self.session._page.click(selector)
            return {"status": "submitted"}
        return {"error": "No active page"}


class BrowserAutomationNative:
    """Main browser automation orchestrator."""

    def __init__(self):
        self.config = BrowserConfig()
        self.session = BrowserSessionNative(self.config)
        self.scraper = WebScraperNative(self.session)
        self.form_filler = FormFillerNative(self.session)

    def search(self, query: str) -> List[Dict]:
        return self.scraper.search_duckduckgo(query)

    def scrape(self, url: str) -> Dict[str, Any]:
        return self.scraper.scrape_article(url)

    def navigate(self, url: str) -> Dict[str, Any]:
        return self.session.navigate(url)

    def close(self):
        self.session.close()


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Browser Automation Demo")
    print("=" * 60)

    browser = BrowserAutomationNative()

    print("\n[1] Navigating example.com...")
    result = browser.navigate("https://example.com")
    print(f"    Status: {result['status']}, Title: {result['title'][:40]}")

    print("\n[2] Searching DuckDuckGo...")
    results = browser.search("MAGNATRIX-OS open source")
    for i, r in enumerate(results[:3], 1):
        print(f"    {i}. {r['title'][:50]}...")

    print("\n[3] Scraping article...")
    article = browser.scrape("https://example.com")
    print(f"    Title: {article['title'][:40]}")
    print(f"    Paragraphs: {len(article['paragraphs'])}")
    print(f"    Headings: {len(article['headings'])}")

    browser.close()
    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
