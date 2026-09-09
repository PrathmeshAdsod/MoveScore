/**
 * VideoUploader — Drag-and-drop / click-to-upload video component.
 * Dark premium style matching MoveScore design system.
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
        id="video-upload-zone"
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            inputRef.current?.click();
          }
        }}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={`drop-zone${dragOver ? " dragover" : ""}${disabled ? " disabled" : ""}`}
      >
        {/* Film strip icon */}
        <div className="drop-zone-icon">
          <svg width="44" height="44" viewBox="0 0 44 44" fill="none" aria-hidden="true">
            <rect x="2" y="8" width="40" height="28" rx="4" stroke="currentColor" strokeWidth="1.5" fill="none" opacity="0.35"/>
            <rect x="2" y="8" width="6" height="4" rx="1" fill="currentColor" opacity="0.4"/>
            <rect x="2" y="16" width="6" height="4" rx="1" fill="currentColor" opacity="0.4"/>
            <rect x="2" y="24" width="6" height="4" rx="1" fill="currentColor" opacity="0.4"/>
            <rect x="2" y="32" width="6" height="4" rx="1" fill="currentColor" opacity="0.4"/>
            <rect x="36" y="8" width="6" height="4" rx="1" fill="currentColor" opacity="0.4"/>
            <rect x="36" y="16" width="6" height="4" rx="1" fill="currentColor" opacity="0.4"/>
            <rect x="36" y="24" width="6" height="4" rx="1" fill="currentColor" opacity="0.4"/>
            <rect x="36" y="32" width="6" height="4" rx="1" fill="currentColor" opacity="0.4"/>
            {/* Play triangle */}
            <path d="M18 17l10 5-10 5V17z" fill="currentColor" opacity="0.55"/>
          </svg>
        </div>

        <div className="drop-zone-primary">
          {dragOver ? "Drop to upload" : "Drop your choreography here"}
        </div>
        <div className="drop-zone-secondary">
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
        id="video-file-input"
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
