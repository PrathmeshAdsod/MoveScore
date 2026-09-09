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
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import vertexai
from vertexai import types
from config import settings
from agent.runtime import app

PROJECT_ID = settings.google_cloud_project_id or os.environ.get("PROJECT_ID", "")
REGION = settings.gcp_region or os.environ.get("REGION", "us-central1")
STAGING_BUCKET = settings.gcs_temp_bucket or os.environ.get("GCS_TEMP_BUCKET", "movescore-temp")

if not PROJECT_ID:
    print("ERROR: GOOGLE_CLOUD_PROJECT_ID or PROJECT_ID must be set.")
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

client = vertexai.Client(project=PROJECT_ID, location=REGION)

# Packaging required local modules (agent, schemas, services, prompts, utils, config)
backend_dir = Path(__file__).parent.parent / "backend"
extra_packages = [str(backend_dir)]

print("\nDeploying Reasoning Engine with AdkApp...")
remote_agent = client.agent_engines.create(
    agent=app,
    config={
        "requirements": [
            "google-adk>=2.0.0",
            "google-cloud-aiplatform[agent_engines,adk]>=1.112.0",
            "google-genai>=2.0.0",
            "google-cloud-storage>=2.19.0",
            "pydantic>=2.9.0",
            "pydantic-settings>=2.6.0",
            "httpx>=0.27.0",
        ],
        "extra_packages": extra_packages,
        "staging_bucket": f"gs://{STAGING_BUCKET}",
        "identity_type": types.IdentityType.AGENT_IDENTITY,
    },
)

resource_name = remote_agent.resource_name
print("\n" + "=" * 60)
print("SUCCESS: Agent successfully deployed to Agent Runtime!")
print(f"Reasoning Engine Resource: {resource_name}")
print("\nNext step: Set this resource name in your backend Cloud Run service:")
print(f"  gcloud run services update movescore-backend \\")
print(f"    --region {REGION} \\")
print(f"    --update-env-vars AGENT_ENGINE_RESOURCE_NAME={resource_name}")
print("=" * 60)
