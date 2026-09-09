# MoveScore - Devpost Submission Draft

## One-line pitch

**MoveScore makes choreography the prompt. Upload a dance first, then generate original music around its key movement moments, tempo, and energy arc.**

## Tagline

**Dance first. Music second.**

---

# Project Story

## Inspiration

Most short-form creator workflows start with music.

A dancer hears a song, finds a section that works, and then builds choreography around it. That is completely normal, but I kept thinking about the opposite situation: what if the movement already exists first?

It could be a freestyle, rehearsal, original dance routine, creator transition, or a brand movement. In that case, the creator still has to search for music that approximately fits what they already made.

That felt backwards to me.

I wanted to see if the choreography itself could become the creative input for music generation.

That became MoveScore.

The simple idea is:

```
Normal workflow:
Music -> Choreography

MoveScore:
Choreography -> Music
```

Instead of asking a music model to make "an energetic song", MoveScore first tries to understand the dance. It looks at the movement structure, key moments, intensity, movement tempo, and energy arc. Then it converts that understanding into musical direction before Lyria generates anything.

The phrase I ended up using throughout the project is:

**MoveScore makes choreography the prompt.**

---

## What it does

A creator uploads an MP4 dance or choreography video and chooses the creative direction they want.

They can choose:

- Instrumental or Song / Vocals
- Style
- Mood
- Energy
- Movement feel
- An optional custom instruction

MoveScore then runs a real multi-step production workflow.

First, Gemini 3.8 Flash analyzes the choreography and returns a structured movement representation. This includes timestamped movement segments, key moments such as hits, jumps, spins, freezes, climax points and final poses, plus movement intensity, energy, approximate movement BPM, and confidence.

The next step uses Gemini again, but this time as a music director. It receives the choreography structure and the creator's preferences, then translates movement into musical language.

For example:

```
accent / hit  -> strong drum hit or musical accent
freeze        -> brief silence, breath, or sustained note
buildup       -> rising energy and instrumentation
climax_start  -> drop or high-energy section
spin          -> swirling transition
final_pose    -> strong ending
```

That reasoning step produces timestamp-aware music direction.

Lyria 3.5 then generates the actual soundtrack.

Finally, the backend combines the generated music with the original choreography video using FFmpeg and returns a downloadable MP4.

I intentionally do not describe this as frame-perfect synchronization. The timestamps are musical directions, not sample-accurate beat matching. The goal is for the music to be composed around the choreography's structure and energy instead of being generated from a generic text prompt.

---

## How I built it

I built MoveScore as a small production-style pipeline rather than a single API call.

The frontend is a Next.js application running on Cloud Run. The backend is FastAPI, also on Cloud Run.

The core AI workflow runs as a Google ADK agent deployed to **Gemini Enterprise Agent Platform / Agent Runtime**.

The production path is:

```
Browser
-> Cloud Run frontend
-> Cloud Run backend
-> Gemini Enterprise Agent Runtime
-> Google ADK agent
-> Gemini 3.8 Flash choreography analysis
-> Gemini 3.8 Flash music planning
-> Lyria 3.5 music generation
-> Cloud Storage
-> FFmpeg
-> final MP4
```

The deployed Agent Runtime resource is:

`projects/1093246532955/locations/us-central1/reasoningEngines/2313598414480211968`

The successful production flow invokes that runtime directly. It does not use the local fallback path.

### IBM Bob

IBM Bob was the main development environment for the initial and largest part of the project.

I first used **Bob Plan Mode** to work through the product architecture, model/API choices, choreography-to-music flow, known limitations, and the original Google Cloud deployment plan.

I then moved into **Bob Agent Mode** for the first implementation of the backend and frontend. That included the FastAPI services, Gemini and Lyria integration, ADK workflow, schemas, prompts, FFmpeg logic, GCS handling, Next.js UI, tests, Dockerfiles, and deployment scripts.

By the time my Bobcoins were almost exhausted, the core product and architecture were already there.

### Google Antigravity

I then handed the production-hardening phase to Google Antigravity.

I used Antigravity to review the implementation against the current Google SDKs and documentation, identify production blockers, harden Agent Runtime packaging and authentication, fix remote runtime response handling, troubleshoot Cloud Run and Agent Runtime compatibility issues, and validate the final production flow with a real MP4.

The end result keeps the original IBM Bob foundation and architecture, but with the production path hardened and verified.

### Storage and privacy

Uploaded videos, generated audio, and final MP4 files are stored in a private Cloud Storage bucket used for temporary processing.

The bucket has a one-day deletion lifecycle and versioning is disabled. Final downloads use signed URLs.

There is no user database, profile history, or permanent media library in this hackathon version.

---

## Challenges I ran into

The hardest part was not getting Gemini or Lyria to return something once. It was making the complete workflow behave reliably in production.

### Agent Runtime integration

The application had to run as a real ADK agent on Gemini Enterprise Agent Platform rather than only as local Python orchestration.

I ran into several runtime and SDK compatibility issues around packaging, service identity, secret access, environment configuration, and remote event parsing.

The final runtime uses a dedicated service account with the permissions it needs for Secret Manager and Cloud Storage.

### Current SDK behavior

The project was built against very current Google APIs and SDKs.

That meant some examples and assumptions from older documentation or early implementation plans were no longer correct. I had to verify the actual current behavior rather than simply trusting the first deployment notes.

### Gemini model routing

The deployed ADK agent initially tried to resolve `gemini-3.8-flash` through the wrong model path.

The production runtime now uses the supported Gemini Developer API client inside the deployed Agent Runtime while keeping the agent itself hosted and orchestrated on Gemini Enterprise Agent Platform.

### Signed URLs from Cloud Run

Generating signed GCS URLs without downloading a private service-account key required getting the IAM signing path correct.

The final deployment uses Google-managed credentials rather than shipping credential files with the application.

### Lyria duration

Lyria's generated duration is approximate.

In one provider test it produced substantially more audio than requested. The final media pipeline therefore uses the choreography video as the duration boundary when combining audio and video.

### Keeping the claim honest

One of the product-design challenges was deciding what MoveScore should claim.

Lyria can follow timestamp-aware musical direction, but this is not frame-level scoring where every body movement gets an exact sound.

I kept the product positioned around **key movement moments, tempo, structure, and energy arc**. I think that is both technically honest and still useful.

---

## Accomplishments that I'm proud of

The biggest accomplishment is that MoveScore is not only a local prototype.

I got the real production path working end to end:

```
real MP4
-> GCS
-> Gemini Enterprise Agent Runtime
-> Gemini choreography analysis
-> Gemini music planning
-> Lyria
-> generated MP3
-> FFmpeg
-> final MP4
-> browser playback
-> download
```

The final production validation included:

- Real upload to GCS
- Direct Agent Runtime invocation with no local fallback
- Gemini 3.8 Flash choreography analysis
- Gemini 3.8 Flash music planning
- Lyria 3.5 MP3 generation
- Browser-compatible H.264 + AAC final MP4
- Full FFmpeg decode validation
- Chrome UI playback and download
- Temporary storage lifecycle and restricted credentials

The successful 10-second test completed the full pipeline in about 103 seconds.

I am also happy that the product stayed small. I did not add accounts, social features, project history, databases, or editing timelines just to make the app look bigger. The core loop is still the thing I wanted to test:

**Can movement come first and music come second?**

---

## What I learned

I learned that multimodal generation gets much more interesting when the first model is not responsible for the final creative output.

Gemini is not just being used to caption a video here. Its structured choreography analysis becomes an intermediate representation that another reasoning step can turn into music direction.

That separation made the system easier to reason about:

```
understand movement
-> translate movement into musical intent
-> generate music
```

I also learned that productionizing an agent is very different from running the same code locally.

Identity, packaging, permissions, remote event formats, storage access, model routing, and timeouts all become part of the product.

Another useful lesson was to keep uncertainty visible. If a movement is too fast to analyze confidently, the prompt tells Gemini not to invent detail. The UI also exposes analysis confidence rather than pretending every result is exact.

---

## Demo input and narration disclosure

The choreography clip used in the demo is synthetic test footage that I generated with Google Gemini.

Prompt:

> "Create a 10-second dance choreography video. Don't give it a good song; I'm interested in the dance only. Make it nice, smooth, and energetic, like someone is rehearsing."

I used a simple rehearsal-style clip intentionally so the movement is easy to see and the demo can focus on the soundtrack MoveScore creates.

For the demo narration, I used **Google Cloud Agent Platform Studio Speech** with **Gemini 3.1 Flash TTS (Preview)** and the **Umbriel (Male)** voice.

---

## What's next for MoveScore

The current version proved the core idea, but there are several directions I would like to explore next.

The first is better temporal understanding for fast choreography. The current system is strongest at important structural movement moments rather than very fast frame-level motion.

I would also like to add:

- Multiple soundtrack variations from the same choreography
- Section-level creative direction
- Faster asynchronous generation with live progress
- Better mobile upload and creator workflow
- A/B comparison between two musical interpretations
- Stronger rhythm and section constraints when the music model supports them
- More precise visual alignment between detected movement moments and generated musical sections

Longer term, I think the interesting part of MoveScore is bigger than dance music generation itself.

The underlying pattern is that **movement can become creative direction**.

---

# What Google Cloud products did you use in this project?

I used the following Google Cloud and Google AI products in MoveScore:

### Core agent and AI workflow

- **Gemini Enterprise Agent Platform / Agent Runtime**
  - Hosts the production MoveScore ADK agent.
  - The backend invokes the deployed runtime directly for the choreography-to-music workflow.

- **Google Agent Development Kit (ADK)**
  - Defines the agent and its three main tools: choreography analysis, music planning, and music generation.

- **Gemini 3.8 Flash**
  - Used for multimodal choreography analysis.
  - Used again as the music-planning reasoning step that converts movement structure and creator preferences into timestamp-aware music direction.

- **Lyria 3.5**
  - Generates the original music from the choreography-derived music prompt.
  - Supports both instrumental and Song / Vocals modes in MoveScore.

### Application and deployment

- **Cloud Run**
  - Hosts the Next.js frontend.
  - Hosts the FastAPI backend and FFmpeg media-combine step.

- **Google Cloud Storage**
  - Stores uploaded MP4s, generated audio, and final MP4s temporarily.
  - Configured with a one-day deletion lifecycle and versioning disabled.

- **Secret Manager**
  - Stores the restricted Gemini API key used by the production runtime.

- **Artifact Registry**
  - Stores production container images.

- **Cloud Build**
  - Used to build deployment artifacts for Cloud Run.

- **IAM and service accounts**
  - Used for least-privilege runtime, Cloud Run, storage, secret, and signing access.

- **Cloud Logging**
  - Used to diagnose real Agent Runtime and Cloud Run deployment/runtime failures during production validation.

- **Cloud Resource Manager**
  - Enabled as part of the deployed Agent Runtime session-service requirements.

### Demo production

- **Google Cloud Agent Platform Studio Speech**
  - Used to generate the hackathon demo narration.

- **Gemini 3.1 Flash TTS (Preview)**
  - Narration model.

- **Umbriel (Male)**
  - Voice selected for the demo narration.

---

# Please list all other tools or products you used in your project.

### IBM Bob

IBM Bob was the main development environment during the first and largest build phase.

I used Bob Plan Mode for architecture, API and limitation analysis, workflow planning, and the initial deployment plan. I then used Bob Agent Mode for the initial backend, frontend, prompts, schemas, tests, Dockerfiles, and deployment scripts.

### Google Antigravity

When my Bobcoins were almost exhausted, I moved the remaining production-hardening work to Google Antigravity.

I used Antigravity to audit the existing implementation against the current Google SDKs, resolve production blockers, harden the Agent Runtime integration, troubleshoot Cloud Run and GCP runtime issues, and validate the real end-to-end production flow.

### Development stack

- **Python**
- **FastAPI**
- **Pydantic**
- **Next.js**
- **React**
- **TypeScript**
- **google-genai Python SDK**
- **Google Cloud Python SDKs**
- **FFmpeg / ffprobe**
- **Docker**
- **Git and GitHub**

### Demo editing

- **VSDC**
  - Used to edit the final screen-recorded hackathon demo.

---

# Useful submission links

- **Live app:** https://movescore-frontend-tjzml33mta-uc.a.run.app
- **Backend health:** https://movescore-backend-tjzml33mta-uc.a.run.app/health
- **GitHub:** https://github.com/PrathmeshAdsod/MoveScore
- **Agent Runtime:** `projects/1093246532955/locations/us-central1/reasoningEngines/2313598414480211968`

---

# Short description for Devpost

**MoveScore reverses the normal creator workflow. Instead of starting with music and choreographing around it, creators upload choreography first. Gemini understands the movement, translates key moments and energy into timestamp-aware musical direction, and Lyria 3.5 composes an original soundtrack around the dance. The production workflow runs as a Google ADK agent on Gemini Enterprise Agent Platform and returns a playable, downloadable MP4.**
