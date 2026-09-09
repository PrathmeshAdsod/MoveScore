# GCP Setup & Deployment Guide
## MoveScore — Production Guide for Gemini Enterprise Agent Platform

> This guide contains verified, end-to-end instructions to configure Google Cloud Platform, set up least-privilege IAM security, deploy to **Gemini Enterprise Agent Platform (Agent Runtime)**, and run MoveScore in production.
> 
> **Do not skip sections.** Execute each command in order in your bash/zsh shell.

---

## Architecture & Authentication Overview

MoveScore uses a clean, least-privilege enterprise architecture:

```
[Browser Client]
       │
       ▼ (1) Upload Video (validated ≤ 60s via ffprobe)
[FastAPI on Cloud Run] ──► Uploads to GCS (video_gcs_uri)
       │
       ▼ (2) Orchestrate Pipeline (video_gcs_uri, preferences)
[Gemini Enterprise Agent Runtime (Agent Engine ReasoningEngine)]
   • Step 1: analyze_choreography (Gemini 3.8 Flash via Files API)
   • Step 2: plan_music (Gemini 3.8 Flash text reasoning)
   • Step 3: generate_music (Lyria 3.5 via Interactions API, uploads MP3 to GCS)
   ◄── Returns structured JSON: {choreography_json, choreography_summary, music_prompt, audio_gcs_uri}
       │
       ▼ (3) Deterministic Media Processing (Local on Cloud Run)
[FastAPI on Cloud Run]
   • Step 4: combine_media via local FFmpeg (H.264/yuv420p + AAC)
   • Step 5: Generates V4 Signed URL via Cloud Run ADC + IAM Credentials API
       │
       ▼
[Browser Client: Video Preview & Download]
```

### Authentication Model Matrix
| Component | Credential Type | Purpose | IAM Scope / API |
| :--- | :--- | :--- | :--- |
| **Gemini 3.8 Flash & Lyria 3.5** | `GEMINI_API_KEY` (Secret Manager) | Multimodal video analysis & Lyria Interactions API | Stored in Secret Manager `gemini-api-key`, mounted as env var in Cloud Run |
| **Cloud Run Backend** | Attached Service Account (ADC) | GCS bucket reads/writes & V4 Signed URL generation | `roles/storage.objectAdmin` (bucket level), `roles/iam.serviceAccountTokenCreator` (on SA self) |
| **Cloud Run Backend -> Agent Runtime** | Attached Service Account (ADC) | Calling Agent Runtime Reasoning Engine | `roles/aiplatform.user` (project level) |
| **Agent Runtime Agent Identity** | Agent Identity SA | Downloading video & uploading generated MP3 | `roles/storage.objectAdmin` (bucket level) |

---

## Section 1 — Prerequisites & Local Setup

### Local Tools
1. **Google Cloud CLI (`gcloud`)**:
   ```bash
   gcloud version
   # If not installed: https://cloud.google.com/sdk/docs/install
   ```
2. **Node.js (v20+) & npm**:
   ```bash
   node --version
   npm --version
   ```
3. **Python (3.11 or 3.12)**:
   ```bash
   python3 --version
   ```
4. **FFmpeg & ffprobe**:
   ```bash
   ffmpeg -version
   ffprobe -version
   # Ubuntu/Debian: sudo apt-get install -y ffmpeg
   # macOS: brew install ffmpeg
   ```

---

## Section 2 — GCP Project, Billing & Authentication

### 1. Set Project Variables
```bash
export PROJECT_ID="your-gcp-project-id"   # Replace with your actual project ID
export REGION="us-central1"
export GCS_TEMP_BUCKET="movescore-temp-${PROJECT_ID}"
export RUNTIME_SA="movescore-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Set default project and region for gcloud
gcloud config set project "${PROJECT_ID}"
gcloud config set run/region "${REGION}"
```

### 2. Verify Billing & Credits
Ensure billing is active on your project (required for Cloud Run, Cloud Build, and Vertex AI):
```bash
gcloud beta billing projects describe "${PROJECT_ID}"
```

### 3. Authenticate CLI
```bash
# Authenticate your personal user account for gcloud commands
gcloud auth login

# Set up local Application Default Credentials (ADC) for local Python testing
gcloud auth application-default login
```

---

## Section 3 — Enable Required Google APIs

Enable only the services strictly required by MoveScore:
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  iamcredentials.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  --project "${PROJECT_ID}"
```

Verification:
```bash
gcloud services list --enabled --filter="name:(run artifactregistry cloudbuild storage iamcredentials secretmanager aiplatform)"
```

---

## Section 4 — Gemini & Lyria API Key in Secret Manager

The application uses `gemini-3.8-flash` for multimodal analysis/planning and `lyria-3.5` for music generation.

### 1. Obtain your Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/apikey).
2. Create an API key associated with your project `${PROJECT_ID}`.

### 2. Store Key in Secret Manager
Do **not** commit keys or deploy them in plaintext environment variable commands. Store in Secret Manager:
```bash
echo -n "YOUR_ACTUAL_GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
  --data-file=- \
  --replication-policy="automatic" \
  --project "${PROJECT_ID}"
```

---

## Section 5 — Cloud Storage Bucket & 24-Hour Lifecycle

Create the temporary bucket with an automatic 24-hour expiration policy:

### 1. Create Bucket
```bash
gcloud storage buckets create "gs://${GCS_TEMP_BUCKET}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --uniform-bucket-level-access
```

### 2. Set 24-Hour Auto-Delete Lifecycle Policy
Create a lifecycle configuration file `gcs-lifecycle.json`:
```bash
cat << 'EOF' > gcs-lifecycle.json
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 1}
    }
  ]
}
EOF

gcloud storage buckets update "gs://${GCS_TEMP_BUCKET}" --lifecycle-file=gcs-lifecycle.json
rm gcs-lifecycle.json
```

Verify lifecycle:
```bash
gcloud storage buckets describe "gs://${GCS_TEMP_BUCKET}" --format="json(lifecycle)"
```

---

## Section 6 — Service Accounts & Least-Privilege IAM Setup

MoveScore follows Google Cloud's least-privilege security model.

### 1. Create Backend Cloud Run Service Account
```bash
gcloud iam service-accounts create movescore-backend-sa \
  --display-name="MoveScore Backend Cloud Run SA" \
  --project="${PROJECT_ID}"
```

### 2. Grant Bucket Storage Permissions (Scoped to Bucket Only)
Grant `roles/storage.objectAdmin` **only** on the temp bucket, not project-wide:
```bash
gcloud storage buckets add-iam-policy-binding "gs://${GCS_TEMP_BUCKET}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/storage.objectAdmin"
```

### 3. Grant Token Creator for V4 Signed URLs via ADC (Without Private Keys)
To allow Cloud Run to generate V4 signed URLs using Application Default Credentials (via the IAM Credentials `signBlob` API), the service account must have `roles/iam.serviceAccountTokenCreator` on **itself**:
```bash
gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SA}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="${PROJECT_ID}"
```

### 4. Grant Secret Manager Access
Allow the service account to read the Gemini API key secret:
```bash
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project="${PROJECT_ID}"
```

### 5. Grant Vertex AI / Agent Runtime User Access
Allow the service account to invoke Agent Runtime Reasoning Engines:
```bash
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/aiplatform.user"
```

*(Note: We deliberately do **not** grant `roles/run.invoker` or broad project editor roles. Permissions are strictly scoped).*

---

## Section 7 — Local Testing & Model Proofs

Before deploying to the cloud, verify that your models work locally:

```bash
cd backend
cp ../.env.example .env
```
Edit `.env` and configure:
```ini
GOOGLE_CLOUD_PROJECT_ID=your-gcp-project-id
GCS_TEMP_BUCKET=movescore-temp-your-gcp-project-id
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash
LYRIA_MODEL=lyria-3.5
```

### Test 1: Video Analysis Proof (`gemini-3.8-flash`)
```bash
python scripts/proof_gemini_analysis.py path/to/sample_dance.mp4
```
Expected: Prints structured choreography moments, tempo, and confidence.

### Test 2: Lyria 3.5 Music Generation Proof (`lyria-3.5`)
```bash
python scripts/proof_lyria_generation.py
```
Expected: Generates `./test_output_music.mp3` via Gemini Interactions API.

---

## Section 8 — Artifact Registry Setup

Create the Docker repository for Cloud Run images:
```bash
gcloud artifacts repositories create agentic-cinema \
  --repository-format=docker \
  --location="${REGION}" \
  --description="MoveScore Docker repository" \
  --project="${PROJECT_ID}"
```

---

## Section 9 — Deploy to Gemini Enterprise Agent Platform (Agent Runtime)

Deploy the static MoveScore ADK agent wrapped with `AdkApp` as a Vertex AI Reasoning Engine resource:

```bash
cd ..  # return to repo root
python scripts/deploy-agent-runtime.py
```

This outputs your deployed resource:
```
SUCCESS: Agent successfully deployed to Agent Runtime!
Reasoning Engine Resource: projects/PROJECT_NUMBER/locations/us-central1/reasoningEngines/REASONING_ENGINE_ID
```
Copy this resource string; you will pass it to the backend deployment as `AGENT_ENGINE_RESOURCE_NAME`.

---

## Section 10 — Deploy Backend to Cloud Run

Deploy the FastAPI backend container to Cloud Run using Cloud Build:

```bash
./scripts/deploy-backend.sh
```

Or deploy manually via gcloud:
```bash
export IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/agentic-cinema/movescore-backend:latest"

# Build image using Cloud Build
gcloud builds submit ./backend --tag "${IMAGE_NAME}" --project "${PROJECT_ID}"

# Deploy to Cloud Run
gcloud run deploy movescore-backend \
  --image "${IMAGE_NAME}" \
  --region "${REGION}" \
  --platform managed \
  --service-account "${RUNTIME_SA}" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars "GCS_TEMP_BUCKET=${GCS_TEMP_BUCKET}" \
  --set-env-vars "GEMINI_MODEL=gemini-3.8-flash" \
  --set-env-vars "LYRIA_MODEL=lyria-3.5" \
  --set-env-vars "GCP_REGION=${REGION}" \
  --set-env-vars "SERVICE_ACCOUNT_EMAIL=${RUNTIME_SA}" \
  --set-env-vars "AGENT_ENGINE_RESOURCE_NAME=${AGENT_ENGINE_RESOURCE_NAME}" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest" \
  --timeout 600 \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 10 \
  --allow-unauthenticated \
  --project "${PROJECT_ID}"
```

Obtain the backend URL:
```bash
BACKEND_URL=$(gcloud run services describe movescore-backend --region "${REGION}" --format="value(status.url)")
echo "Backend URL: ${BACKEND_URL}"
```

Verify backend health:
```bash
curl -f "${BACKEND_URL}/health"
# Returns: {"status":"ok","version":"1.0.0"}
```

---

## Section 11 — Deploy Frontend to Cloud Run

The Next.js frontend builds with the deployed `BACKEND_URL` baked into its client bundles.

```bash
export BACKEND_URL="${BACKEND_URL}"
./scripts/deploy-frontend.sh
```

Obtain the frontend URL:
```bash
FRONTEND_URL=$(gcloud run services describe movescore-frontend --region "${REGION}" --format="value(status.url)")
echo "Frontend URL: ${FRONTEND_URL}"
```

---

## Section 12 — Configure CORS on Backend

Now that the frontend is live, lock down backend CORS strictly to the deployed frontend domain:

```bash
gcloud run services update movescore-backend \
  --region "${REGION}" \
  --update-env-vars "FRONTEND_URL=${FRONTEND_URL}" \
  --project "${PROJECT_ID}"
```

---

## Section 13 — Production Smoke Tests

### Test 1: Health Check
```bash
curl -i "${BACKEND_URL}/health"
```

### Test 2: Upload Video & Duration Validation
Upload a valid MP4 (<60s):
```bash
curl -i -X POST "${BACKEND_URL}/upload" \
  -F "file=@path/to/short_dance.mp4"
```
Verify response includes `gcs_uri` and `preview_signed_url`.

### Test 3: Duration Rejection Test (>60s)
Upload a test file longer than 60 seconds:
```bash
curl -i -X POST "${BACKEND_URL}/upload" \
  -F "file=@path/to/long_video_70s.mp4"
```
Verify response is HTTP 400:
```json
{"detail":"Video duration is 70.0s. Maximum supported duration is 60 seconds."}
```

### Test 4: End-to-End Pipeline Execution
```bash
curl -i -X POST "${BACKEND_URL}/run-agent" \
  -H "Content-Type: application/json" \
  -d '{
    "gcs_uri": "'"${GCS_URI}"'",
    "user_preferences": {
      "style": "Afrobeat",
      "mood": "Euphoric",
      "energy": "high",
      "output_type": "instrumental"
    }
  }'
```
Verify response returns `final_video_signed_url`, `choreography_summary`, and `music_prompt`.

---

## Section 14 — Logs & Debugging

Stream real-time production logs:

```bash
# Backend logs
gcloud beta run services logs tail movescore-backend --region "${REGION}"

# Agent Runtime logs
gcloud logging read "resource.type=aiplatform.googleapis.com/ReasoningEngine" --limit 50 --format="json"
```

---

## Section 15 — Cleanup Instructions

To avoid ongoing cloud charges after testing or demonstration:

```bash
# Delete Cloud Run services
gcloud run services delete movescore-frontend --region "${REGION}" --quiet
gcloud run services delete movescore-backend --region "${REGION}" --quiet

# Delete Artifact Registry images
gcloud artifacts repositories delete agentic-cinema --location "${REGION}" --quiet

# Delete GCS bucket
gcloud storage rm -r "gs://${GCS_TEMP_BUCKET}"

# Delete Secret
gcloud secrets delete gemini-api-key --quiet

# Delete Service Account
gcloud iam service-accounts delete "${RUNTIME_SA}" --quiet
```
