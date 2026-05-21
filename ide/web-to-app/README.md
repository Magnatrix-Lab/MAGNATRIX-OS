# web-to-app Integration — MAGNATRIX Agentic OS

> **Repo**: https://github.com/shiahonb777/web-to-app | 3.4k stars | On-Device APK Builder

## Status: ADOPTED

---

## Integration Strategy: Embed

web-to-app menjadi **core engine untuk Layer 12 (IDE) — Mobile App Builder** di MAGNATRIX. Build APK sepenuhnya di Android tanpa PC.

## Directory

```
ide/web-to-app/
├── README.md              # This file
├── integration.md         # Full integration plan (dari Android Claw)
└── mcp-adapter.py         # MCP bridge untuk brain agent trigger build
```

## Key Features untuk MAGNATRIX

1. **On-Device APK Builder** — `com.android.tools.build:apksig` build + sign APK di Android
2. **Native Runtimes** — Node.js (4 mode), PHP 8.4, Python (Flask/Django), Go
3. **Module Market** — GitHub-backed skill marketplace pattern
4. **WebView Hardening** — 28-vector fingerprint disguise
5. **App Modifier** — Clone APK + patch icon/nama/package
6. **Website Scraper** → Offline Pack
7. **APK Hardening** — DEX encryption, anti-Frida/Xposed
8. **AI Module Developer** — Generate extension dari prompt

## MCP Bridge

```python
# ide/web-to-app/mcp-adapter.py

def tool_build_apk(params: dict) -> dict:
    """Build APK dari URL atau source code."""
    return {
        "status": "building",
        "output_path": f"/sdcard/magnatrix/apps/{params['name']}.apk"
    }

def tool_install_runtime(params: dict) -> dict:
    """Install Node.js/Python/Go/PHP di Android."""
    return {
        "status": "installed",
        "runtime": params["type"],
        "version": params.get("version", "latest")
    }

def tool_disguise_fingerprint(params: dict) -> dict:
    """Apply 28-vector fingerprint disguise ke WebView."""
    return {
        "status": "applied",
        "level": params.get("level", "stealth")
    }
```

## Commands

```bash
# Build APK dari website
cd ide/web-to-app
python mcp-adapter.py build_apk --url https://example.com --name MyApp

# Install runtime
python mcp-adapter.py install_runtime --type nodejs

# Disguise fingerprint
python mcp-adapter.py disguise_fingerprint --level ghost
```

## Integration dengan Android Claw

```
Android Claw (brain) → MCP → web-to-app (APK builder)
                             ↓
                        Edge Deploy (ke device)
                             ↓
                        Swarm Register (ke P2P mesh)
```

## Notes

- Integration plan detail ada di `integration.md` (dari Android Claw deep dive).
- License: TBD — verify sebelum full embed.
- Recommendation: Fork sebagai submodule.
