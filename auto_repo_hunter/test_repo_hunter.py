#!/usr/bin/env python3
"""Integration tests — Auto Repo Hunter (Layer 13.5)."""
import json, os, sys, tempfile, unittest
from unittest.mock import patch
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "auto_repo_hunter")
if _REPO_DIR not in sys.path: sys.path.insert(0, _REPO_DIR)
from repo_hunter_native import RepoHunter, SearchQuery, RepoResult
from pattern_extractor_native import PatternExtractor, PatternSummary
from native_generator_native import NativeGenerator

MOCK_SEARCH = {"total_count": 2, "items": [
    {"full_name": "mockuser/demo-repo", "html_url": "https://github.com/mockuser/demo-repo",
     "description": "Demo for testing.", "stargazers_count": 1200, "forks_count": 45,
     "language": "Python", "topics": ["demo", "patterns"], "created_at": "2024-01-15T10:00:00Z",
     "updated_at": "2025-03-20T14:30:00Z", "open_issues_count": 3, "size": 420,
     "license": {"spdx_id": "MIT"}},
    {"full_name": "mockuser/another-lib", "html_url": "https://github.com/mockuser/another-lib",
     "description": "Another lib.", "stargazers_count": 800, "forks_count": 20,
     "language": "Python", "topics": ["async"], "created_at": "2023-06-01T08:00:00Z",
     "updated_at": "2025-02-10T09:00:00Z", "open_issues_count": 0, "size": 210, "license": None},
]}

class FakeResp:
    def __init__(self, body, headers=None):
        self.body = json.dumps(body).encode()
        self._h = headers or {}
        self._h.setdefault("X-RateLimit-Remaining", "4999")
        self._h.setdefault("X-RateLimit-Reset", "9999999999")
    def read(self): return self.body
    def __enter__(self): return self
    def __exit__(self, *a): pass
    @property
    def headers(self): return self._h

def mock_factory(url_map):
    def fn(req, **kw):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        for prefix, data in url_map.items():
            if url.startswith(prefix): return FakeResp(data)
        return FakeResp({"message": "Not Found"}, {"status": 404})
    return fn

class TestSearch(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_basic(self, mock):
        mock.side_effect = mock_factory({"https://api.github.com/search/repositories": MOCK_SEARCH})
        hunter = RepoHunter()
        q = SearchQuery(keywords=["demo"], language="python", min_stars=100)
        res = hunter.search(q, max_results=5, use_cache=False)
        self.assertEqual(len(res), 2)
        self.assertIsInstance(res[0], RepoResult)
        self.assertEqual(res[0].full_name, "mockuser/demo-repo")
        self.assertEqual(res[0].stars, 1200)
        self.assertTrue(res[0].relevance_score > 0)

class TestExtractor(unittest.TestCase):
    def test_synthetic_repo(self):
        with tempfile.TemporaryDirectory() as td:
            open(os.path.join(td, "README.md"), "w").write("# Demo\nArchitecture: event-driven microservices.\n")
            open(os.path.join(td, "core.py"), "w").write('''import json\nfrom dataclasses import dataclass\n@dataclass\nclass Event:\n    id: str\n    payload: dict\nclass EventBus:\n    def __init__(self): self._handlers = []\n    async def publish(self, event: Event):\n        for h in self._handlers: await h(event)\n''')
            ex = PatternExtractor()
            s = ex.extract("mockuser/demo-repo", "https://github.com/mockuser/demo-repo", td, 5)
            self.assertIn("event-driven", " ".join(s.architecture_notes).lower())
            ptypes = {p["type"] for p in s.patterns}
            self.assertIn("dataclass_pattern", ptypes)
            self.assertIn("async_pattern", ptypes)
            self.assertIn("class_inventory", ptypes)

class TestGenerator(unittest.TestCase):
    def test_generate(self):
        with tempfile.TemporaryDirectory() as td:
            s = PatternSummary(
                repo_full_name="mockuser/demo-repo", repo_url="https://github.com/mockuser/demo-repo",
                extraction_time="2025-01-01T00:00:00Z", tech_stack=["python"],
                architecture_notes=["Event-driven microservices with registry pattern"],
                patterns=[{"type": "dataclass_pattern", "count": 2},
                           {"type": "async_pattern", "count": 1},
                           {"type": "class_inventory", "data": ["EventBus", "Registry"]}],
                raw_readme_summary="demo")
            sp = os.path.join(td, "p.json")
            open(sp, "w").write(s.to_json())
            gen = NativeGenerator(sp)
            out, name = gen.generate(output_dir=td)
            self.assertTrue(os.path.exists(out))
            src = open(out).read()
            self.assertIn("class EventBus", src)
            self.assertIn("class Registry", src)
            compile(src, out, "exec")
            self.assertTrue(os.path.exists(out.replace(".py", "_meta.json")))

    def test_layer_map(self):
        with tempfile.TemporaryDirectory() as td:
            s = PatternSummary(repo_full_name="t/x", repo_url="https://github.com/t/x",
                extraction_time="2025-01-01T00:00:00Z", tech_stack=["python"],
                architecture_notes=["High-frequency trading engine"], patterns=[], raw_readme_summary="trading")
            sp = os.path.join(td, "p.json"); open(sp, "w").write(s.to_json())
            self.assertEqual(NativeGenerator(sp)._classify_layer()[0], "layer12")

class TestLoopUnit(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_pipeline(self, mock):
        mock.side_effect = mock_factory({"https://api.github.com/search/repositories": MOCK_SEARCH})
        from self_improvement_loop import SelfImprovementLoop
        loop = SelfImprovementLoop()
        loop.cfg["queries"] = [{"keywords": ["demo"], "language": "python", "min_stars": 100, "sort": "stars", "max_results": 2}]
        loop.cfg["max_repos_per_run"] = 2
        loop.cfg["max_py_files_per_repo"] = 5
        loop.cfg["git_remote"] = "__mock__"
        results = loop.run()
        self.assertTrue(len(results) > 0)
        for r in results:
            self.assertIn("repo", r)
            self.assertIn("status", r)

if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=2).run(unittest.TestLoader().loadTestsFromModule(sys.modules[__name__]))
    sys.exit(0 if r.wasSuccessful() else 1)
