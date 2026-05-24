#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Integration Hub (Layer 1.5 Extension)
Inspired by: itseffi/agentic-os System/integrations/
External tool connectors: Slack, Linear, Google Calendar, Jira, Confluence,
Granola, GitHub, Notion, Discord, Telegram.
================================================================================
Zero-dependency integration stubs with webhook-style event reception
and REST API wrappers (using urllib only).
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================
DEFAULT_TIMEOUT = 15.0


# =============================================================================
# Data Types
# =============================================================================
class IntegrationStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class IntegrationEvent:
    source: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    raw: str = ""


@dataclass
class APICall:
    method: str
    endpoint: str
    params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class APIResponse:
    status: int
    body: str
    headers: Dict[str, str] = field(default_factory=dict)
    latency_ms: float = 0.0


# =============================================================================
# Base Connector
# =============================================================================
class BaseConnector(ABC):
    def __init__(self, name: str, base_url: str, api_key: str = "", token: str = "") -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = token
        self.status = IntegrationStatus.DISCONNECTED
        self._webhook_handlers: List[Callable[[IntegrationEvent], None]] = []
        self._lock = threading.Lock()

    def _request(self, call: APICall) -> APIResponse:
        t0 = time.perf_counter()
        url = f"{self.base_url}{call.endpoint}"
        if call.params:
            url += "?" + urllib.parse.urlencode(call.params)
        headers = {"Content-Type": "application/json", **call.headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        try:
            data = call.body.encode("utf-8") if call.body else None
            req = urllib.request.Request(url, data=data, headers=headers, method=call.method)
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
                return APIResponse(
                    status=resp.status,
                    body=body,
                    headers=dict(resp.headers),
                    latency_ms=(time.perf_counter() - t0) * 1000,
                )
        except urllib.error.HTTPError as e:
            return APIResponse(status=e.code, body=e.read().decode("utf-8", errors="replace"), latency_ms=(time.perf_counter() - t0) * 1000)
        except Exception as exc:
            return APIResponse(status=0, body=str(exc), latency_ms=(time.perf_counter() - t0) * 1000)

    def on_webhook(self, handler: Callable[[IntegrationEvent], None]) -> None:
        self._webhook_handlers.append(handler)

    def emit(self, event: IntegrationEvent) -> None:
        for h in self._webhook_handlers:
            h(event)

    @abstractmethod
    def health_check(self) -> IntegrationStatus: ...


# =============================================================================
# Slack Connector
# =============================================================================
class SlackConnector(BaseConnector):
    def __init__(self, token: str = "") -> None:
        super().__init__("slack", "https://slack.com/api", token=token)

    def health_check(self) -> IntegrationStatus:
        r = self._request(APICall("GET", "/auth.test"))
        if r.status == 200:
            try:
                d = json.loads(r.body)
                self.status = IntegrationStatus.CONNECTED if d.get("ok") else IntegrationStatus.ERROR
            except Exception:
                self.status = IntegrationStatus.ERROR
        elif r.status == 429:
            self.status = IntegrationStatus.RATE_LIMITED
        else:
            self.status = IntegrationStatus.ERROR
        return self.status

    def post_message(self, channel: str, text: str) -> APIResponse:
        return self._request(APICall(
            "POST", "/chat.postMessage",
            body=json.dumps({"channel": channel, "text": text}),
        ))

    def list_channels(self) -> APIResponse:
        return self._request(APICall("GET", "/conversations.list"))


# =============================================================================
# Linear Connector
# =============================================================================
class LinearConnector(BaseConnector):
    def __init__(self, token: str = "") -> None:
        super().__init__("linear", "https://api.linear.app/graphql", token=token)

    def health_check(self) -> IntegrationStatus:
        r = self._request(APICall("POST", "", body=json.dumps({"query": "{ viewer { id } }"})))
        self.status = IntegrationStatus.CONNECTED if r.status == 200 else IntegrationStatus.ERROR
        return self.status

    def create_issue(self, title: str, team_id: str, description: str = "") -> APIResponse:
        query = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) { success issue { id title } }
        }
        """
        variables = {"input": {"title": title, "teamId": team_id, "description": description}}
        return self._request(APICall("POST", "", body=json.dumps({"query": query, "variables": variables})))

    def list_issues(self, team_id: str) -> APIResponse:
        query = """
        query Issues($filter: IssueFilter) { issues(filter: $filter) { nodes { id title state { name } } } }
        """
        variables = {"filter": {"team": {"id": {"eq": team_id}}}}
        return self._request(APICall("POST", "", body=json.dumps({"query": query, "variables": variables})))


# =============================================================================
# Google Calendar Connector
# =============================================================================
class GoogleCalendarConnector(BaseConnector):
    def __init__(self, api_key: str = "") -> None:
        super().__init__("google_calendar", "https://www.googleapis.com/calendar/v3", api_key=api_key)

    def health_check(self) -> IntegrationStatus:
        r = self._request(APICall("GET", "/users/me/calendarList"))
        self.status = IntegrationStatus.CONNECTED if r.status == 200 else IntegrationStatus.ERROR
        return self.status

    def list_events(self, calendar_id: str = "primary", time_min: str = "", time_max: str = "") -> APIResponse:
        params: Dict[str, str] = {}
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        return self._request(APICall("GET", f"/calendars/{calendar_id}/events", params=params))

    def create_event(self, calendar_id: str, summary: str, start: str, end: str) -> APIResponse:
        body = json.dumps({"summary": summary, "start": {"dateTime": start}, "end": {"dateTime": end}})
        return self._request(APICall("POST", f"/calendars/{calendar_id}/events", body=body))


# =============================================================================
# Jira Connector
# =============================================================================
class JiraConnector(BaseConnector):
    def __init__(self, base_url: str, user: str = "", token: str = "") -> None:
        super().__init__("jira", base_url, api_key=token)
        self.user = user

    def health_check(self) -> IntegrationStatus:
        r = self._request(APICall("GET", "/rest/api/2/myself"))
        self.status = IntegrationStatus.CONNECTED if r.status == 200 else IntegrationStatus.ERROR
        return self.status

    def create_issue(self, project_key: str, summary: str, issue_type: str = "Task") -> APIResponse:
        body = json.dumps({"fields": {"project": {"key": project_key}, "summary": summary, "issuetype": {"name": issue_type}}})
        return self._request(APICall("POST", "/rest/api/2/issue", body=body))

    def list_issues(self, project_key: str) -> APIResponse:
        jql = urllib.parse.quote(f"project={project_key}")
        return self._request(APICall("GET", f"/rest/api/2/search?jql={jql}"))


# =============================================================================
# GitHub Connector
# =============================================================================
class GitHubConnector(BaseConnector):
    def __init__(self, token: str = "") -> None:
        super().__init__("github", "https://api.github.com", token=token)

    def health_check(self) -> IntegrationStatus:
        r = self._request(APICall("GET", "/user"))
        self.status = IntegrationStatus.CONNECTED if r.status == 200 else IntegrationStatus.ERROR
        return self.status

    def list_repos(self, org: str = "") -> APIResponse:
        endpoint = f"/orgs/{org}/repos" if org else "/user/repos"
        return self._request(APICall("GET", endpoint))

    def create_issue(self, owner: str, repo: str, title: str, body: str = "") -> APIResponse:
        return self._request(APICall(
            "POST", f"/repos/{owner}/{repo}/issues",
            body=json.dumps({"title": title, "body": body}),
        ))

    def get_repo(self, owner: str, repo: str) -> APIResponse:
        return self._request(APICall("GET", f"/repos/{owner}/{repo}"))


# =============================================================================
# Notion Connector
# =============================================================================
class NotionConnector(BaseConnector):
    def __init__(self, token: str = "") -> None:
        super().__init__("notion", "https://api.notion.com/v1", token=token)
        self._default_headers = {"Notion-Version": "2022-06-28"}

    def health_check(self) -> IntegrationStatus:
        r = self._request(APICall("GET", "/users", headers=self._default_headers))
        self.status = IntegrationStatus.CONNECTED if r.status == 200 else IntegrationStatus.ERROR
        return self.status

    def list_databases(self) -> APIResponse:
        return self._request(APICall("GET", "/databases", headers=self._default_headers))

    def query_database(self, database_id: str, filter_json: Optional[Dict[str, Any]] = None) -> APIResponse:
        body = json.dumps({"filter": filter_json} if filter_json else {})
        return self._request(APICall("POST", f"/databases/{database_id}/query", body=body, headers=self._default_headers))


# =============================================================================
# Discord Connector
# =============================================================================
class DiscordConnector(BaseConnector):
    def __init__(self, token: str = "") -> None:
        super().__init__("discord", "https://discord.com/api/v10", token=token)

    def health_check(self) -> IntegrationStatus:
        r = self._request(APICall("GET", "/users/@me"))
        self.status = IntegrationStatus.CONNECTED if r.status == 200 else IntegrationStatus.ERROR
        return self.status

    def send_message(self, channel_id: str, content: str) -> APIResponse:
        return self._request(APICall(
            "POST", f"/channels/{channel_id}/messages",
            body=json.dumps({"content": content}),
        ))


# =============================================================================
# Telegram Connector
# =============================================================================
class TelegramConnector(BaseConnector):
    def __init__(self, bot_token: str = "") -> None:
        super().__init__("telegram", f"https://api.telegram.org/bot{bot_token}", token=bot_token)

    def health_check(self) -> IntegrationStatus:
        r = self._request(APICall("GET", "/getMe"))
        self.status = IntegrationStatus.CONNECTED if r.status == 200 else IntegrationStatus.ERROR
        return self.status

    def send_message(self, chat_id: str, text: str) -> APIResponse:
        return self._request(APICall(
            "POST", "/sendMessage",
            body=json.dumps({"chat_id": chat_id, "text": text}),
        ))


# =============================================================================
# Integration Hub
# =============================================================================
class IntegrationHub:
    """Central registry and router for all external integrations."""

    def __init__(self) -> None:
        self._connectors: Dict[str, BaseConnector] = {}
        self._lock = threading.Lock()
        self._event_handlers: List[Callable[[IntegrationEvent], None]] = []

    def register(self, connector: BaseConnector) -> None:
        with self._lock:
            self._connectors[connector.name] = connector
        connector.on_webhook(self._route_event)

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._connectors.pop(name, None) is not None

    def get(self, name: str) -> Optional[BaseConnector]:
        return self._connectors.get(name)

    def list_all(self) -> List[BaseConnector]:
        with self._lock:
            return list(self._connectors.values())

    def health_check_all(self) -> Dict[str, IntegrationStatus]:
        return {name: conn.health_check() for name, conn in self._connectors.items()}

    def on_event(self, handler: Callable[[IntegrationEvent], None]) -> None:
        self._event_handlers.append(handler)

    def _route_event(self, event: IntegrationEvent) -> None:
        for h in self._event_handlers:
            h(event)

    def broadcast(self, connector_names: List[str], message: str) -> Dict[str, APIResponse]:
        results = {}
        for name in connector_names:
            conn = self._connectors.get(name)
            if isinstance(conn, SlackConnector):
                results[name] = conn.post_message("#general", message)
            elif isinstance(conn, DiscordConnector):
                # Need channel_id from config
                results[name] = APIResponse(status=0, body="No channel configured")
            elif isinstance(conn, TelegramConnector):
                results[name] = conn.send_message("@channel", message)
            else:
                results[name] = APIResponse(status=0, body="Broadcast not supported")
        return results


# =============================================================================
# Integration Kernel Bridge
# =============================================================================
class IntegrationKernelBridge:
    def __init__(self, hub: IntegrationHub, event_bus: Any = None) -> None:
        self.hub = hub
        self.bus = event_bus
        hub.on_event(self._on_event)

    def _on_event(self, event: IntegrationEvent) -> None:
        if self.bus:
            self.bus.publish(f"integration.{event.source}", {
                "type": event.event_type,
                "payload": event.payload,
            })

    def notify(self, connectors: List[str], title: str, body: str) -> None:
        for name in connectors:
            conn = self.hub.get(name)
            if conn:
                msg = f"**{title}**\n{body}"
                if isinstance(conn, SlackConnector):
                    conn.post_message("#alerts", msg)
                elif isinstance(conn, DiscordConnector):
                    conn.send_message("alerts", msg)


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Integration Hub Demo")
    print("=" * 60)
    hub = IntegrationHub()
    # Register connectors (without real tokens, will show disconnected)
    hub.register(SlackConnector(token="xoxb-fake"))
    hub.register(GitHubConnector(token="ghp-fake"))
    hub.register(LinearConnector(token="lin_api_fake"))
    health = hub.health_check_all()
    for name, status in health.items():
        print(f"  {name}: {status.value}")
    print(f"Total connectors: {len(hub.list_all())}")
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
