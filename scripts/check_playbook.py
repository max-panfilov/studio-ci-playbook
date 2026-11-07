#!/usr/bin/env python3
"""Static checks for the public, synthetic studio-ci-playbook repository."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML


ROOT = Path(__file__).resolve().parents[1]
KIND_TO_DEF = {
    "studio-ci": "studioCi",
    "release-policy": "releasePolicy",
    "plan": "plan",
    "request": "request",
    "release-manifest": "releaseManifest",
}
EXPECTED_MERMAID = {
    "docs/architecture.md": 1,
    "docs/scope-and-components.md": 1,
    "docs/native-release.md": 2,
    "docs/operations.md": 1,
}
HOSTED_RUNNERS = {"ubuntu-latest", "windows-latest", "macos-latest"}
PLACEHOLDER_SHAS = {char * 40 for char in "012"}
PLACEHOLDER_HASHES = {char * 64 for char in "01234"}
PLACEHOLDER_DIGESTS = {"sha256:" + value for value in PLACEHOLDER_HASHES}
PLACEHOLDER_UUIDS = {"00000000-0000-0000-0000-000000000000"}
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".sh", ".toml", ".txt"}
SHA_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")
HASH_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
UUID_RE = re.compile(
    r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![0-9a-f])",
    re.IGNORECASE,
)
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
PRIVATE_MARKERS = {
    "private-network-zone": re.compile(
        r"(?<![\w.-])(?:[a-z0-9-]+\.)+(?:pd|internal|lan)(?![\w.-])", re.I
    ),
    "local-root-path": re.compile(r"(?:/Users/|/opt/|/root/|/usr/local/|/home/|/var/lib/)"),
    "dated-private-receipt": re.compile(r"(?i)\b(?:accepted-release|runtime-journal)-\d{8}\.json\b"),
}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"),
    "assigned-secret": re.compile(
        r"(?i)\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9+/_.=-]{12,}"
    ),
    "bearer-token": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{16,}={0,2}"),
    "ssh-public-key": re.compile(r"\bssh-(?:rsa|ed25519)\s+AAAA[A-Za-z0-9+/]{20,}={0,3}"),
}
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})([^`]*)$")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]], source: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"{source}: DUPLICATE_JSON_KEY: {key}")
        result[key] = value
    return result


def load_json_text(text: str, source: str = "<memory>") -> Any:
    """Parse JSON and reject duplicate object keys."""
    return json.loads(text, object_pairs_hook=lambda pairs: _reject_duplicate_pairs(pairs, source))


def load_json(path: Path) -> Any:
    return load_json_text(path.read_text(encoding="utf-8"), path.as_posix())


def make_yaml() -> YAML:
    """Return a safe YAML 1.2 parser with duplicate-key rejection."""
    yaml = YAML(typ="safe")
    yaml.version = (1, 2)
    yaml.allow_duplicate_keys = False
    return yaml


def schema_for_kind(schema: dict[str, Any], kind: str) -> dict[str, Any]:
    definition = KIND_TO_DEF[kind]
    return {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{definition}",
    }


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in {"LICENSE", ".gitignore"}:
            files.append(path)
    return sorted(files)


def validate_json_examples(root: Path, errors: list[str]) -> None:
    schema_path = root / "schemas" / "examples.schema.json"
    try:
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        errors.append(f"{schema_path.relative_to(root)}: INVALID_SCHEMA: {exc}")
        return

    for path in sorted((root / "examples").glob("*.json")):
        relative = path.relative_to(root).as_posix()
        try:
            document = load_json(path)
            if document.get("synthetic") is not True or document.get("evidence") is not False:
                errors.append(f"{relative}: SYNTHETIC_FLAGS_REQUIRED")
            kind = document.get("kind")
            if kind not in KIND_TO_DEF:
                errors.append(f"{relative}: UNKNOWN_EXAMPLE_KIND")
                continue
            validator = Draft202012Validator(schema_for_kind(schema, kind))
            for failure in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
                location = "/".join(str(part) for part in failure.path) or "<root>"
                errors.append(f"{relative}: SCHEMA_VIOLATION at {location}: {failure.message}")
        except Exception as exc:
            errors.append(f"{relative}: INVALID_JSON: {exc}")


def validate_workflow_document(document: Any, source: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return [f"{source}: YAML_ROOT_MUST_BE_MAPPING"]
    if True in document or "on" not in document:
        errors.append(f"{source}: YAML_12_ON_KEY_REQUIRED")
    triggers = document.get("on")
    if not isinstance(triggers, dict) or set(triggers) != {"push", "workflow_dispatch"}:
        errors.append(f"{source}: PUSH_AND_DISPATCH_TRIGGERS_REQUIRED")
    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        errors.append(f"{source}: JOBS_REQUIRED")
        return errors
    for name, job in jobs.items():
        if not isinstance(job, dict):
            errors.append(f"{source}: JOB_MUST_BE_MAPPING: {name}")
            continue
        runs_on = job.get("runs-on")
        labels = runs_on if isinstance(runs_on, list) else [runs_on]
        if "self-hosted" not in labels:
            errors.append(f"{source}: SELF_HOSTED_RUNNER_REQUIRED: {name}")
        if any(label in HOSTED_RUNNERS for label in labels):
            errors.append(f"{source}: HOSTED_RUNNER_FORBIDDEN: {name}")
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{source}: STEPS_REQUIRED: {name}")
        elif any(not isinstance(step, dict) or not isinstance(step.get("run"), str) for step in steps):
            errors.append(f"{source}: SCHEMATIC_RUN_STEPS_REQUIRED: {name}")
    return errors


def validate_yaml_workflow(root: Path, errors: list[str]) -> None:
    path = root / "examples" / "gitea-ci.yml"
    relative = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
        document = make_yaml().load(text)
        errors.extend(validate_workflow_document(document, relative))
        if not text.startswith("# СИНТЕТИЧЕСКИЙ ПРИМЕР"):
            errors.append(f"{relative}: SYNTHETIC_WARNING_REQUIRED")
        if "PLAYBOOK_SYNTHETIC_ONLY: ''" not in text:
            errors.append(f"{relative}: DEFAULT_EXECUTION_REFUSAL_REQUIRED")
        if "${{ secrets." in text:
            errors.append(f"{relative}: SECRET_REFERENCE_FORBIDDEN")
    except Exception as exc:
        errors.append(f"{relative}: INVALID_YAML_12_OR_DUPLICATE_KEY: {exc}")


def _without_fences(text: str) -> str:
    output: list[str] = []
    inside = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            inside = not inside
            output.append("")
        else:
            output.append("" if inside else line)
    return "\n".join(output)


def github_anchors(text: str) -> set[str]:
    counts: Counter[str] = Counter()
    anchors: set[str] = set()
    for line in _without_fences(text).splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        heading = re.sub(r"`[^`]*`", "", match.group(1))
        heading = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading)
        heading = re.sub(r"<[^>]+>", "", heading).strip().lower().replace(" ", " ")
        anchor = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE).replace(" ", "-")
        index = counts[anchor]
        counts[anchor] += 1
        anchors.add(anchor if index == 0 else f"{anchor}-{index}")
    return anchors


def validate_markdown_file(path: Path, root: Path, errors: list[str]) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(root).as_posix()
    mermaid: list[dict[str, Any]] = []
    inside = False
    marker = ""
    language = ""
    start_line = 0
    body: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if not inside and match:
            inside = True
            marker = match.group(1)[0] * 3
            language = match.group(2).strip().split(maxsplit=1)[0] if match.group(2).strip() else ""
            start_line = number
            body = []
            continue
        if inside and line.strip() == marker:
            if language == "mermaid":
                mermaid.append({"path": relative, "line": start_line, "body": "\n".join(body)})
            inside = False
            marker = ""
            language = ""
            continue
        if inside:
            body.append(line)
    if inside:
        errors.append(f"{relative}:{start_line}: UNCLOSED_FENCE")

    plain = _without_fences(text)
    for match in LINK_RE.finditer(plain):
        raw = match.group(1).strip()
        if raw.startswith("<") and raw.endswith(">"):
            raw = raw[1:-1]
        target = raw.split(maxsplit=1)[0]
        if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue
        file_part, separator, anchor = target.partition("#")
        if not file_part:
            destination = path
        else:
            file_part = unquote(file_part)
            if file_part.startswith("/"):
                errors.append(f"{relative}: ABSOLUTE_MARKDOWN_LINK: {target}")
                continue
            destination = (path.parent / file_part).resolve()
        try:
            destination.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{relative}: LINK_ESCAPES_ROOT: {target}")
            continue
        if not destination.exists():
            errors.append(f"{relative}: MISSING_LINK_TARGET: {target}")
            continue
        if separator and anchor:
            if destination.is_dir() or destination.suffix != ".md":
                errors.append(f"{relative}: ANCHOR_ON_NON_MARKDOWN_TARGET: {target}")
                continue
            if unquote(anchor) not in github_anchors(destination.read_text(encoding="utf-8")):
                errors.append(f"{relative}: MISSING_ANCHOR: {target}")
    return mermaid


def _basic_mermaid_errors(block: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lines = [line.strip() for line in block["body"].splitlines() if line.strip()]
    location = f"{block['path']}:{block['line']}"
    if not lines or not re.match(r"^(?:flowchart\s+(?:TD|TB|LR|RL|BT)|sequenceDiagram|stateDiagram-v2)$", lines[0]):
        errors.append(f"{location}: MERMAID_DECLARATION_REQUIRED")
    square = 0
    curly = 0
    quoted = False
    escaped = False
    for char in block["body"]:
        if escaped:
            escaped = False
            continue
        if char == "\\" and quoted:
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            continue
        if quoted:
            continue
        square += (char == "[") - (char == "]")
        curly += (char == "{") - (char == "}")
        if square < 0 or curly < 0:
            errors.append(f"{location}: MERMAID_UNBALANCED_DELIMITERS")
            break
    if quoted or square != 0 or curly != 0:
        errors.append(f"{location}: MERMAID_UNBALANCED_DELIMITERS")
    for number, line in enumerate(lines[1:], start=block["line"] + 2):
        if re.search(r"\b[A-Za-z][\w-]*\[(?!\")", line):
            errors.append(f"{block['path']}:{number}: MERMAID_NODE_LABEL_MUST_BE_QUOTED")
    return errors


def validate_markdown(root: Path, errors: list[str]) -> None:
    blocks: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        blocks.extend(validate_markdown_file(path, root, errors))
    counts = Counter(block["path"] for block in blocks)
    for path, expected in EXPECTED_MERMAID.items():
        if counts[path] != expected:
            errors.append(f"{path}: MERMAID_COUNT_EXPECTED_{expected}_GOT_{counts[path]}")
    for block in blocks:
        errors.extend(_basic_mermaid_errors(block))


def find_safety_markers(
    text: str, source: str = "<memory>", include_private_markers: bool = True
) -> list[str]:
    findings: list[str] = []
    if include_private_markers:
        for name, pattern in PRIVATE_MARKERS.items():
            if pattern.search(text):
                findings.append(f"{source}: PRIVATE_MARKER_{name}")
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{source}: SECRET_PATTERN_{name}")
    if IPV4_RE.search(text):
        findings.append(f"{source}: IPV4_LITERAL_FORBIDDEN")
    for value in SHA_RE.findall(text):
        if value.lower() not in PLACEHOLDER_SHAS:
            findings.append(f"{source}: NON_PLACEHOLDER_GIT_SHA")
    for value in HASH_RE.findall(text):
        if value.lower() not in PLACEHOLDER_HASHES:
            findings.append(f"{source}: NON_PLACEHOLDER_HASH")
    for value in UUID_RE.findall(text):
        if value.lower() not in PLACEHOLDER_UUIDS:
            findings.append(f"{source}: NON_PLACEHOLDER_UUID")
    return findings


def _walk_values(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield child_path, key, child
            yield from _walk_values(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_values(child, f"{path}[{index}]")


def validate_placeholder_policy(root: Path, errors: list[str]) -> None:
    documents: list[tuple[str, Any]] = []
    for path in sorted((root / "examples").glob("*.json")):
        try:
            documents.append((path.relative_to(root).as_posix(), load_json(path)))
        except Exception:
            continue
    try:
        documents.append(("examples/gitea-ci.yml", make_yaml().load((root / "examples" / "gitea-ci.yml").read_text(encoding="utf-8"))))
    except Exception:
        pass

    for source, document in documents:
        for location, key, value in _walk_values(document):
            if key in {"run_id", "run_attempt", "attempt", "artifact_id", "build_run_id"} and value != 0:
                errors.append(f"{source}:{location}: ZERO_PLACEHOLDER_ID_REQUIRED")
            if key == "request_id" and value not in PLACEHOLDER_UUIDS:
                errors.append(f"{source}:{location}: NIL_UUID_REQUIRED")
            if key == "release_authorized" and value is not False:
                errors.append(f"{source}:{location}: RELEASE_AUTHORITY_MUST_BE_FALSE")
            if not isinstance(value, str):
                continue
            if value.startswith(("https://", "http://")):
                host = urlsplit(value).hostname or ""
                if not host.endswith(".invalid"):
                    errors.append(f"{source}:{location}: INVALID_HOSTNAME_REQUIRED")
            if value.startswith("registry.") and not value.split("/", 1)[0].endswith(".invalid"):
                errors.append(f"{source}:{location}: INVALID_REGISTRY_REQUIRED")
            if "@" in value and "sha256:" in value:
                digest = "sha256:" + value.rsplit("sha256:", 1)[1]
                if digest not in PLACEHOLDER_DIGESTS:
                    errors.append(f"{source}:{location}: NON_PLACEHOLDER_DIGEST")

    manifest_path = root / "examples" / "release-manifest.json"
    try:
        manifest = load_json(manifest_path)
        if manifest.get("status") != "synthetic-only" or manifest.get("scan", {}).get("fresh") is not False:
            errors.append("examples/release-manifest.json: NON_EVIDENCE_STATUS_REQUIRED")
    except Exception:
        pass


def validate_public_safety(root: Path, errors: list[str]) -> None:
    if not (root / "uv.lock").exists():
        errors.append("uv.lock: LOCKFILE_REQUIRED_FOR_REPRODUCIBLE_VERIFICATION")
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".pyz", ".pem", ".key", ".p12", ".pfx"}:
            errors.append(f"{path.relative_to(root)}: FORBIDDEN_BINARY_OR_CREDENTIAL_ARTIFACT")
    for path in iter_text_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{relative}: TEXT_UTF8_REQUIRED")
            continue
        # Marker literals live in this checker's own pattern definitions.
        # Secret, hash, UUID and IP checks still apply to the checker itself.
        errors.extend(
            find_safety_markers(
                text,
                relative,
                include_private_markers=relative != "scripts/check_playbook.py",
            )
        )


def run_checks(root: Path = ROOT) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    validate_json_examples(root, errors)
    validate_yaml_workflow(root, errors)
    validate_markdown(root, errors)
    validate_placeholder_policy(root, errors)
    validate_public_safety(root, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Playbook repository root")
    args = parser.parse_args()
    errors = run_checks(args.root)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"PLAYBOOK_CHECKS_FAILED: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("PLAYBOOK_CHECKS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
