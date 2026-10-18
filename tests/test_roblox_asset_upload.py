"""Tests for tools/roblox_asset_upload.py, tools/blender_export_roblox.py (outer half) and tools/studio/render_insert_snippet.py
(docs/169). No network, no Blender: the HTTP layer and the subprocess runner are replaced by fakes."""
from pathlib import Path
import contextlib
import io
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "studio"))
import roblox_asset_upload as up  # noqa: E402
import blender_export_roblox as bx  # noqa: E402
import render_insert_snippet as rs  # noqa: E402

SECRET = "SUPER-SECRET-KEY-12345"
FBX_HEAD = b"Kaydara FBX Binary  \x00\x1a\x00" + b"\x00" * 64


class FakeNet:
    """Records calls; answers POST /assets with an operation and GET operations/ after `pending` not-done answers."""

    def __init__(self, pending=1, post_status=200, post_body=None, done_body=None, status_429=0):
        self.calls = []
        self.pending = pending
        self.post_status = post_status
        self.post_body = post_body
        self.done_body = done_body
        self.status_429 = status_429

    def __call__(self, method, url, headers, body=None, timeout=60):
        self.calls.append((method, url, dict(headers), body))
        if method == "POST":
            if self.status_429 > 0:
                self.status_429 -= 1
                return 429, {"Retry-After": "1"}, b"{}"
            data = self.post_body if self.post_body is not None else json.dumps({"path": "operations/abc-123"}).encode()
            return self.post_status, {}, data
        if self.pending > 0:
            self.pending -= 1
            return 200, {}, json.dumps({"path": "operations/abc-123", "done": False}).encode()
        body = self.done_body or {"path": "operations/abc-123", "done": True,
                                  "response": {"assetId": "987654321", "moderationResult": {"moderationState": "MODERATION_STATE_APPROVED"}}}
        return 200, {}, json.dumps(body).encode()


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.fbx = self.dir / "cube.fbx"
        self.fbx.write_bytes(FBX_HEAD)
        self.env = {up.KEY_ENV: SECRET, up.USER_ENV: "42"}
        self.sleeps = []

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, argv, env=None, net=None):
        net = net or FakeNet()
        out, err = io.StringIO(), io.StringIO()
        lines = []
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = up.main(argv, environ=self.env if env is None else env, transport=net,
                           sleep=lambda s: self.sleeps.append(s), out=lines.append)
        return code, "\n".join(lines) + out.getvalue(), err.getvalue(), net

    # ---- file checks
    def test_bad_extension_empty_and_wrong_header(self):
        (self.dir / "a.txt").write_text("x")
        (self.dir / "empty.fbx").write_bytes(b"")
        (self.dir / "fake.fbx").write_bytes(b"not an fbx at all")
        for name in ("a.txt", "empty.fbx", "fake.fbx", "missing.fbx"):
            with self.assertRaises(up.UploadError):
                up.check_file(self.dir / name)

    def test_size_limit(self):
        big = self.dir / "big.fbx"
        big.write_bytes(FBX_HEAD + b"\0" * (up.MAX_BYTES + 1))
        with self.assertRaises(up.UploadError) as cm:
            up.check_file(big)
        self.assertIn("20 MB", str(cm.exception))

    def test_types(self):
        self.assertEqual(up.check_file(self.fbx)[:2], ("Model", "model/fbx"))

    # ---- dry run
    def test_dry_run_sends_nothing_and_hides_key(self):
        code, out, err, net = self.run_main([str(self.fbx), "--name", "Cube"])
        self.assertEqual(code, 0)
        self.assertEqual(net.calls, [])
        self.assertIn("DRY RUN", out)
        self.assertIn('"assetType": "Model"', out)
        self.assertIn("<hidden>", out)
        self.assertNotIn(SECRET, out + err)

    def test_dry_run_works_without_a_key(self):
        code, out, _, _ = self.run_main([str(self.fbx)], env={up.USER_ENV: "42"})
        self.assertEqual(code, 0)
        self.assertIn("NO (needed for --upload)", out)

    def test_missing_creator(self):
        code, _, err, _ = self.run_main([str(self.fbx), "--config", str(self.dir / "nope.json")], env={up.KEY_ENV: SECRET})
        self.assertEqual(code, 1)
        self.assertIn("No creator id", err)

    def test_creator_from_config_file(self):
        cfg = self.dir / "cfg.json"
        cfg.write_text(json.dumps({"creator_user_id": 77}))
        self.assertEqual(up.load_creator({}, cfg), ("userId", 77))
        with self.assertRaises(up.UploadError):
            up.load_creator({up.USER_ENV: "12abc"}, cfg)

    def test_there_is_no_key_argument(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                up.parse_args([str(self.fbx), "--key", "abc"])

    def test_too_many_files(self):
        files = []
        for i in range(up.MAX_FILES + 1):
            f = self.dir / ("m%d.fbx" % i)
            f.write_bytes(FBX_HEAD)
            files.append(str(f))
        code, _, err, net = self.run_main(files)
        self.assertEqual(code, 1)
        self.assertIn("At most", err)
        self.assertEqual(net.calls, [])

    # ---- real (mocked) upload
    def test_upload_flow(self):
        code, out, err, net = self.run_main([str(self.fbx), "--name", "My Cube", "--upload"])
        self.assertEqual(code, 0, err)
        self.assertIn("ASSET_ID 987654321", out)
        methods = [c[0] for c in net.calls]
        self.assertEqual(methods, ["POST", "GET", "GET"])
        method, url, headers, body = net.calls[0]
        self.assertEqual(url, "https://apis.roblox.com/assets/v1/assets")
        self.assertEqual(headers["x-api-key"], SECRET)  # sent only in the header
        self.assertTrue(headers["Content-Type"].startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="request"', body)
        self.assertIn(b'"displayName": "My Cube"', body)
        self.assertIn(b'"creator": {"userId": "42"}', body)
        self.assertIn(b'name="fileContent"; filename="cube.fbx"', body)
        self.assertIn(b"Content-Type: model/fbx", body)
        self.assertNotIn(SECRET.encode(), body)
        self.assertEqual(net.calls[1][1], "https://apis.roblox.com/assets/v1/operations/abc-123")
        self.assertNotIn(SECRET, out + err)

    def test_register_writes_entry_without_secrets(self):
        reg = self.dir / "reg.json"
        code, out, err, _ = self.run_main([str(self.fbx), "--upload", "--register", "--registry", str(reg)])
        self.assertEqual(code, 0, err)
        data = json.loads(reg.read_text())
        self.assertEqual(data[0]["assetId"], "987654321")
        self.assertEqual(data[0]["file"], "cube.fbx")
        self.assertNotIn(SECRET, reg.read_text())
        self.assertNotIn("42", [str(v) for v in data[0].values()])  # no creator id stored
        # second upload appends
        self.run_main([str(self.fbx), "--upload", "--register", "--registry", str(reg)])
        self.assertEqual(len(json.loads(reg.read_text())), 2)

    def test_no_register_without_flag(self):
        reg = self.dir / "reg.json"
        self.run_main([str(self.fbx), "--upload", "--registry", str(reg)])
        self.assertFalse(reg.exists())

    def test_upload_without_key_fails_before_network(self):
        code, _, err, net = self.run_main([str(self.fbx), "--upload"], env={up.USER_ENV: "42"})
        self.assertEqual(code, 1)
        self.assertIn(up.KEY_ENV, err)
        self.assertEqual(net.calls, [])

    def test_http_error_is_scrubbed(self):
        net = FakeNet(post_status=403, post_body=("echo of your key %s here" % SECRET).encode())
        code, out, err, _ = self.run_main([str(self.fbx), "--upload"], net=net)
        self.assertEqual(code, 1)
        self.assertIn("HTTP 403", err)
        self.assertNotIn(SECRET, out + err)
        self.assertIn("[KEY-REMOVED]", err)

    def test_operation_error_is_scrubbed(self):
        net = FakeNet(pending=0, done_body={"done": True, "error": {"code": 3, "message": "bad %s" % SECRET}})
        code, out, err, _ = self.run_main([str(self.fbx), "--upload"], net=net)
        self.assertEqual(code, 1)
        self.assertIn("refused", err)
        self.assertNotIn(SECRET, out + err)

    def test_rate_limit_backs_off_then_works(self):
        net = FakeNet(pending=0, status_429=2)
        code, out, err, _ = self.run_main([str(self.fbx), "--upload"], net=net)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.sleeps), 2)

    def test_rate_limit_gives_up(self):
        net = FakeNet(status_429=99)
        code, _, err, _ = self.run_main([str(self.fbx), "--upload"], net=net)
        self.assertEqual(code, 1)
        self.assertIn("429", err)

    def test_polling_times_out(self):
        net = FakeNet(pending=10**6)
        code, _, err, _ = self.run_main([str(self.fbx), "--upload", "--timeout", "6"], net=net)
        self.assertEqual(code, 1)
        self.assertIn("Still not done", err)

    def test_bad_operation_path_rejected(self):
        net = FakeNet(post_body=json.dumps({"path": "../../evil"}).encode())
        code, _, err, net = self.run_main([str(self.fbx), "--upload"], net=net)
        self.assertEqual(code, 1)
        self.assertEqual([c[0] for c in net.calls], ["POST"])

    def test_scrub(self):
        self.assertEqual(up.scrub("a %s b" % SECRET, SECRET), "a [KEY-REMOVED] b")
        self.assertEqual(up.scrub("plain", None), "plain")

    def test_clean_name(self):
        self.assertEqual(up.clean_name("Bad<>Name!!", "x"), "BadName")
        self.assertEqual(up.clean_name("???", "fallback"), "fallback")
        self.assertEqual(len(up.clean_name("a" * 200, "x")), up.NAME_MAX)

    def test_source_never_prints_the_key_variable(self):
        src = (ROOT / "tools" / "roblox_asset_upload.py").read_text(encoding="utf-8")
        for bad in ("print(key", "print(headers", "--key", "log(key"):
            self.assertNotIn(bad, src)


class BlenderExportOuterTests(unittest.TestCase):
    def test_command_shape(self):
        cmd = bx.blender_command("blender.exe", "a.blend", "o.fbx", rig=True, anim=True, apply_transforms=False, report="r.json")
        self.assertEqual(cmd[:4], ["blender.exe", "--background", "--factory-startup", "a.blend"])
        self.assertIn("--python", cmd)
        self.assertEqual(cmd[cmd.index("--") + 1:][:2], ["--out", "o.fbx"])
        self.assertIn("--anim", cmd)

    def test_find_blender_env_wins(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "blender.exe"
            exe.write_text("x")
            self.assertEqual(bx.find_blender({"BLENDER_EXE": str(exe)}), str(exe))

    def test_checker_absent_is_a_notice(self):
        lines = []
        self.assertIsNone(bx.run_checker("x.fbx", checker=ROOT / "no_such_checker.py", out=lines.append))
        self.assertIn("NOTICE", lines[0])

    def test_checker_present_is_run(self):
        calls = []

        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""

        with tempfile.TemporaryDirectory() as d:
            chk = Path(d) / "check.py"
            chk.write_text("")
            code = bx.run_checker("x.fbx", runner=lambda cmd, **kw: calls.append(cmd) or R(), checker=chk, out=lambda s: None)
        self.assertEqual(code, 0)
        self.assertEqual(calls[0][-1], "x.fbx")

    def test_outer_dry_run_runs_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            blend = Path(d) / "a.blend"
            blend.write_bytes(b"BLENDER")
            lines = []

            def boom(*a, **k):
                raise AssertionError("must not run")

            code = bx.outer_main([str(blend), "--out", str(Path(d) / "o.fbx"), "--dry-run"], runner=boom,
                                 environ={"BLENDER_EXE": str(blend)}, out=lines.append)
            self.assertEqual(code, 0)
            self.assertIn("--background", lines[0])

    def test_outer_rejects_bad_output_name(self):
        with tempfile.TemporaryDirectory() as d:
            blend = Path(d) / "a.blend"
            blend.write_bytes(b"x")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(bx.outer_main([str(blend), "--out", str(Path(d) / "o.obj")]), 2)

    def test_inner_script_uses_cockatoo_settings(self):
        src = (ROOT / "tools" / "blender_export_roblox.py").read_text(encoding="utf-8")
        for needle in ('axis_forward="-Z"', 'axis_up="Y"', "apply_unit_scale=True", 'colors_type="SRGB"', "add_leaf_bones=False"):
            self.assertIn(needle, src)


class SnippetTests(unittest.TestCase):
    def test_render_fills_placeholders(self):
        text = rs.render("123", "Cockatoosaurus", "Silly secret dinos v3")
        self.assertIn("AssetId = 123,", text)
        self.assertNotIn("__ASSET_ID__", text)
        self.assertNotIn("__NAME__", text)
        self.assertIn("DryRun = true,", text)
        self.assertIn("DryRun = false,", rs.render("123", "A", "B", live=True))

    def test_render_rejects_bad_input(self):
        for args in (("12x", "A", "B"), ("1", 'A"; os.exit()', "B"), ("1", "A", "B\nC")):
            with self.assertRaises(ValueError):
                rs.render(*args)

    def test_snippet_has_no_secrets_and_stays_out_of_src(self):
        text = (ROOT / "tools" / "studio" / "insert_uploaded_model.luau").read_text(encoding="utf-8")
        self.assertNotIn("ROBLOX_OPEN_CLOUD_KEY", text)
        self.assertNotIn("HttpService", text)


if __name__ == "__main__":
    unittest.main()
