"""Local-only NEWGEN web dashboard API; no network deployment or paid inference."""
from __future__ import annotations

import hmac
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import core

DASHBOARD = core.ROOT / "web" / "dashboard.html"
MAX_BODY_BYTES = 65536


def _worker() -> None:
    while True:
        try:
            queued = [j for j in core.list_jobs() if j.get("status") == "queued"]
            if queued:
                core.run_one(queued[-1]["id"])
        except Exception as exc:
            print("NEWGEN background worker error:", repr(exc), flush=True)
        time.sleep(1)


def recover_interrupted() -> None:
    for job in core.list_jobs():
        if job.get("status") == "running":
            job["status"] = "failed"
            job["error"] = "Controller stopped during execution; retry after inspecting artifacts"
            core._event(job, "recovery", "interrupted", job["error"])


class Handler(BaseHTTPRequestHandler):
    server_version = "NEWGEN-local/0.1"

    def _send(self, code: int, obj: object) -> None:
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise core.PipelineError("Invalid Content-Length") from exc
        if not 0 < length <= MAX_BODY_BYTES:
            raise core.PipelineError("Request body size must be 1..65536 bytes")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise core.PipelineError("Expected a JSON object")
        return data

    def _founder_authorized(self) -> bool:
        expected = os.environ.get("NEWGEN_FOUNDER_TOKEN")
        supplied = self.headers.get("X-Newgen-Founder-Token", "")
        return bool(expected and hmac.compare_digest(expected, supplied))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/":
                payload = DASHBOARD.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:;")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if path == "/api/status":
                jobs = core.list_jobs()
                engines = {name: ("configured" if spec.get("type") == "builtin" or spec.get("argv") else "unconfigured")
                           for name, spec in core.config()["stages"].items()}
                self._send(200, {
                    "service": "newgen", "mode": "local_prototype",
                    "jobs": len(jobs), "queued": sum(j["status"] == "queued" for j in jobs),
                    "running": sum(j["status"] == "running" for j in jobs),
                    "approved": sum(j["status"] == "approved" for j in jobs),
                    "engines": engines, "founder_approval_enabled": bool(os.environ.get("NEWGEN_FOUNDER_TOKEN"))
                })
                return
            if path == "/api/jobs":
                self._send(200, {"jobs": core.list_jobs()})
                return
            if path.startswith("/api/jobs/"):
                self._send(200, core.get_job(path.rsplit("/", 1)[-1]))
                return
            self._send(404, {"error": "Not found"})
        except (core.PipelineError, OSError, ValueError) as exc:
            self._send(400, {"error": str(exc)})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._json_body()
            if path == "/api/jobs":
                job = core.create_job(body.get("asset_id"), body.get("reference"))
                self._send(201, job)
                return
            if path == "/api/batches":
                items = body.get("items")
                maximum = max(1, min(100, int(core.config().get("limits", {}).get("max_new_batch", 100))))
                if not isinstance(items, list) or not 1 <= len(items) <= maximum:
                    raise core.PipelineError("Batch requires 1.." + str(maximum) + " assets")
                created, errors = [], []
                for index, item in enumerate(items):
                    if not isinstance(item, dict):
                        errors.append({"index": index, "error": "Expected asset object"})
                        continue
                    try:
                        created.append(core.create_job(item.get("asset_id"), item.get("reference"))["id"])
                    except core.PipelineError as exc:
                        errors.append({"index": index, "error": str(exc)})
                self._send(201 if created else 400, {"created": created, "errors": errors})
                return
            segments = path.strip("/").split("/")
            if len(segments) == 4 and segments[0:2] == ["api", "jobs"]:
                job_id, action = segments[2], segments[3]
                if action == "retry":
                    self._send(200, core.retry_job(job_id))
                    return
                if action == "approve":
                    if not self._founder_authorized():
                        self._send(403, {"error": "Founder token required (server NEWGEN_FOUNDER_TOKEN)"})
                        return
                    self._send(200, core.approve(job_id, str(body.get("gate", "")), str(body.get("actor", "")).strip()))
                    return
            self._send(404, {"error": "Not found"})
        except (core.PipelineError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})


def main() -> None:
    recover_interrupted()
    threading.Thread(target=_worker, daemon=True, name="newgen-worker").start()
    address = ("127.0.0.1", int(os.environ.get("NEWGEN_PORT", "8765")))
    server = ThreadingHTTPServer(address, Handler)
    print("NEWGEN dashboard: http://127.0.0.1:" + str(address[1]), flush=True)
    print("Local prototype only; no public network binding or paid GPU", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
