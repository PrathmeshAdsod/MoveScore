# Agentic Cinema — Choreography-First Music Generator
## Plan File · IBM Bob Hackathon Project

> **Positioning**: Dance first. Music second.
> Upload your choreography. Get original music composed around your movement.

---

## Top-Level Overview

**Goal**: A single-session web app where short-form creators upload a dance video, an AI agent analyzes the movement, composes original music around the choreography structure, and delivers a downloadable final video — with no login, no history, no manual editing.

**Core innovation**: Choreography determines timing and musical structure. User preferences determine creative direction. Lyria composes the soundtrack.

**Non-goals**: Social feed, DAW, timeline editor, accounts, millisecond-perfect beat matching, unnecessary microservices.

---

## Implementation Priority (Prove Before Building)

Before building upload UI, storage, or the full web app, validate the two core product risks first:

```
A. Prove Gemini choreography analysis works on a real 10–15s dance clip
B. Prove Lyria is accessible and generates audio for a test prompt
C. Prove choreography-to-music prompting produces musically sensible output
D. Get one hardcoded end-to-end sample working (script, no UI)
E. Then build upload / UI / storage / polish
```

This sequencing prevents discovering blocking model issues late in development.

---

## ⚠️ Verified Constraints & Honest Unknowns

> Items marked ⚠️ MUST BE VERIFIED in your account/console before the relevant sub-task begins.
> The user has confirmed the information below from official documentation linked in the planning session.

### Gemini Model
- **Model ID**: `gemini-3.8-flash` (confirmed GA by user from `ai.google.dev/gemini-api/docs/models/gemini-3.8-flash`)
- **Capabilities confirmed**: video input (multimodal), structured outputs (`response_schema`), agentic workflows
- **Video input method**: Gemini Files API (recommended for backend/server use); inline base64 acceptable for small files
- **Video frame sampling**: Gemini processes video at approximately **1 FPS**. This is a known limitation — very fast dance movements lasting less than ~1 second may be missed between sampled frames.
  - **MVP approach**: Test native video analysis first (Sub-task 1). If fast choreography is missed, the smallest fallback is to upload an **analysis-only slowed version** of the clip (e.g. 0.5× speed). Do NOT add computer-vision infrastructure preemptively.
- **Structured output**: Use `response_schema` for strict ChoreographySchema JSON output
- ⚠️ **Verify exact model ID string** (may have a version suffix, e.g. `gemini-3.8-flash-001`) in your Google AI Studio or Vertex AI console before Sub-task 2

### Lyria (Music Generation)
- **Access method**: Lyria is accessible through the **Gemini API / `google-genai` SDK** (NOT a separate MusicFX API)
- **Authentication**: Uses the same Gemini API key — no separate Lyria key or endpoint
- **Current model**: ⚠️ Prefer `lyria-3.5` if accessible in your account; verify exact model ID in your console before hardcoding
- **Confirmed capabilities** (user-verified from `ai.google.dev/gemini-api/docs/music-generation`):
  - Instrumental music ✅
  - Vocals / song generation ✅
  - BPM / tempo instructions ✅
  - Mood, genre, instrumentation ✅
  - Song structure ✅
  - **Timestamp-based musical instructions** ✅ (e.g. `[0:00-0:04] restrained intro`)
  - MP3 output ✅
  - Full musical arrangements ✅
- **Timestamp instructions are musical directions, not sample-accurate sync guarantees.** Product copy must reflect this.
- ⚠️ **Max duration**: Verify current maximum generated audio duration from official docs before Sub-task 5
- ⚠️ **Vocals**: Confirm whether song/vocal generation requires a specific parameter or model variant
- ⚠️ **Quota**: Note your account's Lyria quota before demo day

### Agent / Hackathon Compliance
- The Agentic Cinema hackathon requires a **functional AI agent or multi-agent network** powered by Gemini and Google Cloud Agent Builder (user-confirmed from `agentic-cinema.devpost.com/rules`)
- **IBM track**: Genuine IBM Bob usage during development satisfies the IBM partner requirement. Confluent is optional. (User-confirmed from hackathon forum)
- **Implementation**: Use **Google ADK (Agent Development Kit)** to build a single deterministic workflow agent that orchestrates the pipeline. A single orchestrating agent is compliant — fake multi-agent sprawl is explicitly avoided.
- **Backend language**: Python / FastAPI. Python is chosen because it is the simplest path for this implementation (ADK SDK, `google-genai`, and FFmpeg subprocess are all straightforward in Python). ADK itself does not inherently require Python — this is an implementation choice.

### Authentication & Credentials
- **Deployed Cloud Run**: Use an **attached service account with Application Default Credentials (ADC)**. Do not rely on a downloaded JSON key file in the deployed container. Set the Cloud Run service account to have the required IAM roles.
- **Local development**: Use `gcloud auth application-default login` or a locally exported JSON key (never committed). Document this separately in README local setup.
- **GCS Signed URLs**: Generating signed URLs requires the signing service account to have the `iam.serviceAccounts.signBlob` permission (the `Service Account Token Creator` role). Verify this is assigned to the Cloud Run service account during setup (Sub-task 2) — missing this is a common deployment blocker.

### Google Cloud Storage
- Object lifecycle deletion: Supported — configure 24-hour delete rule on temp bucket
- Signed URLs: Supported — configurable TTL (use ~1 hour for final download link)
- Signing IAM requirement: Service account needs `roles/iam.serviceAccountTokenCreator`

### Cloud Run
- Max request timeout: **60 minutes** (configurable; default 15 min — must be set to 600s)
- Max HTTP response body: **32 MB** — final video must NOT be returned as response body; use GCS signed URL
- `/tmp` disk space: **~450 MB** — sufficient for short video processing
- Memory: default 256 MB; increase if FFmpeg combine step requires it
- FFmpeg: installable in Dockerfile (`apt-get install -y ffmpeg`)

---

## What Changed From Previous Plan (Revision Summary)

| Area | Old Plan | Revised Plan |
|------|----------|--------------|
| Gemini model | `gemini-1.5-pro` | `gemini-3.8-flash` |
| Video input to Gemini | GCS URI passed directly | Gemini Files API (backend upload) |
| Lyria access | Separate MusicFX API + `LYRIA_API_ENDPOINT` + `LYRIA_API_KEY` | Gemini API key only via `google-genai` SDK |
| Lyria capabilities | Uncertain / mostly instrumental | Confirmed: vocals, BPM, timestamps, structure, MP3 |
| Music plan output | Natural language only | Natural language with timestamp markers (e.g. `[0:04]`) |
| Agent / hackathon compliance | No agent; plain pipeline | Google ADK single workflow agent (hackathon requirement) |
| Backend language | Node.js / TypeScript | Python / FastAPI (implementation choice, not ADK constraint) |
| Credentials (deployed) | Downloaded JSON key file | Attached service account + ADC (no key file in container) |
| GCS signed URLs | Not flagged | IAM `signBlob` permission flagged as potential deployment blocker |
| `bpm_estimate` field | `bpm_estimate` | `movement_tempo_bpm` (tempo inferred from movement, not from an existing song) |
| Hover tooltips on chips | 1–2 sentence tooltips on every chip | Removed — unnecessary |
| Veo / demo video | Mentioned Veo generation | Removed — not relevant to this product |
| Implementation sequence | Infrastructure-first | Risk-first: prove Gemini + Lyria before building UI |
| Generate Again logic | Unspecified | Defined: preferences unchanged → rerun Lyria+combine; preferences changed → rerun plan+Lyria+combine; never re-analyze video |
| `/run-agent` flow | Polling/job infrastructure | Synchronous first; add polling only if latency requires it |

---

## Final Architecture

### Agent Design

A **single deterministic workflow agent** built with **Google ADK (Python)**, running on **Cloud Run**, orchestrating four tools in sequence:

```
ADK Workflow Agent: "ChoreographyMusicAgent"
  │
  ├── Tool 1: analyze_choreography(video_file_uri) → ChoreographySchema JSON
  │     └─► Gemini 3.8 Flash (multimodal, Files API video input, response_schema)
  │
  ├── Tool 2: plan_music(choreography_json, user_preferences) → MusicPrompt string
  │     └─► Gemini 3.8 Flash (text reasoning, translates schema → timestamp-aware music prompt)
  │
  ├── Tool 3: generate_music(music_prompt, duration_seconds) → audio_gcs_uri
  │     └─► Lyria (via Gemini API / google-genai SDK)
  │     └─► Upload MP3 to GCS temp
  │
  └── Tool 4: combine_media(video_gcs_uri, audio_gcs_uri) → final_video_signed_url
        └─► FFmpeg (download from GCS → combine → upload final MP4 → signed URL)
```

**Why single agent**: The pipeline is deterministic and linear. A single ADK `SequentialAgent` (or equivalent workflow construct) genuinely orchestrates the steps and satisfies the hackathon agent requirement without fake complexity.

**Generate Again logic**:
- Creative preferences unchanged → rerun Tools 3 + 4 (reuse choreography + music plan)
- Style / mood / energy / custom instruction changed → rerun Tools 2 + 3 + 4 (reuse choreography analysis only)
- Never re-analyze the video unless the user uploads a new one

### Full Data Flow

```
[Browser]
  │
  ├─ Upload video (POST /upload)
  │     └─► GCS temp bucket (lifecycle: 24h auto-delete)
  │            └─► returns { gcs_uri }
  │
  ├─ Run agent (POST /run-agent)   [synchronous; timeout 600s]
  │     └─► Cloud Run / FastAPI (Python, ADK)
  │              │
  │              ├── upload video to Gemini Files API → file_uri
  │              │
  │              ├── Tool 1: Gemini 3.8 Flash analyzes video
  │              │     └─► ChoreographySchema JSON
  │              │
  │              ├── Tool 2: Gemini 3.8 Flash plans music
  │              │     └─► timestamp-aware MusicPrompt string
  │              │
  │              ├── Tool 3: Lyria generates audio (MP3)
  │              │     └─► upload to GCS temp
  │              │
  │              └── Tool 4: FFmpeg combines video + audio
  │                    └─► upload final MP4 to GCS temp
  │                    └─► signed URL (TTL 1h)
  │
  └─ Preview + Download
        └─► GCS signed URL
```

> **Polling**: Use a simple synchronous `/run-agent` response first. Add polling / job-ID infrastructure only if real model latency during testing makes it necessary.

---

## Choreography Analysis Schema

```json
{
  "duration_seconds": 18,
  "overall_energy": "high",
  "movement_tempo_bpm": 128,
  "segments": [
    {
      "start_sec": 0.0,
      "end_sec": 3.0,
      "label": "entrance",
      "description": "smooth walk-in, arms relaxed",
      "energy": "low",
      "move_type": "entrance",
      "intensity": 2
    },
    {
      "start_sec": 3.0,
      "end_sec": 3.5,
      "label": "accent",
      "description": "sharp chest pop",
      "energy": "high",
      "move_type": "accent",
      "intensity": 8
    }
  ],
  "key_moments": [
    { "time_sec": 3.0,  "type": "accent",       "note": "strong chest pop, high impact" },
    { "time_sec": 7.0,  "type": "spin",          "note": "360 turn, medium speed" },
    { "time_sec": 10.0, "type": "freeze",        "note": "full stop, held 1 second" },
    { "time_sec": 11.0, "type": "climax_start",  "note": "high energy sequence begins" },
    { "time_sec": 18.0, "type": "final_pose",    "note": "held pose, arms extended" }
  ],
  "movement_patterns": {
    "repeated_motifs": ["arm wave at 2s and 6s"],
    "dominant_style": "hip-hop grooves",
    "has_buildup": true,
    "has_drop": true,
    "has_freeze": true,
    "has_final_pose": true
  },
  "analysis_confidence": "high",
  "analysis_notes": "Clear and well-lit video. All movements visible."
}
```

**Key field notes**:
- `movement_tempo_bpm`: recommended tempo inferred from observed movement rhythm — NOT extracted from an existing song (there may be no music in the uploaded video)
- `intensity`: 1–10 (1=stillness, 10=maximum exertion)
- `move_type` enum: `entrance | accent | transition | spin | jump | freeze | pose | sequence | buildup | climax_start | cooldown | final_pose`
- `analysis_confidence`: `"high" | "medium" | "low"` — if `"low"`, show a warning in the UI
- This JSON stays **internal** — the user only sees a compact summary

**UI display of analysis result** (compact, not raw JSON):
```
6 movement moments detected
Intro → Hit → Spin → Freeze → High Energy → Final Pose
```

---

## Prompting Strategy

### Prompt 1 — Gemini Choreography Analysis

```
You are a professional choreography analyst. Analyze this dance video completely from start to finish.
Produce a STRUCTURED, MACHINE-READABLE choreography analysis only.
Do NOT write prose. Do NOT invent movements you cannot clearly see.

Rules:
- Only describe movements clearly visible in the video
- If a section is unclear or too fast to analyze clearly, note it in analysis_notes
  and set analysis_confidence to "medium" or "low" accordingly
- movement_tempo_bpm: estimate the rhythm/tempo you observe from the dancer's movements
  (this is NOT a song BPM — there may be no music in the video)
- intensity: 1–10 where 1 is stillness and 10 is maximum exertion
- All timestamps in seconds as decimals
- If a movement is sub-second and unclear, note it but do not fabricate detail

Output ONLY valid JSON matching this exact schema: [SCHEMA INJECTED HERE]
```

**Known limitation acknowledged in prompt**: Fast movements (<1 sec) may be under-sampled at ~1 FPS. The prompt instructs the model to acknowledge uncertainty rather than fabricate.

### Prompt 2 — Choreography → Music Plan

```
You are a music director. You have a structured choreography analysis of a dance video.
Write a SINGLE, CONCISE music generation prompt for an AI music composer.

Inputs:
- Choreography: [CHOREOGRAPHY_JSON]
- Creator preferences: Style=[STYLE], Mood=[MOOD], Energy=[ENERGY], Movement Feel=[FEEL]
- Optional note: [OPTIONAL_TEXT]

Rules:
- Translate the choreography's movement structure into musical structure
- Use timestamp markers for key musical moments (e.g. "[0:04] strong hit for accent")
- Map movement events to musical language:
    accent       → drum hit / strong musical accent
    freeze       → brief breath, pause, or sustained note
    buildup      → rising energy and expanding instrumentation
    climax_start → drop / high-energy section begins
    final_pose   → strong conclusive ending
- Use "around [time]" phrasing — these are musical directions, not sample-accurate sync guarantees
- Mention: total duration, overall energy arc, style, mood, instrumentation, BPM direction
- Keep under 300 words
- Output ONLY the music prompt text

Example output structure:
[0:00-0:03] [style] intro, restrained energy, [instrumentation]
around 0:03 strong [musical accent] matching the movement hit
[0:03-0:07] rising energy, [BPM] tempo
around 0:07 [transition element] for spin
around 0:10 brief breath or pause for freeze
[0:11-0:18] [drop / high-energy section]
around 0:18 strong conclusive ending for final pose
```

### Prompt 3 — Lyria Generation

Feed the output of Prompt 2 to the Lyria API via `google-genai` SDK with:
- `prompt`: music plan string from Prompt 2
- `duration_seconds`: from ChoreographySchema
- `movement_tempo_bpm`: pass as BPM instruction if Lyria accepts it as a discrete parameter (verify)
- Model: `lyria-3.5` (or verified current model ID)

---

## UI Structure

### Landing Page (`/`)

```
[Logo]

Dance first.
Music second.

Upload your choreography and get original music
composed around your movement.

[Start Creating →]

─────────────────────────────────────
Normal workflow:    Music → Choreography
Our workflow:  Choreography → Music
─────────────────────────────────────

1. Upload your choreography
2. Choose your vibe
3. Generate and download
```
- No hero image, no screenshot, no demo video, no animation
- Light theme, strong typography, minimal

### App Page (`/create`) — Two-column layout

**Left column:**
- Video upload drop zone → video preview after upload
- After generation: final video preview player
- Status indicator: `Analyzing choreography...` / `Composing music...` / `Preparing your video...`
- Compact analysis result once complete: `6 movement moments detected · Intro → Hit → Spin → Freeze → High Energy → Final Pose`

**Right column — compact chip controls:**
```
OUTPUT
[Instrumental ●] [Song / Vocals]

STYLE  (first 6 shown + "+ More" expands inline)
[Pop] [Dance Pop] [Hip-hop] [Afrobeat] [House] [R&B]  [+ More ▾]

MOOD  (first 6 shown + "+ More" expands inline)
[Confident] [Powerful] [Playful] [Euphoric] [Dark] [Energetic]  [+ More ▾]

ENERGY
[Soft] [Medium ●] [High]

MOVEMENT FEEL
[Smooth] [Punchy] [Groovy] [Sharp]  [+ More ▾]

ANYTHING ELSE?  (optional small textarea)
placeholder: "Make the freeze dramatic."

[Generate Music →]
```

**After generation:**
```
[Final video — left column, visually dominant]
[▶ Play]   [↓ Download Video]   [↺ Generate Again]
```

**Chip design** (matches reference image):
- Small rounded pills, subtle border
- Selected: filled/dark background, white text
- No hover tooltips
- "+ More" expands inline, no modal

**Full catalog (behind "+ More")**:
- Style: Pop, Dance Pop, Afrobeat, Amapiano, Hip-hop, Trap, R&B, House, Deep House, Tech House, EDM, Electronic, Disco, Funk, Latin, Reggaeton, Indian Pop / Bollywood-inspired, Cinematic, Rock, Lo-fi, Ambient, Experimental
- Mood: Confident, Powerful, Playful, Euphoric, Dark, Mysterious, Aggressive, Dramatic, Dreamy, Romantic, Emotional, Melancholic, Rebellious, Elegant, Energetic, Chill, Futuristic
- Movement Feel: Smooth, Punchy, Groovy, Sharp, Flowing, Heavy, Bouncy, Minimal

---

## Project Structure

```
agentic-cinema/
├── PLAN.md
├── .env.example
├── .gitignore
├── README.md
├── AGENTS.md                        # IBM Bob project context
│
├── frontend/                        # Next.js (App Router, TypeScript)
│   ├── app/
│   │   ├── page.tsx                 # Landing page
│   │   ├── create/
│   │   │   └── page.tsx             # Main app page
│   │   └── layout.tsx
│   ├── components/
│   │   ├── VideoUploader.tsx
│   │   ├── ChipSelector.tsx         # Chip/pill selector
│   │   ├── ControlPanel.tsx         # Right column
│   │   ├── VideoPreview.tsx
│   │   ├── AnalysisResult.tsx       # Compact movement summary display
│   │   └── StatusBanner.tsx
│   ├── lib/
│   │   └── api.ts                   # Frontend API client
│   └── package.json
│
├── backend/                         # Python / FastAPI (Cloud Run)
│   ├── main.py                      # FastAPI app entry
│   ├── routes/
│   │   ├── upload.py                # POST /upload
│   │   └── run_agent.py             # POST /run-agent
│   ├── agent/
│   │   ├── workflow.py              # ADK workflow agent definition
│   │   └── tools/
│   │       ├── analyze_choreography.py
│   │       ├── plan_music.py
│   │       ├── generate_music.py
│   │       └── combine_media.py
│   ├── prompts/
│   │   ├── choreography_analysis.py
│   │   └── music_plan.py
│   ├── schemas/
│   │   └── choreography.py          # Pydantic ChoreographySchema
│   ├── services/
│   │   ├── gemini_client.py
│   │   ├── lyria_client.py
│   │   ├── storage.py
│   │   └── ffmpeg_service.py
│   ├── utils/
│   │   └── errors.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── scripts/
│   └── deploy.sh
│
└── tests/
    ├── unit/
    │   ├── test_schema.py
    │   └── test_prompts.py
    └── integration/
        └── test_pipeline.py
```

---

## Implementation Sequence

### Sub-task 1 — Gemini Choreography Analysis Proof (Risk Validation)
**Status**: [ ] pending

**Intent**: Validate core product risk before building any infrastructure. Prove Gemini can meaningfully analyze a real short dance video.

**Todo**:
- Write a standalone Python script (no web server, no ADK yet)
- Upload a real 10–15 second dance clip to Gemini Files API
- Call `gemini-3.8-flash` with the choreography analysis prompt + `response_schema`
- Print and inspect the resulting ChoreographySchema JSON
- Assess: Are key moments detected? Are timestamps reasonable? Are fast movements missed?
- If fast moves are missed: test once with a 0.5× slowed copy of the same clip
- Note findings in `AGENTS.md` — these inform prompt tuning

**Expected Outcomes**: Confirmed that Gemini produces usable ChoreographySchema from a real video. Fast-movement limitation assessed and documented.

---

### Sub-task 2 — Lyria Access & Generation Proof (Risk Validation)
**Status**: [ ] pending

**Intent**: Prove Lyria is accessible in the account and produces audio before building infrastructure around it.

**Todo**:
- Write a standalone Python script
- Verify exact Lyria model ID in console / API explorer
- Send a hardcoded test music prompt to Lyria via `google-genai` SDK
- Save the MP3 output locally and listen to it
- Confirm: audio generates, duration is correct, vocal vs instrumental works
- Note Lyria quota limit

**Expected Outcomes**: MP3 audio file generated from a test prompt. Model ID and SDK call signature confirmed.

---

### Sub-task 3 — Choreography-to-Music Prompting Proof
**Status**: [ ] pending

**Intent**: Prove that Prompt 2 (the Gemini music planning step) produces a Lyria prompt that leads to musically relevant output.

**Todo**:
- Take the ChoreographySchema output from Sub-task 1
- Run it through Prompt 2 (music plan prompt) via Gemini text call
- Feed the resulting music prompt to Lyria (from Sub-task 2)
- Listen to output: does the music reflect the choreography energy arc?
- Tune prompts as needed; record final working versions in `prompts/` files

**Expected Outcomes**: End-to-end audio output that is clearly shaped around choreography structure. Prompts finalized.

---

### Sub-task 4 — Hardcoded End-to-End Script
**Status**: [ ] pending

**Intent**: One working end-to-end pipeline as a Python script, no web server, using the demo video.

**Todo**:
- Script: load demo video → Files API → analyze → plan → Lyria → FFmpeg combine → save final MP4 locally
- This is the proof-of-concept that validates everything before UI is built
- Commit this script; it becomes the reference for the backend implementation

**Expected Outcomes**: A working `demo_pipeline.py` that produces the final video locally.

---

### Sub-task 5 — Repository Setup & GCS Storage
**Status**: [ ] pending

**Intent**: Initialize clean repo and GCS storage service.

**Todo**:
- Initialize Git repo, full directory structure
- `.gitignore`, `.env.example`, README skeleton, AGENTS.md
- ESLint + Prettier for frontend; Black + Ruff for Python backend
- Initialize Next.js frontend (App Router, TypeScript)
- Initialize Python/FastAPI backend with `requirements.txt`
- Implement `storage.py`: upload_file, generate_signed_url (verify `signBlob` IAM permission documented)
- GCS lifecycle rule: 24-hour delete (document manual setup step)
- Local dev: document `gcloud auth application-default login`; deployed: attached service account

**Expected Outcomes**: Clean repo, both apps scaffold, storage service works.

---

### Sub-task 6 — Backend: Upload Endpoint + ADK Agent
**Status**: [ ] pending

**Intent**: Build the FastAPI backend with upload endpoint and ADK workflow agent based on the proven scripts from Sub-tasks 1–4.

**Todo**:
- `POST /upload`: multipart video, validate type + size, upload to GCS, return `{ gcs_uri }`
- Define Pydantic `ChoreographySchema`
- `agent/workflow.py`: define `ChoreographyMusicAgent` as ADK SequentialAgent with Tools 1–4
- `agent/tools/`: implement each tool as a Python function wrapping the proven service calls
- `POST /run-agent`: synchronous call; accepts `{ gcs_uri, user_preferences, cached_choreography? }`; returns `{ choreography_summary, final_video_url, music_prompt }`
  - If `cached_choreography` is provided: skip Tool 1 (re-analyze skip)
  - If only preferences changed: skip Tools 1 and 2 from cache
- Set Cloud Run timeout to 600s
- ⚠️ Confirm ADK deployment: Cloud Run container directly vs managed Agent Runtime

**Expected Outcomes**: Backend handles full pipeline via single POST call. Generate Again works without re-analyzing video.

---

### Sub-task 7 — Frontend Creative Controls (Chip UI)
**Status**: [ ] pending

**Intent**: Right-column control panel with chip selectors.

**Todo**:
- `ChipSelector.tsx`: chips, selected state, "+ More" expand/collapse (no hover tooltips)
- `ControlPanel.tsx`: Output, Style, Mood, Energy, Movement Feel, Optional text textarea
- `AnalysisResult.tsx`: compact display of movement summary
- Wire all controls to state; pass to `/run-agent` as `user_preferences`

**Expected Outcomes**: Full interactive control panel, selections captured and sent correctly.

---

### Sub-task 8 — Full Pipeline Integration & Status Flow
**Status**: [ ] pending

**Intent**: Connect all steps end-to-end with clear status feedback.

**Todo**:
- Frontend pipeline: upload → run-agent (synchronous) → preview/download
- `StatusBanner.tsx`: per-step status labels
- Error handling at each step with user-facing messages
- Final video preview, Download button, Generate Again button
  - Generate Again: detect what changed (nothing / only preferences) and call backend accordingly
- Test full end-to-end flow

**Expected Outcomes**: User completes full flow; status always visible; download works.

---

### Sub-task 9 — Landing Page & Visual Design Polish
**Status**: [ ] pending

**Intent**: Landing page and final visual consistency.

**Todo**:
- Landing page (text-only): headline, subhead, CTA, workflow comparison, 3-step summary
- Design: light theme, strong typography, subtle borders, restrained palette
- No purple gradients, no glassmorphism, no oversized cards
- Responsive: two-column collapses to single column on mobile

**Expected Outcomes**: Landing page is polished and communicates the positioning clearly.

---

### Sub-task 10 — README, AGENTS.md & IBM Bob Evidence
**Status**: [ ] pending

**Intent**: Full documentation and hackathon submission evidence.

**Todo**:
- Complete `README.md`: pitch, architecture Mermaid diagram, tech stack, Gemini/Lyria usage, ADK agent description, IBM Bob usage section, local setup, env vars, deployment steps, demo script, known limitations
- Explicit IBM Bob section: Plan mode used for architecture, Agent mode for implementation; list specific decisions/files Bob produced
- Honest limitations: ~1 FPS Gemini frame sampling, no millisecond sync, Lyria quota, vocal availability
- `AGENTS.md`: Bob project context file
- Verify `.env.example` is complete and accurate
- ⚠️ Confirm from `agentic-cinema.devpost.com/forum_topics/44630` what specific evidence format the IBM track requires

**Expected Outcomes**: README complete, IBM Bob usage documented.

---

### Sub-task 11 — Testing, Linting & Cloud Run Deployment
**Status**: [ ] pending

**Intent**: Validate and deploy to Cloud Run.

**Todo**:
- Unit tests: Pydantic schema validation, prompt builder output, error cases
- Integration test: mock Gemini + Lyria responses, test full agent pipeline
- Black + Ruff for Python; ESLint + Prettier for TypeScript
- `Dockerfile`: Python base + FFmpeg install + FastAPI app
- `scripts/deploy.sh`: `gcloud run deploy` with timeout 600s flag, attached service account, env vars
- Test full pipeline on Cloud Run
- Verify GCS signed URLs work from Cloud Run service identity (confirm `signBlob` permission)

**Expected Outcomes**: App deployed, full pipeline works in production.

---

## Things You Must Do Manually

1. **Create GCP Project** (if not existing): `console.cloud.google.com` → New Project
2. **Enable APIs** in GCP Console:
   - Gemini API or Vertex AI API
   - Cloud Storage API
   - Cloud Run API
   - Artifact Registry API
   - Google Agent Builder / ADK API (for hackathon compliance)
3. **Create a Cloud Run service account** and assign roles:
   - `Storage Object Admin` (GCS)
   - `Vertex AI User` / Gemini access
   - `roles/iam.serviceAccountTokenCreator` (required for GCS signed URLs — verify this before deployment)
4. **Accept model terms of service** for Gemini and Lyria if prompted in AI Studio or Vertex AI console
5. **Verify exact `gemini-3.8-flash` model ID** string (may have version suffix) in your console before Sub-task 1
6. **Verify exact Lyria model ID** (prefer `lyria-3.5`) and max duration limit before Sub-task 2
7. **Confirm Lyria vocal support** parameter before exposing Song/Vocals option in UI
8. **Create GCS bucket** with 24-hour lifecycle deletion rule: Storage → Create bucket → Lifecycle → Add rule → Delete after 1 day
9. **Confirm ADK deployment method** (Cloud Run container vs managed Agent Runtime) from `docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk` before Sub-task 6
10. **Local auth**: Run `gcloud auth application-default login` for local development (do not use JSON keys in code)
11. **Check IBM track submission evidence format** from `agentic-cinema.devpost.com/forum_topics/44630` before finalizing README

---

## Environment Variables (`.env.example`)

```env
# Google Cloud
GOOGLE_CLOUD_PROJECT_ID=your-gcp-project-id
# Local dev only: GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
# Deployed Cloud Run: use attached service account (no key file needed)

# GCS
GCS_TEMP_BUCKET=agentic-cinema-temp

# Gemini API (used for Gemini model AND Lyria — same key)
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash

# Lyria (accessed via google-genai SDK with GEMINI_API_KEY — no separate endpoint or key)
LYRIA_MODEL=lyria-3.5

# App
PORT=8080
FRONTEND_URL=http://localhost:3000
MAX_VIDEO_SIZE_MB=60
SIGNED_URL_TTL_HOURS=1
CLOUD_RUN_TIMEOUT_SECONDS=600
```

> `LYRIA_API_ENDPOINT` and `LYRIA_API_KEY` from the original plan are **removed**. Lyria is accessed through the Gemini API key via the `google-genai` SDK.

---

## Technical Risks & Fallbacks

| Risk | Likelihood | Fallback |
|------|-----------|----------|
| Gemini 1 FPS misses fast dance moves | MEDIUM | Provide slowed copy for analysis; note limitation honestly in UI |
| Lyria quota insufficient for demo day | MEDIUM | Pre-generate demo audio the day before; cache the result |
| Lyria vocal generation unavailable in account | LOW-MEDIUM | Default to Instrumental; disable Song/Vocals chip |
| ADK requires managed Agent Runtime (not Cloud Run direct) | MEDIUM | Deploy to Agent Runtime; frontend calls that endpoint instead |
| `gemini-3.8-flash` model ID string differs in API | LOW | Verify in console; update env var |
| GCS signed URL signing fails (IAM) | MEDIUM | Caught by early manual setup check in Sub-task 5 |
| Synchronous run-agent times out on slow generation | LOW-MEDIUM | Add polling/job-ID if this manifests during Sub-task 8 testing |
| Cloud Run /tmp full on large video | LOW | 60 MB upload limit + clean up temp files after each request |

---

## Demo Script

1. Open app — landing page
2. Click "Start Creating"
3. Drop in a ~15 second dance video
4. Show compact analysis result: `5 movement moments detected · Intro → Hit → Spin → Freeze → Final Pose`
5. Select: Style = **Afrobeat**, Mood = **Euphoric**, Energy = **High**, Movement Feel = **Groovy**
6. Click "Generate Music"
7. Status: `Analyzing choreography...` → `Composing music...` → `Preparing your video...`
8. Play final video — same dance, new original soundtrack
9. Click Download

---

*Plan written with IBM Bob (Plan Mode). Revised with targeted corrections per user-provided official documentation.*
*Implementation begins only after user approval.*
