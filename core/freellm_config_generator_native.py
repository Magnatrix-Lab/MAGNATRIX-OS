"""Free LLM Config Generator -- One-click snippets for Claude Code, Cursor, Codex, Aider."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ConfigSnippet:
    tool: str = ""
    provider: str = ""
    model: str = ""
    snippet: str = ""
    env_vars: dict = None

    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}

class FreellmConfigGenerator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._templates: dict[str, str] = {}
        self._persist_path = self.root / "freellm_configs.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._templates = data.get("templates", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({"templates": self._templates}, indent=2))

    def _mk_env(self, provider: str) -> str:
        return provider.upper().replace("-", "_") + "_API_KEY"

    def generate_claude_code(self, provider: str, model: str, api_key: str) -> ConfigSnippet:
        env_key = self._mk_env(provider)
        lines = [
            "# Add to ~/.claude-code/config.json or env",
            'export ' + env_key + '=\"' + api_key + '\"',
            'export CLAUDE_CODE_MODEL=\"' + model + '\"',
            'export CLAUDE_CODE_API_BASE=\"https://api.' + provider + '.com/v1\"',
            "",
        ]
        return ConfigSnippet("claude_code", provider, model, "\n".join(lines), {env_key: api_key})

    def generate_codex(self, provider: str, model: str, api_key: str) -> ConfigSnippet:
        env_key = self._mk_env(provider)
        lines = [
            "# Add to ~/.codex/config.json",
            "{",
            '  "provider": "' + provider + '",',
            '  "model": "' + model + '",',
            '  "apiKey": "' + api_key + '",',
            '  "baseURL": "https://api.' + provider + '.com/v1"',
            "}",
            "",
        ]
        return ConfigSnippet("codex", provider, model, "\n".join(lines), {env_key: api_key})

    def generate_cursor(self, provider: str, model: str, api_key: str) -> ConfigSnippet:
        env_key = self._mk_env(provider)
        masked = api_key[:4] + "****" + api_key[-4:] if len(api_key) >= 8 else "****"
        lines = [
            "# Cursor Settings > Models > Add Model",
            "Model ID: " + model,
            "Provider: OpenAI Compatible",
            "Base URL: https://api." + provider + ".com/v1",
            "API Key: " + masked,
            "",
        ]
        return ConfigSnippet("cursor", provider, model, "\n".join(lines), {env_key: api_key})

    def generate_aider(self, provider: str, model: str, api_key: str) -> ConfigSnippet:
        env_key = self._mk_env(provider)
        lines = [
            "# Run: aider --model " + provider + "/" + model,
            "export " + env_key + '=\"' + api_key + '\"',
            "aider --model " + provider + "/" + model + " --api-key " + api_key,
            "",
        ]
        return ConfigSnippet("aider", provider, model, "\n".join(lines), {env_key: api_key})

    def generate_generic(self, provider: str, model: str, api_key: str, base_url: str) -> ConfigSnippet:
        env_key = self._mk_env(provider)
        snippet = "curl " + base_url + "/chat/completions \\\n"
        snippet += '  -H "Authorization: Bearer ' + api_key + '" \\\n'
        snippet += '  -H "Content-Type: application/json" \\\n'
        snippet += '  -d \'{"model": "' + model + '", "messages": [{"role": "user", "content": "Hello"}]}\'\n'
        return ConfigSnippet("generic", provider, model, snippet, {env_key: api_key})

    def generate_for_tool(self, tool: str, provider: str, model: str, api_key: str, base_url: str = "") -> ConfigSnippet:
        if tool == "claude_code":
            return self.generate_claude_code(provider, model, api_key)
        elif tool == "codex":
            return self.generate_codex(provider, model, api_key)
        elif tool == "cursor":
            return self.generate_cursor(provider, model, api_key)
        elif tool == "aider":
            return self.generate_aider(provider, model, api_key)
        else:
            url = base_url or ("https://api." + provider + ".com/v1")
            return self.generate_generic(provider, model, api_key, url)

    def save_template(self, name: str, template: str) -> None:
        self._templates[name] = template
        self._save()

    def to_dict(self) -> dict:
        return {"template_count": len(self._templates)}

    def get_stats(self) -> dict:
        return {"templates": len(self._templates)}

__all__ = ["FreellmConfigGenerator", "ConfigSnippet"]
