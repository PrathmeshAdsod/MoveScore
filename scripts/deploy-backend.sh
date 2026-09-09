#!/usr/bin/env bash
# =============================================================================
# deploy-backend.sh — Build and deploy the FastAPI backend to Cloud Run
#
# Usage:
#   ./scripts/deploy-backend.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - PROJECT_ID, REGION, SERVICE_ACCOUNT set below or as environment variables
#   - Artifact Registry repository created (see GCP_SETUP_AND_DEPLOY.md)
#   - GCS bucket created with lifecycle rules
#   - Required APIs enabled
#
# DO NOT EXECUTE THIS YOURSELF — read GCP_SETUP_AND_DEPLOY.md first.
# =============================================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
# Override these with environment variables or edit directly.
PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="movescore-backend"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/agentic-cinema/${SERVICE_NAME}"

# Service account that Cloud Run will run as (must have required IAM roles)
RUNTIME_SA="${RUNTIME_SA:-movescore-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com}"

# Environment variables for the Cloud Run service
# These are read from local .env for the deployment command.
GCS_TEMP_BUCKET="${GCS_TEMP_BUCKET:-agentic-cinema-temp}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.8-flash}"
LYRIA_MODEL="${LYRIA_MODEL:-lyria-3.5}"
FRONTEND_URL="${FRONTEND_URL:-}"  # Set to deployed frontend URL after frontend deploy

if [ -z "$GEMINI_API_KEY" ]; then
  echo "ERROR: GEMINI_API_KEY is not set."
  echo "       Run: export GEMINI_API_KEY=your-key or set it in your .env"
  exit 1
fi

if [ -z "$FRONTEND_URL" ]; then
  echo "WARNING: FRONTEND_URL is not set. CORS will be restricted."
  echo "         Set it to your deployed frontend URL: export FRONTEND_URL=https://..."
fi

echo "=================================================="
echo "Deploying: ${SERVICE_NAME}"
echo "Project:   ${PROJECT_ID}"
echo "Region:    ${REGION}"
echo "Image:     ${IMAGE_NAME}"
echo "=================================================="

# ── Step 1: Configure Docker to push to Artifact Registry ─────────────────────
echo "[1/3] Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ── Step 2: Build and push image using Cloud Build ────────────────────────────
# Using Cloud Build avoids needing Docker installed locally.
echo "[2/3] Building and pushing image via Cloud Build..."
gcloud builds submit ./backend \
  --tag "${IMAGE_NAME}:latest" \
  --project "${PROJECT_ID}"

# ── Step 3: Deploy to Cloud Run ───────────────────────────────────────────────
echo "[3/3] Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}:latest" \
  --region "${REGION}" \
  --platform managed \
  --service-account "${RUNTIME_SA}" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars "GCS_TEMP_BUCKET=${GCS_TEMP_BUCKET}" \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --set-env-vars "GEMINI_MODEL=${GEMINI_MODEL}" \
  --set-env-vars "LYRIA_MODEL=${LYRIA_MODEL}" \
  --set-env-vars "FRONTEND_URL=${FRONTEND_URL}" \
  --set-env-vars "GCP_REGION=${REGION}" \
  --timeout 600 \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 10 \
  --min-instances 0 \
  --max-instances 10 \
  --allow-unauthenticated \
  --project "${PROJECT_ID}"

echo ""
echo "=================================================="
echo "Backend deployed!"
echo "Get the service URL with:"
echo "  gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)'"
echo "=================================================="
