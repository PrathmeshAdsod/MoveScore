#!/usr/bin/env bash
# =============================================================================
# deploy-frontend.sh — Build and deploy the Next.js frontend to Cloud Run
#
# IMPORTANT: Run deploy-backend.sh FIRST and get the backend URL before
# running this script. The backend URL is baked into the Next.js build.
#
# Usage:
#   BACKEND_URL=https://movescore-backend-xxxx-uc.a.run.app ./scripts/deploy-frontend.sh
#
# DO NOT EXECUTE THIS YOURSELF — read GCP_SETUP_AND_DEPLOY.md first.
# =============================================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="movescore-frontend"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/agentic-cinema/${SERVICE_NAME}"

# BACKEND_URL must be set to the deployed backend Cloud Run URL
BACKEND_URL="${BACKEND_URL:-}"

if [ -z "$BACKEND_URL" ]; then
  echo "ERROR: BACKEND_URL is not set."
  echo "       Run deploy-backend.sh first, then:"
  echo "       export BACKEND_URL=https://movescore-backend-xxxx-uc.a.run.app"
  exit 1
fi

echo "=================================================="
echo "Deploying: ${SERVICE_NAME}"
echo "Project:   ${PROJECT_ID}"
echo "Region:    ${REGION}"
echo "Backend:   ${BACKEND_URL}"
echo "=================================================="

# ── Step 1: Configure Docker ───────────────────────────────────────────────────
echo "[1/3] Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ── Step 2: Build with Cloud Build (passes BACKEND_URL as build arg) ──────────
echo "[2/3] Building and pushing image via Cloud Build..."
gcloud builds submit ./frontend \
  --tag "${IMAGE_NAME}:latest" \
  --build-arg "NEXT_PUBLIC_BACKEND_URL=${BACKEND_URL}" \
  --project "${PROJECT_ID}"

# ── Step 3: Deploy to Cloud Run ───────────────────────────────────────────────
echo "[3/3] Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}:latest" \
  --region "${REGION}" \
  --platform managed \
  --set-env-vars "NEXT_PUBLIC_BACKEND_URL=${BACKEND_URL}" \
  --timeout 60 \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10 \
  --allow-unauthenticated \
  --project "${PROJECT_ID}"

echo ""
echo "=================================================="
echo "Frontend deployed!"
echo ""
echo "IMPORTANT: Now update the backend with the frontend URL for CORS:"
FRONTEND_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --format='value(status.url)' \
  --project "${PROJECT_ID}")
echo ""
echo "Frontend URL: ${FRONTEND_URL}"
echo ""
echo "Run this to update the backend CORS setting:"
echo "  gcloud run services update movescore-backend \\"
echo "    --region ${REGION} \\"
echo "    --update-env-vars FRONTEND_URL=${FRONTEND_URL} \\"
echo "    --project ${PROJECT_ID}"
echo "=================================================="
