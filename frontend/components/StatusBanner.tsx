/**
 * StatusBanner — Shows current pipeline step with progress indicator.
 */

"use client";

import type { PipelineStep } from "@/lib/types";

const STEP_CONFIG: Record<
  PipelineStep,
  { label: string; color: string; showSpinner: boolean }
> = {
  idle: { label: "", color: "var(--text-muted)", showSpinner: false },
  uploading: {
    label: "Uploading video...",
    color: "var(--text-muted)",
    showSpinner: true,
  },
  analyzing: {
    label: "Analyzing choreography...",
    color: "var(--status-analyzing)",
    showSpinner: true,
  },
  composing: {
    label: "Composing music plan...",
    color: "var(--status-composing)",
    showSpinner: true,
  },
  generating: {
    label: "Generating music with Lyria...",
    color: "var(--status-composing)",
    showSpinner: true,
  },
  combining: {
    label: "Preparing your video...",
    color: "var(--text-muted)",
    showSpinner: true,
  },
  done: { label: "Done!", color: "var(--status-ready)", showSpinner: false },
  error: { label: "Something went wrong.", color: "var(--error)", showSpinner: false },
};

interface StatusBannerProps {
  step: PipelineStep;
  errorMessage?: string;
}

export default function StatusBanner({ step, errorMessage }: StatusBannerProps) {
  if (step === "idle") return null;

  const config = STEP_CONFIG[step];

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.625rem",
        padding: "0.625rem 0.875rem",
        borderRadius: "var(--radius)",
        border: "1px solid var(--border)",
        background: "var(--surface)",
        fontSize: "0.875rem",
        color: config.color,
      }}
    >
      {config.showSpinner && (
        <span
          aria-hidden="true"
          style={{
            display: "inline-block",
            width: "14px",
            height: "14px",
            border: `2px solid ${config.color}`,
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
            flexShrink: 0,
          }}
        />
      )}
      <span>
        {step === "error" && errorMessage ? errorMessage : config.label}
      </span>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
