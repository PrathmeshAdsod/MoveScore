# GCP Setup & Deployment Guide
## Agentic Cinema — Complete Step-by-Step Instructions

> This guide takes you from zero to a live, deployed Agentic Cinema application.
> Follow every section in order. Do not skip sections.
> Commands marked `# run this` should be run exactly as shown (after replacing placeholders).

---

## Section 1 — Prerequisites

### What you need installed locally

**1. Google Cloud CLI (gcloud)**
```bash
# Check if installed:
gcloud version

# If not installed, download from:
# https://cloud.google.com/sdk/docs/install
# After installing, initialize:
gcloud init
```

**2. Node.js (v20 or later)**
```bash
# Check:
node --version   # should show v20.x.x or higher
npm --version

# Install from: https://nodejs.org/
```

**3. Python (3.12)**
```bash
# Check:
python3 --version   # should show 3.12.x

# Install from: https://python.org/downloads/
```

**4. Git**
```bash
# Check:
git --version

# Install from: https://git-scm.com/
```

**5. FFmpeg (for local development and proof scripts)**
```bash
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install -y ffmpeg

# Check:
ffmpeg -version
```

**6. Docker (optional — only needed if building images locally)**
```bash
# Check:
docker --version

# Cloud Build (used in deployment scripts) doesn't require local Docker.
# Install from: https://docs.docker.com/get-docker/
```

---

## Section 2 — Google Authentication

You need two types of authentication:

| Type | Command | What it does |
|------|---------|--------------|
| **Account login** | `gcloud auth login` | Lets gcloud run commands as you |
| **Application Default** | `gcloud auth application-default login` | Lets Python code (your backend) call Google APIs locally |

**Run both:**
```bash
# 1. Log in to your Google account for gcloud commands:
gcloud auth login

# 2. Set up Application Default Credentials for local Python development:
gcloud auth application-default login
```

After running `gcloud auth application-default login`:
- A browser window opens
- Sign in with your Google account
- Credentials are saved to `~/.config/gcloud/application_default_credentials.json`
- Your local Python backend will automatically use these when running locally

**Important**: The deployed Cloud Run service does NOT use these credentials. It uses an attached service account (configured in Section 7).

---

## Section 3 — Create / Select GCP Project

Replace `YOUR_PROJECT_ID` with a unique ID for your project (lowercase letters, numbers, hyphens only).

```bash
# Set your project ID and region as shell variables.
# Replace these values:
PROJECT_ID=agentic-cinema-demo      # change this — must be globally unique
REGION=us-central1                  # recommended region for Gemini/Lyria

# Option A: Create a new project
gcloud projects create $PROJECT_ID --name="Agentic Cinema"

# Option B: Use an existing project
# (skip the create command above)

# Set this project as your active project:
gcloud config set project $PROJECT_ID

# Verify:
gcloud config get project
# Should print: agentic-cinema-demo (or your chosen ID)

# Also set your default region:
gcloud config set run/region $REGION
```

---

## Section 4 — Billing / Hackathon Credits

**This must be done manually in the Google Cloud Console.**

1. Go to: https://console.cloud.google.com/billing
2. Click **"Link a billing account"**
3. If you have hackathon credits: select the billing account associated with your credits
4. If you don't see hackathon credits: check your hackathon registration email for a coupon code, then redeem it at https://console.cloud.google.com/billing/credits

**Verify billing is active:**
```bash
gcloud beta billing projects describe $PROJECT_ID
# Look for: billingEnabled: true
```

**Note**: Without a linked billing account, the API enablement in Section 5 will fail.

---

## Section 5 — Enable Required APIs

These are the exact APIs required by this application:

```bash
# Enable all required APIs in one command:
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  generativelanguage.googleapis.com \
  iam.googleapis.com \
  --project $PROJECT_ID
```

**What each API does:**
- `run.googleapis.com` — Cloud Run (hosts your frontend and backend)
- `storage.googleapis.com` — Cloud Storage (temporary file storage)
- `artifactregistry.googleapis.com` — Docker image registry
- `cloudbuild.googleapis.com` — Builds Docker images without local Docker
- `aiplatform.googleapis.com` — Vertex AI (Gemini model access)
- `generativelanguage.googleapis.com` — Gemini API direct access
- `iam.googleapis.com` — IAM (service accounts and permissions)

**Verify:**
```bash
gcloud services list --enabled --project $PROJECT_ID | grep -E "run|storage|artifact|build|aiplatform|generative"
```

---

## Section 6 — GCS Bucket (Temporary Storage)

This bucket stores uploaded videos, generated audio, and final videos. Files auto-delete after 24 hours.

```bash
BUCKET_NAME=agentic-cinema-temp-$PROJECT_ID   # must be globally unique
# You can also just use: agentic-cinema-temp-<random>

# Create the bucket in your chosen region:
gcloud storage buckets create gs://$BUCKET_NAME \
  --location=$REGION \
  --uniform-bucket-level-access \
  --project $PROJECT_ID

# Write the lifecycle rule configuration:
cat > /tmp/lifecycle.json << 'EOF'
{
  "rule": [
    {
      "action": { "type": "Delete" },
      "condition": {
        "age": 1,
        "matchesStorageClass": ["STANDARD"]
      }
    }
  ]
}
EOF

# Apply the lifecycle rule:
gcloud storage buckets update gs://$BUCKET_NAME \
  --lifecycle-file=/tmp/lifecycle.json

# Verify the lifecycle rule:
gcloud storage buckets describe gs://$BUCKET_NAME \
  --format="value(lifecycle_config)"
```

**Note down your bucket name** — you'll need it in Section 10 (environment variables).

---

## Section 7 — Service Accounts and IAM

Create a dedicated service account for the backend Cloud Run service. This follows the principle of least privilege.

```bash
# Service account name for the backend
SA_NAME=movescore-backend-sa
SA_EMAIL=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com

# Create the service account:
gcloud iam service-accounts create $SA_NAME \
  --description="Agentic Cinema backend service account" \
  --display-name="Agentic Cinema Backend" \
  --project $PROJECT_ID

# Grant required roles:

# 1. Cloud Storage — read/write objects in the temp bucket
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

# 2. Vertex AI — access Gemini models via Vertex AI
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

# 3. Service Account Token Creator — REQUIRED for generating GCS signed URLs
#    Without this, signed URL generation will fail at runtime.
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator"

# 4. Cloud Run invoker (if backend needs to call other services)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker"

# Verify the service account was created:
gcloud iam service-accounts describe $SA_EMAIL --project $PROJECT_ID
```

**Why each role is needed:**
| Role | Why |
|------|-----|
| `roles/storage.objectAdmin` | Upload videos, audio, final MP4 to GCS; generate signed URLs |
| `roles/aiplatform.user` | Call Gemini models via Vertex AI |
| `roles/iam.serviceAccountTokenCreator` | Sign GCS signed URLs (V4 signing requires this) |
| `roles/run.invoker` | Allows the service to invoke other Cloud Run services if needed |

---

## Section 8 — Gemini Access

The application uses the Gemini API directly (not through Vertex AI endpoint), authenticated via an API key.

**Step 1: Get a Gemini API key**
1. Go to: https://aistudio.google.com/apikey
2. Click **"Create API key"**
3. Select your project: `$PROJECT_ID`
4. Copy the key — you will need it in Section 10

**Step 2: Verify the model ID**
1. Go to: https://ai.google.dev/gemini-api/docs/models
2. Find the current `gemini-2.5-flash` model ID (it may have a version suffix like `-001`)
3. Update `GEMINI_MODEL` in your `.env` if the exact ID differs

**Step 3: Test Gemini access locally**
```bash
# From the backend directory, after setting up your .env:
cd backend
source .venv/bin/activate

# Quick test:
python3 -c "
import os
from google import genai
from google.genai import types

client = genai.Client(api_key='YOUR_API_KEY_HERE')
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Say hello in 5 words.',
)
print(response.text)
"
```

If this prints a short greeting, Gemini is working.

---

## Section 9 — Lyria Access

**This is the most critical section. Complete it before running any proof scripts.**

### Step 1: Check Lyria availability
1. Go to: https://ai.google.dev/gemini-api/docs/music-generation
2. Read the current access requirements
3. Check whether Lyria requires separate enrollment or is available with a standard Gemini API key

### Step 2: Verify the current model ID
1. The current model may be `lyria-002`, `lyria-3.5`, or another ID
2. Check the official docs linked above for the exact current model string
3. Update `LYRIA_MODEL` in your `.env` with the verified ID

### Step 3: Check quota
1. Go to: https://console.cloud.google.com/iam-admin/quotas
2. Filter by: "Generative Language API"
3. Look for Lyria-related quotas
4. Note the requests-per-minute limit — important for demo day

### Step 4: Accept terms of service (if required)
Some Lyria models require explicit acceptance of terms before generation works.
1. Go to: https://aistudio.google.com/
2. Navigate to the music generation section (if available)
3. Accept any additional terms presented for music generation

### Step 5: Test Lyria generation
After running the backend proof scripts (Section 12), run:
```bash
cd backend
source .venv/bin/activate
python3 scripts/proof_lyria_generation.py
```
This will generate a short MP3 using a test prompt.
Listen to the output file `test_output_music.mp3` to verify it worked.

### Step 6: Verify vocal support
If you want to use "Song / Vocals" output type:
1. Check current docs for whether vocal generation is supported
2. If not, the UI will still show the option, but set `output_type: "instrumental"` as default

---

## Section 10 — Environment Configuration

### Backend `.env` file
```bash
cd agentic-cinema/backend
cp ../.env.example .env
```

Edit `.env` and fill in your values:

```bash
# Replace each value:

GOOGLE_CLOUD_PROJECT_ID=agentic-cinema-demo   # your project ID from Section 3
GCS_TEMP_BUCKET=agentic-cinema-temp-xxx       # your bucket name from Section 6
GCP_REGION=us-central1

GEMINI_API_KEY=AIza...                        # your API key from Section 8
GEMINI_MODEL=gemini-2.5-flash                 # verify exact ID in Section 8

LYRIA_MODEL=lyria-002                         # verify exact ID in Section 9

PORT=8080
FRONTEND_URL=http://localhost:3000            # update after deploying frontend
MAX_VIDEO_SIZE_MB=100
SIGNED_URL_TTL_HOURS=1
```

### Frontend `.env.local` file
```bash
cd agentic-cinema/frontend
echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:8080" > .env.local
```

---

## Section 11 — Local Development

### Backend

```bash
cd agentic-cinema/backend

# Create and activate a virtual environment:
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# On Windows: .venv\Scripts\activate

# Install dependencies:
pip install -r requirements.txt

# Verify installation:
python3 -c "import fastapi; import google.genai; print('OK')"

# Run the backend server:
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# The API will be available at:
# http://localhost:8080
# API docs: http://localhost:8080/docs
```

### Frontend

```bash
cd agentic-cinema/frontend

# Install dependencies:
npm install

# Run the development server:
npm run dev

# The app will be available at:
# http://localhost:3000
```

### Run both simultaneously

Open two terminal windows:
- Terminal 1: run the backend (port 8080)
- Terminal 2: run the frontend (port 3000)

The frontend reads `NEXT_PUBLIC_BACKEND_URL=http://localhost:8080` from `.env.local`.

---

## Section 12 — Test the Local End-to-End Flow

Follow this checklist in order. Complete each step before the next.

### Prerequisites
- [ ] Backend is running on port 8080
- [ ] Frontend is running on port 3000
- [ ] `.env` is filled in with real values
- [ ] You have a 10–20 second dance video file (MP4)

### Step A: Run the proof scripts first (recommended)

```bash
cd agentic-cinema/backend
source .venv/bin/activate

# Proof 1 — Gemini choreography analysis:
python3 scripts/proof_gemini_analysis.py /path/to/your/dance_video.mp4

# Expected output:
# ✅ SUCCESS! Choreography analysis complete.
# X movement moments detected
# Intro → Hit → ...
# Full JSON saved to: dance_video_choreography.json

# Proof 2 — Lyria music generation:
python3 scripts/proof_lyria_generation.py dance_video_choreography.json

# Expected output:
# ✅ SUCCESS! Music generated.
# Output: ./test_output_music.mp3
# Listen to the file to verify it sounds correct.

# Proof 3 — Full end-to-end pipeline:
python3 scripts/proof_end_to_end.py /path/to/your/dance_video.mp4 \
  --style Afrobeat --mood Euphoric

# Expected output:
# ✅ END-TO-END PIPELINE COMPLETE
# Final video signed URL: https://...
# Open the URL in a browser to preview.
```

### Step B: Test the web application

1. **Open** http://localhost:3000
2. **Verify landing page** loads correctly (headline, CTA, workflow comparison)
3. **Click "Start Creating →"** — should navigate to `/create`
4. **Upload video**: drag-and-drop or click to upload your dance video
   - Video preview should appear immediately
   - If this fails: check backend logs for upload errors
5. **Select preferences**: choose Style, Mood, Energy, Movement Feel
6. **Click "Generate Music →"**
   - Status should show: "Analyzing choreography..."
   - After 15–30s: analysis result should appear (`X movement moments detected`)
   - Then: music generation (~30–60s)
   - Then: "Preparing your video..."
7. **Verify final video plays** with the generated soundtrack
8. **Download**: click "↓ Download Video" — should download the MP4
9. **Generate Again**: click "↺ Generate Again" — should reuse choreography, re-generate music

### Debugging common issues

```bash
# View backend logs:
# (with the backend running in a terminal, logs appear there)

# Check if backend is responding:
curl http://localhost:8080/health
# Expected: {"status":"ok","version":"1.0.0"}

# Check CORS headers (from frontend origin):
curl -H "Origin: http://localhost:3000" -I http://localhost:8080/health

# Check GCS access:
gcloud storage ls gs://$GCS_TEMP_BUCKET

# Check Gemini API key:
python3 -c "
from config import settings
print('Key set:', bool(settings.gemini_api_key))
print('Model:', settings.gemini_model)
"

# If signed URLs fail — check service account token creator permission:
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/iam.serviceAccountTokenCreator"
```

---

## Section 13 — Artifact Registry

Artifact Registry stores your Docker images for Cloud Run deployment.

```bash
# Create the Docker repository:
gcloud artifacts repositories create agentic-cinema \
  --repository-format=docker \
  --location=$REGION \
  --description="Agentic Cinema Docker images" \
  --project $PROJECT_ID

# Configure Docker to authenticate with Artifact Registry:
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Verify the repository was created:
gcloud artifacts repositories list --location=$REGION --project $PROJECT_ID
```

---

## Section 14 — Deploy Backend to Cloud Run

**Before deploying:**
- [ ] Section 7 (service account) is complete
- [ ] Section 13 (Artifact Registry) is complete
- [ ] `.env` values are confirmed correct
- [ ] Proof scripts passed locally

```bash
# Set your environment variables:
export PROJECT_ID=agentic-cinema-demo        # your project ID
export REGION=us-central1
export GCS_TEMP_BUCKET=agentic-cinema-temp-xxx
export GEMINI_API_KEY=AIza...               # your Gemini API key
export GEMINI_MODEL=gemini-2.5-flash
export LYRIA_MODEL=lyria-002
export RUNTIME_SA=movescore-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Run the deploy script:
cd agentic-cinema
chmod +x scripts/deploy-backend.sh
./scripts/deploy-backend.sh
```

**After deployment:**
```bash
# Get the backend URL:
BACKEND_URL=$(gcloud run services describe movescore-backend \
  --region $REGION \
  --format='value(status.url)' \
  --project $PROJECT_ID)

echo "Backend URL: $BACKEND_URL"
# Save this URL — you need it for the frontend deployment.

# Verify the backend is healthy:
curl $BACKEND_URL/health
# Expected: {"status":"ok","version":"1.0.0"}
```

**Note down the backend URL** (e.g. `https://movescore-backend-abc123-uc.a.run.app`).

---

## Section 15 — Deploy Frontend to Cloud Run

**The frontend must know the backend URL at build time** (Next.js bakes it in via `NEXT_PUBLIC_BACKEND_URL`).

```bash
# Set the backend URL (from Section 14):
export BACKEND_URL=https://movescore-backend-abc123-uc.a.run.app   # replace with real URL

# Deploy the frontend:
cd agentic-cinema
chmod +x scripts/deploy-frontend.sh
./scripts/deploy-frontend.sh
```

**After deployment:**
```bash
# Get the frontend URL:
FRONTEND_URL=$(gcloud run services describe movescore-frontend \
  --region $REGION \
  --format='value(status.url)' \
  --project $PROJECT_ID)

echo "Frontend URL: $FRONTEND_URL"
# This is your live application URL.
```

---

## Section 16 — CORS / Frontend-Backend Connectivity

The backend only accepts requests from the configured `FRONTEND_URL`. After deploying the frontend, update the backend with the real frontend URL:

```bash
# Update the backend CORS setting with the real frontend URL:
gcloud run services update movescore-backend \
  --region $REGION \
  --update-env-vars "FRONTEND_URL=${FRONTEND_URL}" \
  --project $PROJECT_ID
```

**How it works:**
- `FRONTEND_URL` in `main.py` becomes the only allowed CORS origin
- The backend rejects requests from any other origin in production
- Wildcard `*` is NOT used

**Verify CORS is working:**
```bash
# Test a preflight request from the frontend origin:
curl -X OPTIONS \
  -H "Origin: ${FRONTEND_URL}" \
  -H "Access-Control-Request-Method: POST" \
  ${BACKEND_URL}/run-agent \
  -I
# Should see: access-control-allow-origin: <your frontend URL>
```

---

## Section 17 — Production Verification

Run these checks after both services are deployed:

```bash
# 1. Check Cloud Run service statuses:
gcloud run services list --region $REGION --project $PROJECT_ID

# 2. Check backend health:
curl ${BACKEND_URL}/health

# 3. View backend logs (last 50 lines):
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=movescore-backend" \
  --limit=50 \
  --project $PROJECT_ID

# 4. View frontend logs:
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=movescore-frontend" \
  --limit=20 \
  --project $PROJECT_ID

# 5. Verify GCS bucket is accessible from backend:
# Upload a test file to verify permissions:
echo "test" | gcloud storage cp - gs://$GCS_TEMP_BUCKET/test.txt
gcloud storage ls gs://$GCS_TEMP_BUCKET/
gcloud storage rm gs://$GCS_TEMP_BUCKET/test.txt

# 6. Open the frontend in a browser:
echo "Open: $FRONTEND_URL"
```

---

## Section 18 — Demo Readiness Checklist

Go through this list before your hackathon demo:

- [ ] Frontend URL is live and accessible: `$FRONTEND_URL`
- [ ] Backend health check passes: `curl $BACKEND_URL/health`
- [ ] Landing page loads correctly (headline, CTA, workflow comparison)
- [ ] `/create` page loads correctly
- [ ] Video upload works (test with your demo clip)
- [ ] Gemini analysis completes and shows movement summary
- [ ] Lyria generation completes and produces audible music
- [ ] FFmpeg combine produces a working downloadable MP4
- [ ] Download button works
- [ ] "Generate Again" works (preserves choreography, generates new music)
- [ ] Lyria quota is sufficient (check before demo — pre-generate if unsure)
- [ ] Demo dance clip is ready (10–20 seconds, good lighting, clear movement)
- [ ] You've done a full run-through of the demo at least once
- [ ] IBM Bob development evidence is documented in README.md
- [ ] Git repository is clean (no .env files, no service-account.json)
- [ ] GitHub repository is public (or accessible to judges)
- [ ] README.md is complete with all required sections
- [ ] Demo recording is ready as a backup

**Pre-generate demo audio (optional backup):**
If Lyria quota is limited, generate your demo audio the day before and keep the final video ready as a local backup. This ensures your demo runs smoothly even under quota pressure.

---

## Section 19 — Cost and Cleanup

### Expected costs during development / hackathon
- **Cloud Run**: scales to zero — no cost when idle
- **Cloud Storage**: minimal (small files, short retention)
- **Gemini API**: pay-per-token; choreography analysis + music plan per run
- **Lyria**: per-generation cost — check current pricing
- **Artifact Registry**: minimal storage cost for Docker images
- **Cloud Build**: per-build minute

### Cleanup after the hackathon

> ⚠️ **DO NOT RUN THESE COMMANDS UNTIL YOU WANT TO PERMANENTLY DELETE YOUR PROJECT RESOURCES.**

```bash
# Delete Cloud Run services:
gcloud run services delete movescore-backend --region $REGION --project $PROJECT_ID --quiet
gcloud run services delete movescore-frontend --region $REGION --project $PROJECT_ID --quiet

# Delete Artifact Registry repository (and all Docker images):
gcloud artifacts repositories delete agentic-cinema \
  --location=$REGION --project $PROJECT_ID --quiet

# Delete GCS bucket and all contents:
gcloud storage rm -r gs://$GCS_TEMP_BUCKET

# Delete service account:
gcloud iam service-accounts delete \
  movescore-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --project $PROJECT_ID --quiet

# Optionally delete the entire project (IRREVERSIBLE):
# gcloud projects delete $PROJECT_ID
```

---

*Generated with IBM Bob (Plan Mode). See README.md for project overview.*
