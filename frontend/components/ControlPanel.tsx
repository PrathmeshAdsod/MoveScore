/**
 * ControlPanel — Right-column creative controls.
 *
 * Groups: Output, Style, Mood, Energy, Movement Feel, Optional text.
 * Compact chip-based layout with "+ More" expand for large catalogs.
 */

"use client";

import ChipSelector from "./ChipSelector";
import type { UserPreferences } from "@/lib/types";

const STYLES = [
  "Pop",
  "Dance Pop",
  "Hip-hop",
  "Afrobeat",
  "House",
  "R&B",
  "Amapiano",
  "Trap",
  "Deep House",
  "Tech House",
  "EDM",
  "Electronic",
  "Disco",
  "Funk",
  "Latin",
  "Reggaeton",
  "Indian Pop",
  "Cinematic",
  "Rock",
  "Lo-fi",
  "Ambient",
  "Experimental",
];

const MOODS = [
  "Confident",
  "Powerful",
  "Playful",
  "Euphoric",
  "Dark",
  "Energetic",
  "Mysterious",
  "Aggressive",
  "Dramatic",
  "Dreamy",
  "Romantic",
  "Emotional",
  "Melancholic",
  "Rebellious",
  "Elegant",
  "Chill",
  "Futuristic",
];

const MOVEMENT_FEELS = [
  "Smooth",
  "Punchy",
  "Groovy",
  "Sharp",
  "Flowing",
  "Heavy",
  "Bouncy",
  "Minimal",
];

const ENERGY_LEVELS = ["Soft", "Medium", "High"] as const;

interface ControlPanelProps {
  preferences: UserPreferences;
  onChange: (prefs: UserPreferences) => void;
  disabled?: boolean;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        display: "block",
        fontSize: "0.6875rem",
        fontWeight: 600,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: "var(--text-light)",
        marginBottom: "0.5rem",
      }}
    >
      {children}
    </span>
  );
}

export default function ControlPanel({
  preferences,
  onChange,
  disabled = false,
}: ControlPanelProps) {
  const update = (patch: Partial<UserPreferences>) =>
    onChange({ ...preferences, ...patch });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem",
        opacity: disabled ? 0.6 : 1,
        pointerEvents: disabled ? "none" : "auto",
      }}
    >
      {/* OUTPUT */}
      <div>
        <SectionLabel>Output</SectionLabel>
        <div style={{ display: "flex", gap: "0.375rem" }}>
          {(["instrumental", "song"] as const).map((type) => (
            <button
              key={type}
              type="button"
              className={`chip${preferences.output_type === type ? " selected" : ""}`}
              onClick={() => update({ output_type: type })}
              aria-pressed={preferences.output_type === type}
            >
              {type === "instrumental" ? "Instrumental" : "Song / Vocals"}
            </button>
          ))}
        </div>
      </div>

      {/* STYLE */}
      <div>
        <SectionLabel>Style</SectionLabel>
        <ChipSelector
          options={STYLES}
          selected={preferences.style ?? null}
          onSelect={(v) => update({ style: v ?? undefined })}
          initialVisibleCount={6}
        />
      </div>

      {/* MOOD */}
      <div>
        <SectionLabel>Mood</SectionLabel>
        <ChipSelector
          options={MOODS}
          selected={preferences.mood ?? null}
          onSelect={(v) => update({ mood: v ?? undefined })}
          initialVisibleCount={6}
        />
      </div>

      {/* ENERGY */}
      <div>
        <SectionLabel>Energy</SectionLabel>
        <div style={{ display: "flex", gap: "0.375rem" }}>
          {ENERGY_LEVELS.map((level) => (
            <button
              key={level}
              type="button"
              className={`chip${
                (preferences.energy ?? "").toLowerCase() === level.toLowerCase()
                  ? " selected"
                  : ""
              }`}
              onClick={() =>
                update({ energy: level.toLowerCase() as UserPreferences["energy"] })
              }
              aria-pressed={
                (preferences.energy ?? "").toLowerCase() === level.toLowerCase()
              }
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      {/* MOVEMENT FEEL */}
      <div>
        <SectionLabel>Movement Feel</SectionLabel>
        <ChipSelector
          options={MOVEMENT_FEELS}
          selected={preferences.movement_feel ?? null}
          onSelect={(v) => update({ movement_feel: v ?? undefined })}
          initialVisibleCount={4}
        />
      </div>

      {/* CUSTOM INSTRUCTION */}
      <div>
        <SectionLabel>Anything else?</SectionLabel>
        <textarea
          rows={2}
          maxLength={300}
          placeholder='e.g. "Make the freeze dramatic." or "Hit harder when I spin."'
          value={preferences.custom_instruction ?? ""}
          onChange={(e) =>
            update({ custom_instruction: e.target.value || undefined })
          }
          style={{ fontSize: "0.875rem" }}
        />
        {preferences.custom_instruction && (
          <div
            style={{
              textAlign: "right",
              fontSize: "0.75rem",
              color: "var(--text-light)",
              marginTop: "0.25rem",
            }}
          >
            {preferences.custom_instruction.length}/300
          </div>
        )}
      </div>
    </div>
  );
}
