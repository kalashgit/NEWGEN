"""NEWGEN V1 durable, fail-closed local pipeline controller (Python stdlib).

No model provider, paid GPU or Golden promotion is configured by default.
External adapters are trusted, repo-owned executable commands, never user-supplied.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
STAGES = ("sprite_2d", "mesh_3d", "model_3d", "visual_qa", "gameplay_asset")
WRITE_LOCK = threading.RLock()


class PipelineError(Exception):
    pass


class EngineUnavailable(PipelineError):
    pass


class QARejected(PipelineError):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def data_root() -> Path:
    return Path(os.environ.get("NEWGEN_DATA_ROOT", str(ROOT / ".newgen"))).resolve()


def intake_root() -> Path:
    return Path(os.environ.get("NEWGEN_INTAKE_ROOT", str(ROOT / "intake"))).resolve()


def config_path() -> Path:
    return Path(os.environ.get("NEWGEN_ENGINE_CONFIG", str(ROOT / "config" / "engines.json"))).resolve()


def config() -> dict:
    doc = json.loads(config_path().read_text(encoding="utf-8"))
    if doc.get("schema") != "newgen.engine-config.v1":
        raise PipelineError("Unexpected engine configuration schema")
    for stage in STAGES + ("repair_3d",):
        if stage not in doc["stages"]:
            raise PipelineError("Missing engine: " + stage)
    return doc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _reference(relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise PipelineError("Reference must be a relative intake path")
    root = intake_root()
    candidate = (root / relative).resolve()
    if not _inside(candidate, root) or not candidate.is_file() or candidate.is_symlink():
        raise PipelineError("Reference must be a real file inside the intake directory")
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise PipelineError("Expected PNG/JPEG/WebP founder reference")
    return candidate


def _job_path(job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise PipelineError("Invalid job id")
    return data_root() / "jobs" / job_id / "job.json"


def _save(job: dict) -> None:
    with WRITE_LOCK:
        path = _job_path(job["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)


def get_job(job_id: str) -> dict:
    path = _job_path(job_id)
    if not path.is_file():
        raise PipelineError("Job not found")
    return json.loads(path.read_text(encoding="utf-8"))


def list_jobs() -> list[dict]:
    root = data_root() / "jobs"
    if not root.exists():
        return []
    jobs = []
    for path in root.glob("*/job.json"):
        try:
            jobs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(jobs, key=lambda x: x["created_at"], reverse=True)


def create_job(asset_id: str, reference: str) -> dict:
    if not isinstance(asset_id, str) or not ASSET_RE.fullmatch(asset_id):
        raise PipelineError("Use lowercase asset_id: a-z, 0-9, underscores (3-64 chars)")
    src = _reference(reference)
    with WRITE_LOCK:
        maxq = max(1, min(10000, int(config().get("limits", {}).get("max_queued_jobs", 500))))
        if sum(j["status"] in {"queued", "running"} for j in list_jobs()) >= maxq:
            raise PipelineError("Queue limit reached")
        now = utcnow()
        job = {
            "schema": "newgen.job.v1", "id": uuid.uuid4().hex,
            "asset_id": asset_id, "reference": reference, "source_sha256": sha256(src),
            "status": "queued", "stage": "queued", "created_at": now, "updated_at": now,
            "history": [], "artifacts": [], "visual_attempts": 0,
            "founder_golden_approved": False, "godot_iphone_verified": False,
            "error": None
        }
        _save(job)
        return job


def _event(job: dict, stage: str, status: str, detail: str = "") -> None:
    job["stage"] = stage
    job["updated_at"] = utcnow()
    job["history"].append({"time": job["updated_at"], "stage": stage, "status": status, "detail": detail[:1000]})
    _save(job)


def _safe_output(folder: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise PipelineError("Invalid adapter output")
    p = folder / name
    if not _inside(p, folder) or not p.is_file() or p.is_symlink():
        raise PipelineError("Adapter output missing or escaping stage dir: " + name)
    if p.stat().st_size == 0:
        raise PipelineError("Empty adapter output: " + name)
    return p


def _validate_stage(stage: str, folder: Path, files: list[Path]) -> None:
    names = [p.suffix.lower() for p in files]
    if stage in {"mesh_3d", "model_3d"}:
        if ".glb" not in names:
            raise PipelineError("Missing actual .glb geometry")
        for p in files:
            if p.suffix.lower() == ".glb" and p.open("rb").read(4) != b"glTF":
                raise PipelineError("Invalid GLB magic")
    if stage == "model_3d":
        if ".blend" not in names:
            raise PipelineError("Missing editable .blend")
        for p in files:
            if p.suffix.lower() == ".blend" and p.open("rb").read(7) != b"BLENDER":
                raise PipelineError("Invalid Blender file magic")
    if stage == "visual_qa":
        qa_path = next((p for p in files if p.name == "qa_report.json"), None)
        if qa_path is None:
            raise PipelineError("Missing independent qa_report.json")
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        if not isinstance(qa.get("passed"), bool) or not isinstance(qa.get("metrics"), dict):
            raise PipelineError("Malformed visual QA result")
        if not qa["passed"]:
            raise QARejected("Visual QA found defects: " + str(qa.get("defects", []))[:500])
    if stage == "gameplay_asset":
        if ".tscn" not in names or ".json" not in names:
            raise PipelineError("Gameplay requires Godot .tscn and JSON definition")


def run_stage(job: dict, stage: str, attempt: int = 1) -> list[dict]:
    spec = config()["stages"][stage]
    folder = data_root() / "jobs" / job["id"] / stage / f"attempt_{attempt:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    if spec.get("type") == "builtin" and spec.get("handler") == "source_intake" and stage == "sprite_2d":
        source = _reference(job["reference"])
        if sha256(source) != job["source_sha256"]:
            raise PipelineError("Source image has changed since admission")
        target = folder / ("original" + source.suffix.lower())
        shutil.copyfile(source, target)
        outputs = [target]
    else:
        if spec.get("type") != "external" or not spec.get("argv"):
            raise EngineUnavailable("No authorized adapter configured for " + stage)
        mapping = {
            "job_dir": str(folder.parents[1]), "stage_dir": str(folder),
            "asset_id": job["asset_id"], "reference": str(_reference(job["reference"])),
            "attempt": str(attempt), "recipe": str(folder.parents[1] / "recipe.json")
        }
        argv = spec["argv"]
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise PipelineError("Adapter command must be a literal argv list")
        try:
            command = [part.format_map(mapping) for part in argv]
        except (KeyError, ValueError) as exc:
            raise PipelineError("Invalid configured adapter placeholder") from exc
        timeout = min(7200, max(1, int(spec.get("timeout_s", 600))))
        try:
            run = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PipelineError("Adapter process could not complete: " + str(exc)[:400]) from exc
        (folder / "engine.log").write_text((run.stdout + "\n" + run.stderr)[-200000:], encoding="utf-8")
        if run.returncode:
            raise PipelineError(stage + " adapter exit code " + str(run.returncode))
        result_path = _safe_output(folder, "result.json")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("schema") != "newgen.stage-result.v1" or result.get("status") != "pass":
            raise PipelineError("Engine result did not pass stage contract")
        outnames = result.get("outputs")
        if not isinstance(outnames, list) or not outnames or not all(isinstance(x, str) for x in outnames):
            raise PipelineError("Missing result outputs")
        outputs = [_safe_output(folder, name) for name in outnames]
        _validate_stage(stage, folder, outputs)
    evidence = [{"stage": stage, "attempt": attempt,
                 "path": str(p.relative_to(data_root())), "sha256": sha256(p), "bytes": p.stat().st_size}
                for p in outputs]
    job["artifacts"].extend(evidence)
    _event(job, stage, "completed", str(len(outputs)) + " verified outputs")
    return evidence


def run_one(job_id: str) -> dict:
    job = get_job(job_id)
    if job["status"] != "queued":
        raise PipelineError("Only queued jobs can run")
    job["status"] = "running"
    job["error"] = None
    _event(job, "start", "running")
    try:
        run_stage(job, "sprite_2d")
        run_stage(job, "mesh_3d")
        attempts = max(1, min(5, int(config().get("limits", {}).get("max_qa_attempts", 3))))
        for attempt in range(1, attempts + 1):
            job["visual_attempts"] = attempt
            _save(job)
            run_stage(job, "model_3d", attempt)
            try:
                run_stage(job, "visual_qa", attempt)
                break
            except QARejected as exc:
                _event(job, "visual_qa", "rejected", str(exc))
                if attempt == attempts:
                    job["status"] = "needs_visual_review"
                    job["error"] = str(exc)
                    _save(job)
                    return job
                run_stage(job, "repair_3d", attempt)
        run_stage(job, "gameplay_asset")
        job["status"] = "awaiting_founder_review"
        _event(job, "technical_pipeline", "completed", "Not Golden; independent founder + iPhone gates required")
    except EngineUnavailable as exc:
        job["status"] = "blocked_unconfigured"
        job["error"] = str(exc)
        _event(job, job["stage"], "blocked", str(exc))
    except (PipelineError, OSError, ValueError, json.JSONDecodeError) as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        _event(job, job["stage"], "failed", str(exc))
    _save(job)
    return job


def retry_job(job_id: str) -> dict:
    with WRITE_LOCK:
        job = get_job(job_id)
        if job["status"] not in {"blocked_unconfigured", "failed", "needs_visual_review"}:
            raise PipelineError("This job is not retryable")
        job["status"] = "queued"
        job["error"] = None
        job["artifacts"] = []
        job["visual_attempts"] = 0
        _event(job, "queued", "retry_requested")
        return job


def approve(job_id: str, gate: str, actor: str) -> dict:
    if not actor.strip() or len(actor) > 120:
        raise PipelineError("Approver identity required")
    with WRITE_LOCK:
        job = get_job(job_id)
        if job["status"] not in {"awaiting_founder_review", "approved"}:
            raise PipelineError("Technical pipeline must complete before approval")
        if gate == "founder_golden":
            job["founder_golden_approved"] = True
        elif gate == "godot_iphone":
            if not job["founder_golden_approved"]:
                raise PipelineError("Founder Golden must precede iPhone acceptance")
            job["godot_iphone_verified"] = True
        else:
            raise PipelineError("Unknown approval gate")
        if job["founder_golden_approved"] and job["godot_iphone_verified"]:
            job["status"] = "approved"
        _event(job, gate, "human_approved", actor)
        return job
