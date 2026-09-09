/**
 * VideoPreview — Shows the uploaded or final video in a dark card.
 */

"use client";

interface VideoPreviewProps {
  src: string;
  label?: string;
  filename?: string;
}

export default function VideoPreview({ src, label, filename }: VideoPreviewProps) {
  return (
    <div className="video-card">
      <video
        src={src}
        controls
        playsInline
        id="video-preview-player"
      />
      {(label || filename) && (
        <div className="video-card-label">
          {label && (
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "var(--text-light)",
              }}
            >
              {label}
            </span>
          )}
          {filename && (
            <span
              className="text-small"
              style={{ color: "var(--text-light)", marginLeft: label ? "auto" : 0 }}
            >
              {filename}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
