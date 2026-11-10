"""Deployment contract tests for Render, Vercel, and committed secret hygiene."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.request import urlopen

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    """Reads one deployment file from the repository so tests remain easy to audit."""
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _tracked_files() -> list[Path]:
    """Asks Git for committed paths so generated dependencies never enter secret scans."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return [
        REPO_ROOT / path
        for path in result.stdout.decode("utf-8").split("\0")
        if path
    ]


def _connection_urls(environ: Mapping[str, str]) -> tuple[str, str] | None:
    """Returns both live targets only when a maintainer deliberately configured both."""
    render_url = environ.get("RENDER_HEALTH_URL", "").strip()
    vercel_url = environ.get("VERCEL_URL", "").strip()
    if not render_url or not vercel_url:
        return None
    return render_url, vercel_url


def _check_live_connections(
    environ: Mapping[str, str],
    opener: Callable[..., object] = urlopen,
) -> str:
    """Checks both deployments, or reports not-yet-run before making any network call."""
    urls = _connection_urls(environ)
    if urls is None:
        return "not-yet-run"

    # These requests run only in the explicitly selected optional-live test.
    for url in urls:
        with opener(url, timeout=15) as response:  # type: ignore[attr-defined]
            if response.status >= 400:
                raise AssertionError(f"Deployment check failed with HTTP {response.status}")
    return "ok"


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-1"])
def test_dockerfile_uses_render_port_with_8000_fallback(_acceptance_case):
    """Protects Render's dynamic port while preserving port 8000 for local containers."""
    dockerfile = _read("backend/Dockerfile")
    assert "COPY pyproject.toml README.md ./" in dockerfile
    assert dockerfile.index("COPY pyproject.toml README.md ./") < dockerfile.index(
        "pip install --no-cache-dir ."
    )
    assert "${PORT:-8000}" in dockerfile
    assert "USER appuser" in dockerfile
    assert "COPY .env" not in dockerfile


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-2"])
def test_dockerignore_excludes_env_virtualenv_and_caches(_acceptance_case):
    """Keeps credentials, local packages, and generated caches outside Docker images."""
    dockerignore = _read("backend/.dockerignore").splitlines()
    assert ".env" in dockerignore
    assert ".env.*" in dockerignore
    assert ".venv/" in dockerignore
    assert "__pycache__/" in dockerignore
    assert ".pytest_cache/" in dockerignore


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-3"])
def test_render_blueprint_has_safe_health_and_environment_contract(_acceptance_case):
    """Checks the Blueprint's public settings without needing a Render account."""
    render_yaml = _read("render.yaml")
    assert "plan: free" in render_yaml
    assert "dockerContext: ./backend" in render_yaml
    assert "healthCheckPath: /health" in render_yaml
    assert "preDeployCommand: alembic upgrade head" in render_yaml
    assert render_yaml.count("sync: false") == 9
    assert re.search(r"^\s+value\s*:", render_yaml, flags=re.MULTILINE) is None


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-5"])
def test_frontend_example_names_public_variables_and_versioned_api(_acceptance_case):
    """Documents the three browser-safe names and keeps API calls under /api/v1."""
    example = _read("frontend/.env.example")
    entries = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in example.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    assert set(entries) == {
        "NEXT_PUBLIC_SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_API_URL",
    }
    assert entries["NEXT_PUBLIC_API_URL"].rstrip("/").endswith("/api/v1")


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-6"])
def test_committed_files_contain_no_real_keys(_acceptance_case):
    """Rejects common private-key formats while allowing clearly labeled examples."""
    secret_patterns = (
        re.compile(r"sk-ant-[A-Za-z0-9_-]{24,}"),
        re.compile(
            r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"
        ),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    )
    findings: list[str] = []

    # Scan only UTF-8 tracked files; binary assets cannot contain usable text credentials.
    for path in _tracked_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if "placeholder" in line.lower() or "your-" in line.lower():
                continue
            if any(pattern.search(line) for pattern in secret_patterns):
                findings.append(f"{path.relative_to(REPO_ROOT)}:{line_number}")

    assert findings == [], f"Possible committed secrets: {findings}"


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-7"])
def test_production_api_configuration_fails_closed_without_localhost(_acceptance_case):
    """Ensures production rejects a missing API URL instead of silently using localhost."""
    api_client = _read("frontend/src/lib/api.ts")
    production_branch = api_client.split(
        'if (process.env.NODE_ENV === "production")', 1
    )[1].split("return", 1)[0]
    assert "Missing required production configuration: NEXT_PUBLIC_API_URL" in production_branch
    assert "localhost" not in production_branch
    assert 'return "http://localhost:8000/api/v1";' in api_client


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-8"])
def test_live_connection_check_waits_for_both_urls(_acceptance_case):
    """Reports not-yet-run and proves no request happens while either URL is absent."""
    network_calls: list[str] = []

    def recording_opener(url: str, timeout: int):
        """Records an accidental request so the assertion can explain the regression."""
        network_calls.append(f"{url}:{timeout}")
        raise AssertionError("The connection check called the network before both URLs existed")

    assert _check_live_connections({}, recording_opener) == "not-yet-run"
    assert (
        _check_live_connections(
            {"RENDER_HEALTH_URL": "https://api.example.invalid/health"},
            recording_opener,
        )
        == "not-yet-run"
    )
    assert network_calls == []


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-9"])
def test_readme_documents_render_and_vercel_without_values(_acceptance_case):
    """Keeps the production runbook complete without embedding deployment credentials."""
    readme = _read("README.md")
    required_text = (
        "Render backend",
        "backend",
        "/health",
        "alembic upgrade head",
        "DIRECT_URL",
        "Vercel frontend",
        "Root Directory to `frontend`",
        "NEXT_PUBLIC_SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_API_URL",
        "/api/v1",
        "CORS_ORIGINS",
        "scheme and host only, with no path",
        "does not run a seed",
    )
    assert all(item in readme for item in required_text)
    assert re.search(r"(?:DATABASE_URL|ANTHROPIC_API_KEY|SUPABASE_JWT_SECRET)=", readme) is None


@pytest.mark.optional_live
def test_optional_live_render_and_vercel_connections():
    """Checks real deployments only when a maintainer opts in with both complete URLs."""
    if _connection_urls(os.environ) is None:
        pytest.skip("not-yet-run: set both RENDER_HEALTH_URL and VERCEL_URL")

    assert _check_live_connections(os.environ) == "ok"
    with urlopen(os.environ["RENDER_HEALTH_URL"], timeout=15) as response:
        body = json.loads(response.read().decode("utf-8"))
    assert body["status"] == "ok"
