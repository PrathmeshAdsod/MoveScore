/**
 * VideoUploader — Drag-and-drop / click-to-upload video component.
 * Shows a preview after upload and file metadata.
 */

"use client";

import { useCallback, useRef, useState } from "react";

interface VideoUploaderProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED = ["video/mp4", "video/quicktime", "video/webm"];
const MAX_MB = 100;

export default function VideoUploader({
  onFileSelected,
  disabled = false,
}: VideoUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (file: File): string | null => {
    if (!ACCEPTED.includes(file.type) && !file.name.match(/\.(mp4|mov|webm)$/i)) {
      return "Please upload an MP4, MOV, or WebM video file.";
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      return `File is too large. Maximum size is ${MAX_MB} MB.`;
    }
    if (file.size === 0) {
      return "The selected file is empty.";
    }
    return null;
  };

  const handleFile = useCallback(
    (file: File) => {
      setError(null);
      const err = validate(file);
      if (err) {
        setError(err);
        return;
      }
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = () => setDragOver(false);

  return (
    <div>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload dance video"
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            inputRef.current?.click();
          }
        }}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        style={{
          border: `2px dashed ${dragOver ? "var(--text-muted)" : "var(--border)"}`,
          borderRadius: "var(--radius)",
          padding: "3rem 2rem",
          textAlign: "center",
          cursor: disabled ? "not-allowed" : "pointer",
          background: dragOver ? "var(--surface)" : "var(--bg)",
          transition: "all 150ms ease",
          opacity: disabled ? 0.5 : 1,
        }}
      >
        <div style={{ fontSize: "2rem", marginBottom: "0.75rem", lineHeight: 1 }}>
          ↑
        </div>
        <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
          Drop your dance video here
        </div>
        <div className="text-muted text-small">
          or click to browse · MP4, MOV, WebM · max {MAX_MB} MB
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm"
        onChange={onInputChange}
        style={{ display: "none" }}
        disabled={disabled}
      />

      {error && (
        <div
          style={{
            marginTop: "0.5rem",
            color: "var(--error)",
            fontSize: "0.8125rem",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
