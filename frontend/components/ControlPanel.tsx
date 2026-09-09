/**
 * ControlPanel — Right-column creative controls.
 *
 * Groups: Output, Style, Mood, Energy, Movement Feel, Optional text.
 * Chips have HF-style colored dots (genre/mood identity colors).
 * Each chip has a 1-2 sentence tooltip shown on hover.
 */

"use client";

import ChipSelector, { type ChipOption } from "./ChipSelector";
import type { UserPreferences } from "@/lib/types";

const STYLES: ChipOption[] = [
  { label: "Pop",          dotColor: "var(--dot-pop)",          tooltip: "Bright, melodic pop with hooky rhythms and polished production." },
  { label: "Dance Pop",    dotColor: "var(--dot-dance)",        tooltip: "Uptempo pop built for movement — four-on-the-floor pulse, punchy hooks." },
  { label: "Hip-hop",      dotColor: "var(--dot-hiphop)",       tooltip: "Boom-bap or modern trap-influenced beats with a strong rhythmic backbone." },
  { label: "Afrobeat",     dotColor: "var(--dot-afrobeat)",     tooltip: "West African-inspired rhythms, syncopated percussion, and warm horn stabs." },
  { label: "House",        dotColor: "var(--dot-house)",        tooltip: "Classic four-on-the-floor house groove with soulful chords and steady kick." },
  { label: "R&B",          dotColor: "var(--dot-rnb)",          tooltip: "Smooth, soulful production with lush chords and expressive groove." },
  { label: "Amapiano",     dotColor: "var(--dot-amapiano)",     tooltip: "South African log-drum bass, jazzy keys, and laid-back club energy." },
  { label: "Trap",         dotColor: "var(--dot-trap)",         tooltip: "Hi-hat triplets, 808 bass, and heavy sub-bass drops." },
  { label: "Deep House",   dotColor: "var(--dot-deep)",         tooltip: "Deeper, warmer house with organic textures and a subtle late-night feel." },
  { label: "Tech House",   dotColor: "var(--dot-tech)",         tooltip: "Groovy, stripped-back house with a mechanical, club-floor edge." },
  { label: "EDM",          dotColor: "var(--dot-edm)",          tooltip: "High-energy electronic with big build-ups, hard drops, and euphoric synths." },
  { label: "Electronic",   dotColor: "var(--dot-electronic)",   tooltip: "Broad electronic palette — synth-driven, textured, and modern." },
  { label: "Disco",        dotColor: "var(--dot-disco)",        tooltip: "Funky bass lines, orchestral strings, and a warm 70s dancefloor vibe." },
  { label: "Funk",         dotColor: "var(--dot-funk)",         tooltip: "Tight rhythmic interplay, slap bass, and rhythmically precise chord stabs." },
  { label: "Latin",        dotColor: "var(--dot-latin)",        tooltip: "Infectious Latin rhythms — salsa, reggaeton, or cumbia-influenced grooves." },
  { label: "Reggaeton",    dotColor: "var(--dot-reggaeton)",    tooltip: "Dembow rhythm, rolling bass, and urban Latin energy." },
  { label: "Indian Pop",   dotColor: "var(--dot-indian)",       tooltip: "Bollywood-influenced melodies with tabla percussion and rich harmonics." },
  { label: "Cinematic",    dotColor: "var(--dot-cinematic)",    tooltip: "Orchestral, sweeping, and emotionally driven — built around the movement arc." },
  { label: "Rock",         dotColor: "var(--dot-rock)",         tooltip: "Guitar-driven energy with driving drums and powerful dynamics." },
  { label: "Lo-fi",        dotColor: "var(--dot-lofi)",         tooltip: "Warm, relaxed beats with vinyl texture and a hazy, intimate feel." },
  { label: "Ambient",      dotColor: "var(--dot-ambient)",      tooltip: "Expansive, atmosphere-first — texture and space over rhythm." },
  { label: "Experimental", dotColor: "var(--dot-experimental)", tooltip: "Unconventional sound design and structure — for bold, unexpected results." },
];

const MOODS: ChipOption[] = [
  { label: "Confident",   tooltip: "Assured, self-possessed energy — strong without being aggressive." },
  { label: "Powerful",    tooltip: "Heavy, commanding presence with dynamic intensity." },
  { label: "Playful",     tooltip: "Light-hearted, fun, and bouncy — keeps things from feeling too serious." },
  { label: "Euphoric",    tooltip: "Peak positive emotion — uplifting, joyful, and celebratory." },
  { label: "Dark",        tooltip: "Brooding undertones, shadowy texture, and serious tension." },
  { label: "Energetic",   tooltip: "High-octane, continuously forward-moving momentum." },
  { label: "Mysterious",  tooltip: "Unsettled, curious tension — something about to be revealed." },
  { label: "Aggressive",  tooltip: "Raw, forceful, and intense — no restraint." },
  { label: "Dramatic",    tooltip: "High emotional stakes, sweeping builds, and cinematic contrast." },
  { label: "Dreamy",      tooltip: "Hazy, soft-edged, and slightly surreal — floats above the ground." },
  { label: "Romantic",    tooltip: "Warm, intimate, and emotionally expressive." },
  { label: "Emotional",   tooltip: "Vulnerable, heartfelt, and deeply expressive — leans into feeling." },
  { label: "Melancholic", tooltip: "Bittersweet sadness — beauty and ache at the same time." },
  { label: "Rebellious",  tooltip: "Anti-authority energy with attitude and edge." },
  { label: "Elegant",     tooltip: "Refined, graceful, and tastefully restrained." },
  { label: "Chill",       tooltip: "Relaxed and unhurried — movement feels effortless." },
  { label: "Futuristic",  tooltip: "Forward-looking, synthetic, and otherworldly in texture." },
];

const MOVEMENT_FEELS: ChipOption[] = [
  { label: "Smooth",   tooltip: "Fluid, connected movement — music flows continuously without sharp edges." },
  { label: "Punchy",   tooltip: "Sharp attack on accents — music hits hard on strong movement moments." },
  { label: "Groovy",   tooltip: "Rhythmically syncopated feel — music has a natural swing and bounce." },
  { label: "Sharp",    tooltip: "Precise, defined accents — clean stabs with clear musical edges." },
  { label: "Flowing",  tooltip: "Continuous, legato energy — movement and music breathe together." },
  { label: "Heavy",    tooltip: "Dense low-end weight — bass-forward with a physical, grounded feel." },
  { label: "Bouncy",   tooltip: "Light, springy rhythm — music lifts and rebounds on every beat." },
  { label: "Minimal",  tooltip: "Stripped back — space and silence are as important as sound." },
];

const ENERGY_LEVELS = ["Soft", "Medium", "High"] as const;

const ENERGY_TOOLTIPS: Record<string, string> = {
  Soft:   "Gentle, understated dynamics — music stays controlled and intimate.",
  Medium: "Balanced energy — punchy where needed but with room to breathe.",
  High:   "Full intensity throughout — driving, loud, and unrelenting.",
};

interface ControlPanelProps {
  preferences: UserPreferences;
  onChange: (prefs: UserPreferences) => void;
  disabled?: boolean;
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
        opacity: disabled ? 0.4 : 1,
        pointerEvents: disabled ? "none" : "auto",
        transition: "opacity 140ms ease",
      }}
    >
      {/* OUTPUT */}
      <div>
        <span className="section-label">Output</span>
        <div style={{ display: "flex", gap: "0.375rem" }}>
          {(["instrumental", "song"] as const).map((type) => (
            <div key={type} className="chip-wrap">
              <button
                type="button"
                className={`chip${preferences.output_type === type ? " selected" : ""}`}
                onClick={() => update({ output_type: type })}
                aria-pressed={preferences.output_type === type}
                id={`output-type-${type}-btn`}
              >
                {type === "instrumental" ? "Instrumental" : "Song / Vocals"}
              </button>
              <span className="chip-tooltip" role="tooltip">
                {type === "instrumental"
                  ? "AI composes a fully arranged instrumental track — no lyrics, no voice."
                  : "Lyria adds a vocal layer with melodic phrasing around the choreography structure."}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* STYLE */}
      <div>
        <span className="section-label">Style</span>
        <ChipSelector
          options={STYLES}
          selected={preferences.style ?? null}
          onSelect={(v) => update({ style: v ?? undefined })}
          initialVisibleCount={6}
        />
      </div>

      {/* MOOD */}
      <div>
        <span className="section-label">Mood</span>
        <ChipSelector
          options={MOODS}
          selected={preferences.mood ?? null}
          onSelect={(v) => update({ mood: v ?? undefined })}
          initialVisibleCount={6}
        />
      </div>

      {/* ENERGY */}
      <div>
        <span className="section-label">Energy</span>
        <div style={{ display: "flex", gap: "0.375rem" }}>
          {ENERGY_LEVELS.map((level) => (
            <div key={level} className="chip-wrap">
              <button
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
                id={`energy-${level.toLowerCase()}-btn`}
              >
                {level}
              </button>
              <span className="chip-tooltip" role="tooltip">
                {ENERGY_TOOLTIPS[level]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* MOVEMENT FEEL */}
      <div>
        <span className="section-label">Movement Feel</span>
        <ChipSelector
          options={MOVEMENT_FEELS}
          selected={preferences.movement_feel ?? null}
          onSelect={(v) => update({ movement_feel: v ?? undefined })}
          initialVisibleCount={4}
        />
      </div>

      {/* CUSTOM INSTRUCTION */}
      <div>
        <span className="section-label">Anything else?</span>
        <textarea
          rows={2}
          maxLength={300}
          placeholder={'"Make the freeze dramatic." · "Hit harder when I spin."'}
          value={preferences.custom_instruction ?? ""}
          onChange={(e) =>
            update({ custom_instruction: e.target.value || undefined })
          }
          style={{ fontSize: "0.875rem" }}
          id="custom-instruction-input"
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
