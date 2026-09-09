"use client";

/**
 * /create — Main application page.
 *
 * Two-column layout:
 *   Left:  Video upload / preview + status + analysis result
 *   Right: Creative controls + Generate button
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

// Stable JSON comparison for detecting preference changes
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

export default function CreatePage() {
  const [step, setStep] = useState<PipelineStep>("idle");
  const [errorMessage, setErrorMessage] = useState<string | undefined>();

  // Uploaded video
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [gcsUri, setGcsUri] = useState<string | null>(null);

  // User preferences
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFS);

  // Results
  const [analysisResult, setAnalysisResult] = useState<ChoreographySummary | null>(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);
  const [musicPrompt, setMusicPrompt] = useState<string | null>(null);

  // Cache for Generate Again
  const cachedChoreographyRef = useRef<Record<string, unknown> | null>(null);
  const cachedMusicPromptRef = useRef<string | null>(null);
  const cachedPrefsKeyRef = useRef<string | null>(null);

  const isRunning = !["idle", "done", "error"].includes(step);

  // ── Upload ─────────────────────────────────────────────────────────────────
  const handleFileSelected = useCallback(async (file: File) => {
    setErrorMessage(undefined);
    setStep("uploading");
    setFinalVideoUrl(null);
    setAnalysisResult(null);
    cachedChoreographyRef.current = null;
    cachedMusicPromptRef.current = null;
    cachedPrefsKeyRef.current = null;

    // Create a local object URL for immediate preview
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

  // ── Generate ────────────────────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    if (!gcsUri) return;

    setErrorMessage(undefined);
    setFinalVideoUrl(null);

    const currentPrefsKey = prefsKey(preferences);
    const hasCache = cachedChoreographyRef.current !== null;
    const prefsUnchanged =
      hasCache && cachedPrefsKeyRef.current === currentPrefsKey;

    // Determine what to pass from cache
    const cachedChoreography = hasCache ? cachedChoreographyRef.current! : undefined;
    const cachedMusicPromptToPass =
      prefsUnchanged && cachedMusicPromptRef.current
        ? cachedMusicPromptRef.current
        : undefined;

    // Show appropriate status for what will happen
    if (!hasCache) {
      setStep("analyzing");
    } else if (!prefsUnchanged) {
      setStep("composing");
    } else {
      setStep("generating");
    }

    try {
      // The backend runs the full agent synchronously.
      // We set step labels progressively as we know what stage we're in.
      const agentResponse: RunAgentResponse = await runAgent({
        gcs_uri: gcsUri,
        user_preferences: preferences,
        cached_choreography: cachedChoreography,
        cached_music_prompt: cachedMusicPromptToPass,
      });

      // Cache results for Generate Again
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

  // ── Generate Again ──────────────────────────────────────────────────────────
  const handleGenerateAgain = useCallback(() => {
    setFinalVideoUrl(null);
    // Keep cached choreography — will be re-used unless prefs changed
    handleGenerate();
  }, [handleGenerate]);

  // ── Render ──────────────────────────────────────────────────────────────────
  const showUploader = !uploadedFile;
  const showPreview = !!previewUrl;
  const showFinalVideo = !!finalVideoUrl;

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          padding: "0.875rem 1.5rem",
          display: "flex",
          alignItems: "center",
          gap: "1rem",
        }}
      >
        <Link
          href="/"
          style={{
            fontSize: "0.8125rem",
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--text)",
          }}
        >
          Agentic Cinema
        </Link>
        <span className="text-light text-small">Dance first. Music second.</span>
      </header>

      {/* Main content */}
      <main
        style={{
          flex: 1,
          padding: "2rem 1.5rem",
          maxWidth: "1160px",
          margin: "0 auto",
          width: "100%",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 380px",
            gap: "2.5rem",
            alignItems: "start",
          }}
          className="create-grid"
        >
          {/* ── Left column ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Upload zone */}
            {showUploader && (
              <VideoUploader
                onFileSelected={handleFileSelected}
                disabled={isRunning}
              />
            )}

            {/* Uploaded video preview (before final) */}
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
                label="Your video with original soundtrack"
              />
            )}

            {/* Re-upload link */}
            {showPreview && !isRunning && (
              <button
                type="button"
                className="btn-ghost"
                style={{ alignSelf: "flex-start", padding: "0.25rem 0" }}
                onClick={() => {
                  setUploadedFile(null);
                  setPreviewUrl(null);
                  setGcsUri(null);
                  setFinalVideoUrl(null);
                  setAnalysisResult(null);
                  cachedChoreographyRef.current = null;
                  cachedMusicPromptRef.current = null;
                  cachedPrefsKeyRef.current = null;
                  setStep("idle");
                }}
              >
                ← Upload a different video
              </button>
            )}

            {/* Status */}
            {step !== "idle" && (
              <StatusBanner step={step} errorMessage={errorMessage} />
            )}

            {/* Analysis result */}
            {analysisResult && step !== "error" && (
              <AnalysisResult summary={analysisResult} />
            )}

            {/* Download + Generate Again */}
            {showFinalVideo && (
              <div style={{ display: "flex", gap: "0.625rem", flexWrap: "wrap" }}>
                <a
                  href={finalVideoUrl!}
                  download="choreography_with_music.mp4"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                >
                  ↓ Download Video
                </a>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleGenerateAgain}
                  disabled={isRunning}
                >
                  ↺ Generate Again
                </button>
              </div>
            )}
          </div>

          {/* ── Right column ── */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "1.5rem",
              padding: "1.25rem",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              background: "var(--surface)",
              position: "sticky",
              top: "1.5rem",
            }}
          >
            <ControlPanel
              preferences={preferences}
              onChange={setPreferences}
              disabled={isRunning}
            />

            <button
              type="button"
              className="btn btn-primary"
              onClick={handleGenerate}
              disabled={!gcsUri || isRunning}
              style={{ width: "100%", justifyContent: "center" }}
            >
              {isRunning ? "Generating..." : "Generate Music →"}
            </button>

            {!gcsUri && (
              <div className="text-muted text-small" style={{ textAlign: "center" }}>
                Upload a video to get started
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Responsive styles */}
      <style>{`
        @media (max-width: 720px) {
          .create-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
