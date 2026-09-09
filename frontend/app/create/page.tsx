"use client";

/**
 * /create — Main application page.
 *
 * Two-column layout:
 *   Left:  Video upload / preview + status + analysis result
 *   Right: Creative controls (sticky) + Generate button
 *
 * Pipeline:
 *   upload → run-agent (analyzes + plans + generates + combines) → preview + download
 *
 * Generate Again logic:
 *   - preferences unchanged:  rerun generate + combine (pass cached_choreography + cached_music_prompt)
 *   - preferences changed:    rerun plan + generate + combine (pass cached_choreography only)
 *   - new video uploaded:     full pipeline
 */

import { useCallback, useRef, useState } from "react";
import Link from "next/link";

import VideoUploader from "@/components/VideoUploader";
import VideoPreview from "@/components/VideoPreview";
import ControlPanel from "@/components/ControlPanel";
import StatusBanner from "@/components/StatusBanner";
import AnalysisResult from "@/components/AnalysisResult";

import { uploadVideo, runAgent } from "@/lib/api";
import type {
  ChoreographySummary,
  PipelineStep,
  RunAgentResponse,
  UserPreferences,
} from "@/lib/types";

const DEFAULT_PREFS: UserPreferences = {
  output_type: "instrumental",
  style: undefined,
  mood: undefined,
  energy: "medium",
  movement_feel: undefined,
  custom_instruction: undefined,
};

function prefsKey(p: UserPreferences): string {
  return JSON.stringify({
    o: p.output_type,
    s: p.style,
    m: p.mood,
    e: p.energy,
    f: p.movement_feel,
    c: p.custom_instruction,
  });
}

const STEP_LABELS: Record<PipelineStep, string> = {
  idle: "",
  uploading: "Uploading video…",
  analyzing: "Analysing your choreography with Gemini…",
  composing: "Composing music direction…",
  generating: "Generating music with Lyria 3.5…",
  combining: "Combining video and audio…",
  done: "Done!",
  error: "Something went wrong",
};

export default function CreatePage() {
  const [step, setStep] = useState<PipelineStep>("idle");
  const [errorMessage, setErrorMessage] = useState<string | undefined>();

  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [gcsUri, setGcsUri] = useState<string | null>(null);

  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFS);

  const [analysisResult, setAnalysisResult] = useState<ChoreographySummary | null>(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);
  const [musicPrompt, setMusicPrompt] = useState<string | null>(null);

  const cachedChoreographyRef = useRef<Record<string, unknown> | null>(null);
  const cachedMusicPromptRef = useRef<string | null>(null);
  const cachedPrefsKeyRef = useRef<string | null>(null);

  const isRunning = !["idle", "done", "error"].includes(step);

  // ── Upload ────────────────────────────────────────────────────────────────
  const handleFileSelected = useCallback(async (file: File) => {
    setErrorMessage(undefined);
    setStep("uploading");
    setFinalVideoUrl(null);
    setAnalysisResult(null);
    cachedChoreographyRef.current = null;
    cachedMusicPromptRef.current = null;
    cachedPrefsKeyRef.current = null;

    const localUrl = URL.createObjectURL(file);
    setPreviewUrl(localUrl);
    setUploadedFile(file);

    try {
      const res = await uploadVideo(file);
      setGcsUri(res.gcs_uri);
      setStep("idle");
    } catch (err) {
      setStep("error");
      setErrorMessage(
        err instanceof Error ? err.message : "Upload failed. Please try again."
      );
    }
  }, []);

  // ── Generate ──────────────────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    if (!gcsUri) return;

    setErrorMessage(undefined);
    setFinalVideoUrl(null);

    const currentPrefsKey = prefsKey(preferences);
    const hasCache = cachedChoreographyRef.current !== null;
    const prefsUnchanged = hasCache && cachedPrefsKeyRef.current === currentPrefsKey;

    const cachedChoreography = hasCache ? cachedChoreographyRef.current! : undefined;
    const cachedMusicPromptToPass =
      prefsUnchanged && cachedMusicPromptRef.current
        ? cachedMusicPromptRef.current
        : undefined;

    if (!hasCache) setStep("analyzing");
    else if (!prefsUnchanged) setStep("composing");
    else setStep("generating");

    try {
      const agentResponse: RunAgentResponse = await runAgent({
        gcs_uri: gcsUri,
        user_preferences: preferences,
        cached_choreography: cachedChoreography,
        cached_music_prompt: cachedMusicPromptToPass,
      });

      cachedChoreographyRef.current = agentResponse.choreography_json;
      cachedMusicPromptRef.current = agentResponse.music_prompt;
      cachedPrefsKeyRef.current = currentPrefsKey;

      setAnalysisResult(agentResponse.choreography_summary);
      setMusicPrompt(agentResponse.music_prompt);
      setFinalVideoUrl(agentResponse.final_video_signed_url);
      setStep("done");
    } catch (err) {
      setStep("error");
      setErrorMessage(
        err instanceof Error ? err.message : "Generation failed. Please try again."
      );
    }
  }, [gcsUri, preferences]);

  // ── Generate Again ────────────────────────────────────────────────────────
  const handleGenerateAgain = useCallback(() => {
    setFinalVideoUrl(null);
    handleGenerate();
  }, [handleGenerate]);

  // ── Reset ─────────────────────────────────────────────────────────────────
  const handleReset = useCallback(() => {
    setUploadedFile(null);
    setPreviewUrl(null);
    setGcsUri(null);
    setFinalVideoUrl(null);
    setAnalysisResult(null);
    setMusicPrompt(null);
    setErrorMessage(undefined);
    cachedChoreographyRef.current = null;
    cachedMusicPromptRef.current = null;
    cachedPrefsKeyRef.current = null;
    setStep("idle");
  }, []);

  const showUploader = !uploadedFile;
  const showPreview = !!previewUrl;
  const showFinalVideo = !!finalVideoUrl;

  // Running status text
  const runningLabel =
    step !== "idle" && step !== "done" && step !== "error"
      ? STEP_LABELS[step]
      : null;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* ── Header ── */}
      <header className="app-header">
        <Link href="/" className="app-header-wordmark" id="movescore-wordmark-link">
          MoveScore
        </Link>
        <span className="app-header-tagline">Dance first. Music second.</span>
        <div className="app-header-badge">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <circle cx="5" cy="5" r="4" fill="#34d399" opacity="0.85"/>
          </svg>
          Gemini · Lyria 3.5
        </div>
      </header>

      {/* ── Main ── */}
      <main
        style={{
          flex: 1,
          padding: "2rem 1.75rem",
          maxWidth: "1180px",
          margin: "0 auto",
          width: "100%",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 380px",
            gap: "2rem",
            alignItems: "start",
          }}
          className="create-grid"
        >
          {/* ── Left column ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.125rem" }}>

            {/* Upload zone */}
            {showUploader && (
              <VideoUploader
                onFileSelected={handleFileSelected}
                disabled={isRunning}
              />
            )}

            {/* Uploaded video preview */}
            {showPreview && !showFinalVideo && (
              <VideoPreview
                src={previewUrl!}
                label="Your choreography"
                filename={uploadedFile?.name}
              />
            )}

            {/* Final video */}
            {showFinalVideo && (
              <VideoPreview
                src={finalVideoUrl!}
                label="Your video · original soundtrack"
              />
            )}

            {/* Re-upload link */}
            {showPreview && !isRunning && (
              <button
                type="button"
                className="btn-ghost"
                style={{ alignSelf: "flex-start", padding: "0.25rem 0" }}
                onClick={handleReset}
                id="upload-different-video-btn"
              >
                ← Upload a different video
              </button>
            )}

            {/* Status banner */}
            {step !== "idle" && (
              <StatusBanner step={step} errorMessage={errorMessage} />
            )}

            {/* Analysis result */}
            {analysisResult && step !== "error" && (
              <div className="fade-up">
                <AnalysisResult summary={analysisResult} />
              </div>
            )}

            {/* Music prompt preview (collapsible) */}
            {musicPrompt && step === "done" && (
              <details
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                  padding: "0.625rem 0.875rem",
                  background: "var(--surface)",
                  fontSize: "0.8125rem",
                  color: "var(--text-muted)",
                  lineHeight: 1.6,
                }}
              >
                <summary
                  style={{
                    cursor: "pointer",
                    fontWeight: 600,
                    color: "var(--text-light)",
                    fontSize: "0.75rem",
                    letterSpacing: "0.07em",
                    textTransform: "uppercase",
                    userSelect: "none",
                  }}
                >
                  Music direction sent to Lyria
                </summary>
                <p style={{ marginTop: "0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.8125rem", lineHeight: 1.65 }}>
                  {musicPrompt}
                </p>
              </details>
            )}

            {/* Download + Generate Again */}
            {showFinalVideo && (
              <div
                className="fade-up"
                style={{ display: "flex", gap: "0.625rem", flexWrap: "wrap" }}
              >
                <a
                  href={finalVideoUrl!}
                  download="movescore_video.mp4"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                  id="download-video-btn"
                >
                  ↓ Download
                </a>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleGenerateAgain}
                  disabled={isRunning}
                  id="generate-again-btn"
                >
                  ↺ Generate Again
                </button>
              </div>
            )}
          </div>

          {/* ── Right column — Control panel ── */}
          <div className="control-panel-card">
            <ControlPanel
              preferences={preferences}
              onChange={setPreferences}
              disabled={isRunning}
            />

            <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: "0.625rem" }}>
              <button
                type="button"
                className={`btn-generate${isRunning ? " running" : ""}`}
                onClick={handleGenerate}
                disabled={!gcsUri || isRunning}
                id="generate-music-btn"
              >
                {isRunning ? (
                  <>
                    <span className="spinner" />
                    {runningLabel || "Processing…"}
                  </>
                ) : (
                  <>
                    Generate Music
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </>
                )}
              </button>

              {!gcsUri && (
                <div
                  className="text-muted text-small"
                  style={{ textAlign: "center" }}
                >
                  Upload a video to get started
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
