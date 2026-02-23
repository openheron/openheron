"""Tests for browser control service + routes."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openheron.browser_service import BrowserDispatchRequest, get_browser_control_service
from openheron.browser_runtime import configure_browser_runtime


class BrowserServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        configure_browser_runtime(None)

    def test_dispatch_basic_lifecycle_routes(self) -> None:
        service = get_browser_control_service()

        status = service.dispatch(BrowserDispatchRequest(method="GET", path="/"))
        self.assertEqual(status.status, 200)
        self.assertFalse(status.body["running"])

        started = service.dispatch(BrowserDispatchRequest(method="POST", path="/start"))
        self.assertEqual(started.status, 200)
        self.assertTrue(started.body["running"])

        stopped = service.dispatch(BrowserDispatchRequest(method="POST", path="/stop"))
        self.assertEqual(stopped.status, 200)
        self.assertFalse(stopped.body["running"])

    def test_dispatch_agent_routes(self) -> None:
        service = get_browser_control_service()
        service.dispatch(BrowserDispatchRequest(method="POST", path="/start"))

        opened = service.dispatch(
            BrowserDispatchRequest(
                method="POST",
                path="/tabs/open",
                body={"url": "https://example.com"},
            )
        )
        self.assertEqual(opened.status, 200)
        target_id = opened.body["targetId"]

        snap = service.dispatch(
            BrowserDispatchRequest(
                method="GET",
                path="/snapshot",
                query={"targetId": target_id, "format": "ai"},
            )
        )
        self.assertEqual(snap.status, 200)
        self.assertEqual(snap.body["targetId"], target_id)

        navigated = service.dispatch(
            BrowserDispatchRequest(
                method="POST",
                path="/navigate",
                body={"targetId": target_id, "url": "https://example.org"},
            )
        )
        self.assertEqual(navigated.status, 200)
        self.assertIn("example.org", navigated.body["url"])

        with tempfile.TemporaryDirectory() as tmp:
            shot_path = Path(tmp) / "shots" / "service.png"
            shot = service.dispatch(
                BrowserDispatchRequest(
                    method="POST",
                    path="/screenshot",
                    body={"targetId": target_id, "type": "png", "path": str(shot_path)},
                )
            )
            self.assertEqual(shot.status, 200)
            self.assertTrue(shot.body["imageBase64"])
            self.assertEqual(Path(shot.body["path"]).resolve(), shot_path.resolve())
            self.assertTrue(shot_path.exists())

        with tempfile.TemporaryDirectory() as tmp:
            upload_file = Path(tmp) / "demo.txt"
            upload_file.write_text("demo", encoding="utf-8")
            uploaded = service.dispatch(
                BrowserDispatchRequest(
                    method="POST",
                    path="/hooks/file-chooser",
                    body={"targetId": target_id, "paths": [str(upload_file)], "ref": "#file"},
                )
            )
        self.assertEqual(uploaded.status, 200)
        self.assertEqual(uploaded.body["uploadedPaths"], [str(upload_file)])

        dialog = service.dispatch(
            BrowserDispatchRequest(
                method="POST",
                path="/hooks/dialog",
                body={"targetId": target_id, "accept": True, "promptText": "yes"},
            )
        )
        self.assertEqual(dialog.status, 200)
        self.assertTrue(dialog.body["armed"])

        acted = service.dispatch(
            BrowserDispatchRequest(
                method="POST",
                path="/act",
                body={"targetId": target_id, "request": {"kind": "click", "ref": "e1"}},
            )
        )
        self.assertEqual(acted.status, 200)
        self.assertEqual(acted.body["kind"], "click")

        acted_flat = service.dispatch(
            BrowserDispatchRequest(
                method="POST",
                path="/act",
                body={"targetId": target_id, "kind": "wait", "timeMs": 10},
            )
        )
        self.assertEqual(acted_flat.status, 200)
        self.assertEqual(acted_flat.body["kind"], "wait")

    def test_dispatch_reports_404_for_unknown_route(self) -> None:
        service = get_browser_control_service()
        res = service.dispatch(BrowserDispatchRequest(method="GET", path="/missing"))
        self.assertEqual(res.status, 404)
        self.assertFalse(res.body["ok"])

    def test_dispatch_validates_upload_and_dialog_inputs(self) -> None:
        service = get_browser_control_service()
        no_paths = service.dispatch(
            BrowserDispatchRequest(method="POST", path="/hooks/file-chooser", body={"paths": []})
        )
        self.assertEqual(no_paths.status, 400)
        self.assertFalse(no_paths.body["ok"])

        missing_accept = service.dispatch(
            BrowserDispatchRequest(method="POST", path="/hooks/dialog", body={"promptText": "x"})
        )
        self.assertEqual(missing_accept.status, 400)
        self.assertFalse(missing_accept.body["ok"])


if __name__ == "__main__":
    unittest.main()
