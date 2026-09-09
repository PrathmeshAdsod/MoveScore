#!/usr/bin/env python3
"""
MoveScore — Deploy ADK Agent to Gemini Enterprise Agent Platform (Agent Runtime)

Usage:
    python scripts/deploy-agent-runtime.py

Prerequisites:
    - gcloud auth application-default login
    - Required APIs enabled (aiplatform.googleapis.com, storage.googleapis.com)
    - STAGING_BUCKET, PROJECT_ID, and REGION configured in environment or .env
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import MethodType

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import vertexai
from agent.runtime import app
from config import settings
from google.cloud import storage

PROJECT_ID = (
    os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
    or os.environ.get("PROJECT_ID")
    or settings.google_cloud_project_id
).strip()
REGION = (
    os.environ.get("GCP_REGION") or os.environ.get("REGION") or "us-central1"
).strip()
STAGING_BUCKET = os.environ.get("GCS_TEMP_BUCKET", "").removeprefix("gs://").strip()
GEMINI_SECRET_ID = os.environ.get("GEMINI_SECRET_ID", "gemini-api-key").strip()
GEMINI_SECRET_VERSION = os.environ.get("GEMINI_SECRET_VERSION", "latest").strip()
EXISTING_RESOURCE_NAME = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "").strip()
RUNTIME_SERVICE_ACCOUNT = os.environ.get("AGENT_RUNTIME_SERVICE_ACCOUNT", "").strip()

if not PROJECT_ID:
    print("ERROR: GOOGLE_CLOUD_PROJECT_ID or PROJECT_ID must be set.")
    sys.exit(1)
if not STAGING_BUCKET:
    print(
        "ERROR: GCS_TEMP_BUCKET must be set explicitly to the existing project bucket."
    )
    sys.exit(1)
if not RUNTIME_SERVICE_ACCOUNT:
    print(
        "ERROR: AGENT_RUNTIME_SERVICE_ACCOUNT must be set. "
        "MoveScore uses the documented custom service-account runtime identity."
    )
    sys.exit(1)

storage_client = storage.Client(project=PROJECT_ID)
if not storage_client.bucket(STAGING_BUCKET).exists():
    print(
        f"ERROR: Staging bucket gs://{STAGING_BUCKET} does not exist in {PROJECT_ID}."
    )
    sys.exit(1)

print("=" * 60)
print("Deploying MoveScore ADK Agent to Gemini Enterprise Agent Platform")
print("=" * 60)
print(f"Project:        {PROJECT_ID}")
print(f"Region:         {REGION}")
print(f"Staging Bucket: gs://{STAGING_BUCKET}")
print(f"Agent Model:    {settings.gemini_model}")
print(f"Lyria Model:    {settings.lyria_model}")
print("=" * 60)

client = vertexai.Client(
    project=PROJECT_ID,
    location=REGION,
    http_options={"api_version": "v1beta1"},
)

# google-cloud-aiplatform 2.1.0 currently includes an empty `secret_env: []`
# whenever plain environment variables are configured. Agent Runtime validates
# the mere presence of that empty field as a secret reference and rejects an
# otherwise valid deployment. Remove only the empty field before serialization.
_original_deployment_spec_builder = (
    client.agent_engines._generate_deployment_spec_or_raise
)


def _deployment_spec_without_empty_secret_env(
    agent_engines: object, **kwargs: object
) -> tuple[dict[str, object], list[str]]:
    del agent_engines
    deployment_spec, update_masks = _original_deployment_spec_builder(**kwargs)
    if not deployment_spec.get("secret_env"):
        deployment_spec.pop("secret_env", None)
    return deployment_spec, list(update_masks)


client.agent_engines._generate_deployment_spec_or_raise = MethodType(
    _deployment_spec_without_empty_secret_env,
    client.agent_engines,
)


def _resource_name(agent_engine: object) -> str:
    """Read the resource name across current and legacy SDK object shapes."""
    direct_name = getattr(agent_engine, "resource_name", None) or getattr(
        agent_engine, "name", None
    )
    if direct_name:
        return str(direct_name)
    api_resource = getattr(agent_engine, "api_resource", None)
    api_name = getattr(api_resource, "name", None)
    if api_name:
        return str(api_name)
    raise RuntimeError("Agent Runtime response did not include a resource name")


# Package only the modules required by Agent Runtime. The SDK recursively tars
# every path in extra_packages, so passing backend/ directly would also upload
# .env files, tests, caches, and the local virtual environment.
backend_dir = Path(__file__).parent.parent / "backend"
runtime_directories = ("agent", "schemas", "services", "prompts", "utils")
ignore_runtime_junk = shutil.ignore_patterns(
    ".env*",
    ".venv",
    "venv",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".ruff_cache",
    "tests",
    "scripts",
    "*.mp3",
    "*.mp4",
    "*.mov",
    "*.webm",
)

with tempfile.TemporaryDirectory(prefix="movescore-agent-package-") as package_tmp:
    runtime_backend = Path(package_tmp) / "backend"
    runtime_backend.mkdir()
    shutil.copy2(backend_dir / "config.py", runtime_backend / "config.py")
    for directory in runtime_directories:
        shutil.copytree(
            backend_dir / directory,
            runtime_backend / directory,
            ignore=ignore_runtime_junk,
        )

    packaged_files = [path for path in runtime_backend.rglob("*") if path.is_file()]
    packaged_size = sum(path.stat().st_size for path in packaged_files)
    print(
        f"Runtime package: {len(packaged_files)} source files, {packaged_size / 1024:.1f} KiB"
    )
    runtime_package_paths = [
        "config.py",
        *runtime_directories,
    ]

    if EXISTING_RESOURCE_NAME:
        print(f"Using existing Agent Runtime identity: {EXISTING_RESOURCE_NAME}")
        remote_agent = client.agent_engines.get(name=EXISTING_RESOURCE_NAME)
    else:
        print("\nCreating Agent Runtime identity...")
        identity_config = {"service_account": RUNTIME_SERVICE_ACCOUNT}
        remote_agent = client.agent_engines.create(
            config={
                "display_name": "MoveScore Choreography Music Agent",
                **identity_config,
            }
        )

    resource_name = _resource_name(remote_agent)
    effective_identity = getattr(
        getattr(remote_agent.api_resource, "spec", None), "effective_identity", ""
    )
    if not effective_identity:
        raise RuntimeError("Agent Runtime did not return an effective identity")

    member = f"serviceAccount:{RUNTIME_SERVICE_ACCOUNT}"
    gcloud_command = shutil.which("gcloud")
    if not gcloud_command:
        raise RuntimeError(
            "gcloud CLI is required to grant Agent Runtime IAM permissions"
        )
    print(f"Runtime identity: {member}")
    print(
        "Granting the exact agent identity access to the runtime secret and GCS bucket..."
    )
    subprocess.run(
        [
            gcloud_command,
            "secrets",
            "add-iam-policy-binding",
            GEMINI_SECRET_ID,
            f"--project={PROJECT_ID}",
            f"--member={member}",
            "--role=roles/secretmanager.secretAccessor",
            "--quiet",
        ],
        check=True,
    )
    subprocess.run(
        [
            gcloud_command,
            "storage",
            "buckets",
            "add-iam-policy-binding",
            f"gs://{STAGING_BUCKET}",
            f"--project={PROJECT_ID}",
            f"--member={member}",
            "--role=roles/storage.objectAdmin",
            "--quiet",
        ],
        check=True,
    )

    print("Deploying the ADK package to the provisioned Agent Runtime identity...")
    deployment_identity_config = {"service_account": RUNTIME_SERVICE_ACCOUNT}
    previous_working_directory = Path.cwd()
    try:
        # The SDK preserves supplied paths as tar archive names. Staging from
        # this directory keeps `agent/`, `schemas/`, and peers at archive root.
        os.chdir(runtime_backend)
        remote_agent = client.agent_engines.update(
            name=resource_name,
            agent=app,
            config={
                "display_name": "MoveScore Choreography Music Agent",
                "description": "Gemini and Lyria workflow for choreography-first music generation",
                "requirements": [
                    "cloudpickle==3.1.2",
                    "google-adk==2.8.0",
                    "google-cloud-aiplatform[agent_engines,adk]==2.1.0",
                    "google-genai==2.22.0",
                    "google-cloud-secret-manager==2.30.0",
                    "google-cloud-storage==3.14.1",
                    "pydantic==2.13.5",
                    "pydantic-settings==2.15.0",
                ],
                # The pickled app imports `agent`, `schemas`, and the other modules
                # as top-level packages, so each package must be staged directly.
                "extra_packages": runtime_package_paths,
                "staging_bucket": f"gs://{STAGING_BUCKET}",
                "gcs_dir_name": "movescore-agent-runtime",
                **deployment_identity_config,
                "env_vars": {
                    "GOOGLE_CLOUD_PROJECT_ID": PROJECT_ID,
                    "GCP_REGION": REGION,
                    "GCS_TEMP_BUCKET": STAGING_BUCKET,
                    "GEMINI_MODEL": settings.gemini_model,
                    "LYRIA_MODEL": settings.lyria_model,
                    "GEMINI_SECRET_ID": GEMINI_SECRET_ID,
                    "GEMINI_SECRET_VERSION": GEMINI_SECRET_VERSION,
                },
                "min_instances": 0,
                "max_instances": 1,
            },
        )
    finally:
        os.chdir(previous_working_directory)

resource_name = _resource_name(remote_agent)
effective_identity = getattr(
    getattr(remote_agent.api_resource, "spec", None), "effective_identity", ""
)
print("\n" + "=" * 60)
print("SUCCESS: Agent successfully deployed to Agent Runtime!")
print(f"AGENT_ENGINE_RESOURCE_NAME={resource_name}")
print(f"AGENT_EFFECTIVE_IDENTITY={effective_identity}")
print("\nNext step: Set this resource name in your backend Cloud Run service:")
print("  gcloud run services update movescore-backend \\")
print(f"    --region {REGION} \\")
print(f"    --update-env-vars AGENT_ENGINE_RESOURCE_NAME={resource_name}")
print("=" * 60)
