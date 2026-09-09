# MoveScore - Final Devpost Submission

## One-line pitch

**MoveScore makes choreography the prompt. Upload a dance first, then generate original music around its key movement moments, tempo, and energy arc.**

## Tagline

**Dance first. Music second.**

---

# Project Story

## Inspiration

Most short-form creator workflows start with music.

A dancer finds a song, chooses a section, and then builds choreography around it. That works when the song comes first, but I kept thinking about the opposite situation: what if the movement already exists first?

It could be a freestyle, rehearsal, original routine, creator transition, or a brand movement. In that case, the creator still has to search for music that approximately fits something they already made.

That felt backwards to me.

I wanted to see if the choreography itself could become the creative input for music generation.

That became MoveScore.

The core idea is simple:

```
Normal workflow:
Music -> Choreography

MoveScore:
Choreography -> Music
```

Instead of sending a generic text prompt such as "make an energetic song" directly to a music model, MoveScore first tries to understand the movement. It looks at the choreography structure, key moments, intensity, movement tempo, and energy arc, then turns that understanding into musical direction before Lyria generates anything.

**MoveScore makes choreography the prompt.**

## What it does

A creator uploads an MP4 dance or choreography video and chooses the creative direction they want:

- Instrumental or Song / Vocals
- Style
- Mood
- Energy
- Movement feel
- Optional custom instruction

MoveScore then runs a real multi-step agentic workflow.

First, Gemini 3.8 Flash analyzes the choreography and returns a structured movement representation. It captures timestamped segments, intensity, movement tempo, key moments such as hits, jumps, spins, freezes, climax points and final poses, plus an overall energy arc and confidence.

A second Gemini 3.8 Flash step acts like a music director. It receives that structured choreography plus the creator's preferences and translates movement into musical language.

For example:

```
accent / hit  -> strong drum hit or musical accent
freeze        -> brief silence, breath, or sustained note
buildup       -> rising energy and instrumentation
climax_start  -> drop or high-energy section
spin          -> swirling melodic or rhythmic transition
final_pose    -> strong ending
```

That reasoning step produces timestamp-aware musical direction.

Lyria 3.5 then generates the soundtrack from that direction.

Finally, the backend combines the generated audio with the original choreography using FFmpeg and returns a playable, downloadable MP4.

I intentionally do not describe MoveScore as frame-perfect beat synchronization. The timestamps are musical directions, not sample-accurate guarantees. The goal is to compose music around the choreography's structure, key moments, movement tempo, and energy arc instead of generating a generic track from text alone.

## How we built it

I built MoveScore as a small production-style pipeline rather than a single API call.

The frontend is built with Next.js and runs on Cloud Run. The backend is built with FastAPI and also runs on Cloud Run.

The core AI workflow is a Google ADK agent deployed to **Gemini Enterprise Agent Platform / Agent Runtime**.

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

The production backend invokes the deployed Agent Runtime directly. The successful end-to-end path does not use the local fallback.

### IBM Bob

IBM Bob was the main development environment during the first and largest build phase.

I started in **Bob Plan Mode** to work through the product architecture, API choices, choreography-to-music workflow, limitations, and the initial Google Cloud deployment plan.

I then used **Bob Agent Mode** for the first implementation across the backend and frontend. That included the FastAPI services, Gemini and Lyria integration, ADK workflow, schemas, prompts, FFmpeg logic, GCS handling, Next.js UI, tests, Dockerfiles, and deployment scripts.

By the time my Bobcoins were almost exhausted, the core architecture and product were already in place.

### Google Antigravity

I then used Google Antigravity for the final production-hardening phase.

I used it to review the existing implementation against the current Google SDKs and documentation, identify production blockers, harden Agent Runtime packaging and authentication, fix remote runtime response handling, troubleshoot Cloud Run and Agent Runtime compatibility issues, and validate the real production flow with an actual MP4.

That final pass kept the original IBM Bob foundation while making the production path reliable enough for a real browser demo.

### Storage and privacy

Uploaded videos, generated audio, and final MP4s are stored in a private Cloud Storage bucket used for temporary processing.

The bucket has a one-day deletion lifecycle and versioning is disabled. Final results are returned through signed URLs.

There is no user database, profile history, or permanent media library in this hackathon version.

## Challenges we ran into

The hardest part was not getting Gemini or Lyria to produce one successful response. The difficult part was making the complete workflow reliable in production.

### Agent Runtime integration

The application had to run as a real ADK agent on Gemini Enterprise Agent Platform rather than only as local Python orchestration.

I ran into issues around Agent Runtime packaging, runtime identity, secret access, environment configuration, SDK behavior, and remote event parsing.

### Current Google SDK behavior

The project uses very current Google APIs and SDKs, so some older examples and assumptions from the early deployment plan were no longer correct.

I had to verify the actual current runtime and SDK behavior instead of blindly following the first setup notes.

### Gemini model routing

The deployed ADK agent initially tried to resolve `gemini-3.8-flash` through the wrong model path.

The final production runtime uses the supported Gemini Developer API client inside the deployed Agent Runtime while keeping the agent itself hosted and orchestrated on Gemini Enterprise Agent Platform.

### Signed URLs from Cloud Run

Generating signed GCS URLs without downloading a private service-account key required getting the IAM signing path correct.

The final deployment uses Google-managed credentials rather than shipping credential files with the application.

### Lyria duration

Lyria's generated duration is approximate. In one provider test it produced substantially more audio than requested.

The final FFmpeg pipeline therefore uses the choreography video as the duration boundary when combining generated audio and video.

### Keeping the product claim honest

Lyria can follow timestamp-aware musical direction, but it is not frame-level scoring where every body movement gets an exact sound.

I deliberately kept MoveScore positioned around **key movement moments, movement tempo, structure, and energy arc**. That is both technically honest and still useful.

## Accomplishments that we're proud of

The biggest accomplishment is that MoveScore is not only a local prototype.

The real production flow works end to end:

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
- Temporary storage lifecycle
- Restricted credentials and dedicated runtime identity

A real 10-second choreography test completed the full production pipeline in about 103 seconds.

I am also proud that I kept the product focused. I did not add accounts, social feeds, project history, databases, or editing timelines just to make the app look bigger.

The core question stayed the same throughout the hackathon:

**Can movement come first and music come second?**

## What we learned

I learned that multimodal generation becomes much more interesting when the first model is not responsible for the final creative output.

Gemini is not just captioning a dance video here. Its structured choreography analysis becomes an intermediate representation that another reasoning step turns into musical intent.

That separation gave the workflow a clear structure:

```
understand movement
-> translate movement into musical intent
-> generate music
```

I also learned that productionizing an agent is very different from running the same workflow locally.

Identity, packaging, permissions, remote event formats, storage access, model routing, timeouts, signed URLs, and deployment behavior all became part of the product.

Another useful lesson was to keep uncertainty visible. If movement is too fast to analyze confidently, the prompt tells Gemini not to invent detail. The UI exposes analysis confidence instead of pretending every result is exact.

### Demo disclosure

The choreography clip used in the demo is synthetic test footage generated with Google Gemini.

Prompt:

> "Create a 10-second dance choreography video. Don't give it a good song; I'm interested in the dance only. Make it nice, smooth, and energetic, like someone is rehearsing."

I intentionally used a simple rehearsal-style clip so the movement is easy to see and the demo can focus on what MoveScore adds.

The demo narration was generated in **Google Cloud Agent Platform Studio Speech** using **Gemini 3.1 Flash TTS (Preview)** with the **Umbriel (Male)** voice.

## What's next for MoveScore

The current version proves the core idea, but there is a lot more I would explore next.

The first improvement would be better temporal understanding for fast choreography. The current system is strongest at important structural movement moments rather than very fast frame-level motion.

I would also like to add:

- Multiple soundtrack variations from the same choreography
- Section-level creative direction
- Faster asynchronous generation with live progress
- Better mobile creator workflow
- A/B comparison between musical interpretations
- Stronger rhythm and section constraints when music models expose them
- More precise visual alignment between detected movement moments and generated musical sections

Longer term, the idea I find most interesting is bigger than dance music generation itself:

**movement can become creative direction.**

---

# What Google Cloud products did you use in this project?

I used the following Google Cloud and Google AI products in MoveScore:

## Core agent and AI workflow

- **Gemini Enterprise Agent Platform / Agent Runtime**
  - Hosts the production MoveScore ADK agent.
  - The backend invokes the deployed runtime directly for the choreography-to-music workflow.

- **Google Agent Development Kit (ADK)**
  - Defines the MoveScore agent and its choreography analysis, music planning, and music generation tools.

- **Gemini 3.8 Flash**
  - Used for multimodal choreography analysis.
  - Used again for the music-planning reasoning step that converts movement structure and creator preferences into timestamp-aware musical direction.

- **Lyria 3.5**
  - Generates the original music from the choreography-derived music direction.
  - Used for both Instrumental and Song / Vocals modes.

## Application and production infrastructure

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
  - Used to build production deployment artifacts.

- **IAM and service accounts**
  - Used for least-privilege access between Agent Runtime, Cloud Run, Cloud Storage, Secret Manager, and signed URL generation.

- **Cloud Logging**
  - Used to diagnose production Agent Runtime and Cloud Run failures during validation.

- **Cloud Resource Manager**
  - Enabled as part of the deployed Agent Runtime session-service requirements.

## Demo production

- **Google Cloud Agent Platform Studio Speech**
  - Used to generate narration for the hackathon demo.

- **Gemini 3.1 Flash TTS (Preview)**
  - Text-to-speech model used for the narration.

- **Umbriel (Male)**
  - Voice selected for the final demo narration.

---

# Please list all other tools or products you used in your project.

## IBM Bob

IBM Bob was the main development environment during the first and largest build phase.

I used Bob Plan Mode for architecture, API and limitation analysis, workflow planning, and the initial Google Cloud deployment plan.

I then used Bob Agent Mode for the initial backend, frontend, prompts, schemas, tests, Dockerfiles, and deployment scripts.

## Google Antigravity

When my Bobcoins were almost exhausted, I moved the remaining production-hardening work to Google Antigravity.

I used Antigravity to review the existing implementation against current Google SDKs, resolve production blockers, harden the Agent Runtime integration, troubleshoot Cloud Run and GCP runtime issues, and validate the real end-to-end production flow.

## Development stack

- Python
- FastAPI
- Pydantic
- Next.js
- React
- TypeScript
- google-genai Python SDK
- Google Cloud Python SDKs
- FFmpeg / ffprobe
- Docker
- Git
- GitHub

## Demo editing

- **VSDC**
  - Used to edit the final screen-recorded demo video.

---

# Submission links

- **Live app:** https://movescore-frontend-tjzml33mta-uc.a.run.app
- **Backend health:** https://movescore-backend-tjzml33mta-uc.a.run.app/health
- **GitHub:** https://github.com/PrathmeshAdsod/MoveScore
- **Agent Runtime:** `projects/1093246532955/locations/us-central1/reasoningEngines/2313598414480211968`

---

# Short description

**MoveScore reverses the normal creator workflow. Instead of starting with music and choreographing around it, creators upload choreography first. Gemini understands the movement, translates key moments and energy into timestamp-aware musical direction, and Lyria 3.5 composes an original soundtrack around the dance. The production workflow runs as a Google ADK agent on Gemini Enterprise Agent Platform and returns a playable, downloadable MP4.**
