/**
 * AnalysisResult — Choreography analysis display with movement timeline.
 *
 * Shows:
 * - Moment count + confidence badge
 * - BPM estimate
 * - Visual timeline: colored dots connected by lines (●────●────●)
 * - Moment legend chips
 * - Low-confidence warning if needed
 */

"use client";

import type { ChoreographySummary } from "@/lib/types";

interface AnalysisResultProps {
  summary: ChoreographySummary;
}

// Map moment label keywords to dot colors (timeline dots)
const TYPE_COLORS: Record<string, string> = {
  accent:     "#60a5fa",
  hit:        "#60a5fa",
  spin:       "#a78bfa",
  jump:       "#34d399",
  freeze:     "#f87171",
  buildup:    "#fbbf24",
  build:      "#fbbf24",
  drop:       "#f472b6",
  climax:     "#e879f9",
  final:      "#67e8f9",
  pose:       "#67e8f9",
  transition: "#94a3b8",
};

function dotColorForLabel(label: string): string {
  const lower = label.toLowerCase();
  for (const [key, color] of Object.entries(TYPE_COLORS)) {
    if (lower.includes(key)) return color;
  }
  return "#5a5f6f";
}

export default function AnalysisResult({ summary }: AnalysisResultProps) {
  const moments = summary.moment_labels;
  const confidence = summary.analysis_confidence ?? "high";

  const confidenceClass =
    confidence === "high" ? "high"
    : confidence === "medium" ? "medium"
    : "low";

  const confidenceLabel =
    confidence === "high" ? "High confidence"
    : confidence === "medium" ? "Medium confidence"
    : "Low confidence";

  return (
    <div className="analysis-card">
      {/* Header row */}
      <div className="analysis-header">
        <span
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: "var(--status-ready)",
            flexShrink: 0,
            boxShadow: "0 0 6px var(--status-ready)",
          }}
        />
        <span style={{ fontSize: "0.875rem", fontWeight: 600 }}>
          {summary.moment_count} movement moment
          {summary.moment_count !== 1 ? "s" : ""} detected
        </span>

        {summary.movement_tempo_bpm && (
          <span
            className="text-small"
            style={{
              color: "var(--text-light)",
              fontFamily: "var(--font-mono)",
              marginLeft: "auto",
              paddingRight: "0.25rem",
            }}
          >
            ~{summary.movement_tempo_bpm} BPM
          </span>
        )}

        <span className={`analysis-badge ${confidenceClass}`}>
          {confidenceLabel}
        </span>
      </div>

      {/* Timeline: ●────●────●────● */}
      {moments.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <div className="section-label" style={{ marginBottom: "0.5rem" }}>
            Movement timeline
          </div>
          <div className="timeline">
            {moments.map((label, i) => {
              const color = dotColorForLabel(label);
              return (
                <div key={i} style={{ display: "flex", alignItems: "center" }}>
                  {i > 0 && <div className="timeline-line" />}
                  <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                    <div
                      className="timeline-dot"
                      title={label}
                      style={{
                        background: color,
                        boxShadow: `0 0 4px ${color}80`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Moment legend chips */}
      {moments.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3125rem" }}>
          {moments.map((label, i) => (
            <span key={i} className="moment-tag">
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: dotColorForLabel(label),
                  flexShrink: 0,
                  display: "inline-block",
                }}
              />
              {label}
            </span>
          ))}
        </div>
      )}

      {/* Low confidence warning */}
      {summary.low_confidence_warning && (
        <div className="warning-box" style={{ marginTop: "0.75rem" }}>
          ⚠ Some fast movements may not have been fully captured — Gemini samples
          video at ~1 FPS. The music will still reflect the overall energy structure.
        </div>
      )}
    </div>
  );
}
