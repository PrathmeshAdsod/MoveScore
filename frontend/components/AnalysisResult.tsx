/**
 * AnalysisResult — Compact UI display of choreography analysis.
 * Shows only what the user needs — internal JSON stays hidden.
 */

"use client";

import type { ChoreographySummary } from "@/lib/types";

interface AnalysisResultProps {
  summary: ChoreographySummary;
}

export default function AnalysisResult({ summary }: AnalysisResultProps) {
  const labels = summary.moment_labels.join(" → ");

  return (
    <div
      style={{
        padding: "0.75rem 1rem",
        borderRadius: "var(--radius)",
        border: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          marginBottom: labels ? "0.375rem" : 0,
        }}
      >
        <span
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: "var(--status-ready)",
            flexShrink: 0,
          }}
        />
        <span style={{ fontSize: "0.875rem", fontWeight: 600 }}>
          {summary.moment_count} movement moment
          {summary.moment_count !== 1 ? "s" : ""} detected
        </span>
        {summary.movement_tempo_bpm && (
          <span
            className="text-muted text-small"
            style={{ marginLeft: "auto" }}
          >
            ~{summary.movement_tempo_bpm} BPM
          </span>
        )}
      </div>

      {labels && (
        <div
          className="text-muted text-small text-mono"
          style={{ paddingLeft: "1.25rem" }}
        >
          {labels}
        </div>
      )}

      {summary.low_confidence_warning && (
        <div className="warning-box" style={{ marginTop: "0.625rem" }}>
          ⚠ Some fast movements may not have been fully captured (Gemini samples
          video at ~1 FPS). The music will still reflect the overall energy
          structure.
        </div>
      )}
    </div>
  );
}
