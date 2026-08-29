import json
import os
import subprocess
import tempfile
import unittest
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "archive_config.py"
HTML_SCRIPT = Path(__file__).parents[1] / "scripts" / "html_to_markdown.py"


class ArchiveConfigTests(unittest.TestCase):
    def run_script(self, *args: str, home: Path, check: bool = True):
        env = dict(os.environ)
        env["HOME"] = str(home)
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            text=True,
            capture_output=True,
            env=env,
            check=check,
        )

    def test_project_overrides_personal_recursively(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            nested = project / "nested"
            (home / ".codex").mkdir(parents=True)
            nested.mkdir(parents=True)
            (home / ".codex" / "article-archiver.json").write_text(
                json.dumps({"assets": {"mode": "remote"}, "output_dir": "personal"}), encoding="utf-8"
            )
            (project / ".article-archiver.json").write_text(
                json.dumps({"output_dir": "project"}), encoding="utf-8"
            )
            result = self.run_script("resolve", "--cwd", str(nested), home=home)
            value = json.loads(result.stdout)
            self.assertEqual(value["config"]["output_dir"], "project")
            self.assertEqual(value["config"]["assets"]["mode"], "remote")

    def test_plan_sanitizes_and_detects_conflict(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            first = self.run_script("plan", "--cwd", str(project), "--title", "Bad: title.md", home=home)
            paths = json.loads(first.stdout)["paths"]
            article = Path(paths[0])
            article.parent.mkdir(parents=True)
            article.write_text("occupied", encoding="utf-8")
            second = self.run_script("plan", "--cwd", str(project), "--title", "Bad: title.md", home=home, check=False)
            self.assertEqual(second.returncode, 2)
            self.assertIn(str(article), json.loads(second.stdout)["conflicts"])

    def test_default_plan_uses_flat_original_and_grouped_assets(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            result = self.run_script("plan", "--cwd", str(project), "--title", "原始标题", home=home)
            paths = json.loads(result.stdout)["paths"]
            self.assertEqual(paths, [
                str(project.resolve() / "articles" / "原始标题.md"),
                str(project.resolve() / "articles" / "assets" / "原始标题"),
            ])

    def test_init_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            self.run_script("init", "--scope", "project", "--cwd", str(project), home=home)
            result = self.run_script("init", "--scope", "project", "--cwd", str(project), home=home, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("拒绝替换已有配置", result.stderr)


class HtmlToMarkdownTests(unittest.TestCase):
    def test_converts_isolated_fragment(self):
        spec = importlib.util.spec_from_file_location("html_to_markdown", HTML_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        result = module.convert(
            '<article><h1>Title</h1><p>Hello <strong>world</strong>.</p>'
            '<ul><li><a href="https://example.com">Link</a></li></ul>'
            '<pre><code>x &lt; 2</code></pre><script>bad()</script></article>'
        )
        self.assertIn("# Title", result)
        self.assertIn("Hello **world**.", result)
        self.assertIn("- [Link](https://example.com)", result)
        self.assertIn("```\nx < 2\n```", result)
        self.assertNotIn("bad()", result)


if __name__ == "__main__":
    unittest.main()
