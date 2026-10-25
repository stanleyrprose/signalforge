"""Regression for isolated S01 inference and retained, redacted provider failures."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from signalforge import s01_codex_review_runner as runner

class RuntimeInvocationTests(unittest.TestCase):
    def connection(self):
        conn=MagicMock()
        conn.__enter__.return_value=conn
        conn.execute.return_value.fetchall.return_value=[
            ("https://myanmar.gov.mm/news/example","Example","Source body","a"*64)]
        return conn

    def test_inference_does_not_load_workspace_apps_or_user_config(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            calls=[]
            def invoke(args, **kwargs):
                calls.append(args)
                Path(args[args.index("-o")+1]).write_text(json.dumps({"items":[{"item_id":"0"}]}))
                return subprocess.CompletedProcess(args,0,stderr="")
            summary={"total_discovered":1,"included":1,"excluded":0,"unresolved":0,"digest_publish_gate":"PASS"}
            with patch.object(runner,"connect",return_value=self.connection()), \
                 patch.object(runner.subprocess,"run",side_effect=invoke), \
                 patch.object(runner,"validate_review_result",return_value=[{"source_url":"https://myanmar.gov.mm/news/example"}]), \
                 patch.object(runner,"reconcile_ai_digest",return_value=summary), \
                 patch.object(runner,"render_chinese_digest",return_value="审核"):
                self.assertEqual(runner.run(root/"db",root)["included"],1)
            self.assertIn("--ignore-user-config",calls[0])
            self.assertIn("--ephemeral",calls[0])
            self.assertIn("apps",calls[0])
            self.assertIn("plugins",calls[0])

    def test_failed_provider_retains_bounded_redacted_diagnostic(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with patch.object(runner,"connect",return_value=self.connection()), \
                 patch.object(runner.subprocess,"run",return_value=subprocess.CompletedProcess(
                     ["codex"],1,stderr="token=SECRET refresh_token_reused workspace routing discovery unauthorized (401)")):
                with self.assertRaisesRegex(RuntimeError, 'CODEX_AUTH_REAUTH_REQUIRED'):
                    runner.run(root/"db",root)
            diagnostic=json.loads((root/"model-error-01.json").read_text())
            self.assertNotIn("SECRET",diagnostic["detail"])
            self.assertIn("401",diagnostic["detail"])
            self.assertEqual(diagnostic["attempt"],1)
