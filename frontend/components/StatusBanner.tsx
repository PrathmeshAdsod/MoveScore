/**
 * StatusBanner — Pipeline step indicator with spinner and step-specific color.
 * Sits below the video uploader/preview in the left column.
 */

"use client";

import type { PipelineStep } from "@/lib/types";

const STEP_CONFIG: Record<
  PipelineStep,
  { label: string; color: string; showSpinner: boolean }
> = {
  idle:       { label: "",                                         color: "var(--text-muted)",       showSpinner: false },
  uploading:  { label: "Uploading video to cloud storage…",        color: "var(--text-muted)",       showSpinner: true  },
  analyzing:  { label: "Analysing choreography with Gemini…",      color: "var(--status-analyzing)", showSpinner: true  },
  composing:  { label: "Composing music direction…",               color: "var(--status-composing)", showSpinner: true  },
  generating: { label: "Generating music with Lyria 3.5…",         color: "var(--status-composing)", showSpinner: true  },
  combining:  { label: "Combining video and audio with FFmpeg…",   color: "var(--text-muted)",       showSpinner: true  },
  done:       { label: "Ready — your soundtrack is composed.",      color: "var(--status-ready)",     showSpinner: false },
  error:      { label: "Something went wrong.",                    color: "var(--error)",            showSpinner: false },
};

interface StatusBannerProps {
  step: PipelineStep;
  errorMessage?: string;
}

export default function StatusBanner({ step, errorMessage }: StatusBannerProps) {
  if (step === "idle") return null;

  const cfg = STEP_CONFIG[step];

  return (
    <div
      role="status"
      aria-live="polite"
      className="status-banner fade-up"
      style={{ color: cfg.color, borderColor: step === "error" ? "rgba(248,113,113,0.25)" : undefined }}
    >
      {cfg.showSpinner && (
        <span className="spinner" aria-hidden="true" style={{ color: cfg.color }} />
      )}
      {!cfg.showSpinner && (
        <span
          style={{
            width: "7px",
            height: "7px",
            borderRadius: "50%",
            background: cfg.color,
            flexShrink: 0,
            boxShadow: step === "done" ? `0 0 6px ${cfg.color}` : "none",
          }}
          className={step === "done" ? "" : "status-dot-pulse"}
        />
      )}
      <span style={{ fontWeight: 500 }}>
        {step === "error" && errorMessage ? errorMessage : cfg.label}
      </span>
    </div>
  );
}
