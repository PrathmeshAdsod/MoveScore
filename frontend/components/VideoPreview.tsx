/**
 * VideoPreview — Shows the uploaded or final video with player controls.
 */

"use client";

interface VideoPreviewProps {
  src: string;
  label?: string;
  filename?: string;
}

export default function VideoPreview({ src, label, filename }: VideoPreviewProps) {
  return (
    <div>
      {label && (
        <div
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            color: "var(--text-light)",
            marginBottom: "0.5rem",
          }}
        >
          {label}
        </div>
      )}
      <video
        src={src}
        controls
        playsInline
        style={{
          width: "100%",
          borderRadius: "var(--radius)",
          border: "1px solid var(--border)",
          background: "#000",
          display: "block",
          maxHeight: "480px",
          objectFit: "contain",
        }}
      />
      {filename && (
        <div
          className="text-muted text-small"
          style={{ marginTop: "0.375rem" }}
        >
          {filename}
        </div>
      )}
    </div>
  );
}
