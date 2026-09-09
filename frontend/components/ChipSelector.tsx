/**
 * ChipSelector — HF-style pill chip selector with colored dots + "More" expand.
 *
 * Each chip can have:
 *   - A colored dot (dotColor CSS var or hex)
 *   - A tooltip shown on hover via CSS
 *   - Selected state: light fill with dark text
 *
 * Deselect by clicking the selected chip again.
 */

"use client";

import { useState } from "react";

export interface ChipOption {
  label: string;
  tooltip?: string;
  dotColor?: string; // CSS color string e.g. "#f472b6" or "var(--dot-pop)"
}

interface ChipSelectorProps {
  options: ChipOption[];
  selected: string | null;
  onSelect: (value: string | null) => void;
  initialVisibleCount?: number;
}

export default function ChipSelector({
  options,
  selected,
  onSelect,
  initialVisibleCount = 6,
}: ChipSelectorProps) {
  const [expanded, setExpanded] = useState(false);

  const visible = expanded ? options : options.slice(0, initialVisibleCount);
  const hiddenCount = options.length - initialVisibleCount;

  const handleClick = (label: string) => {
    onSelect(selected === label ? null : label);
  };

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem", alignItems: "center" }}>
      {visible.map((opt) => {
        const isSelected = selected === opt.label;
        return (
          <div key={opt.label} className="chip-wrap">
            <button
              type="button"
              className={`chip${isSelected ? " selected" : ""}`}
              onClick={() => handleClick(opt.label)}
              aria-pressed={isSelected}
            >
              {opt.dotColor && (
                <span
                  className="chip-dot"
                  style={{
                    background: opt.dotColor,
                    // When selected, the background is light so make dot slightly darker/opaque
                    opacity: isSelected ? 0.8 : 0.75,
                    filter: isSelected ? "saturate(0.7) brightness(0.7)" : "none",
                  }}
                />
              )}
              {opt.label}
            </button>
            {opt.tooltip && (
              <span className="chip-tooltip" role="tooltip">
                {opt.tooltip}
              </span>
            )}
          </div>
        );
      })}

      {hiddenCount > 0 && (
        <button
          type="button"
          className="chip-more"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          {expanded ? "Show less" : `+${hiddenCount} more`}
        </button>
      )}
    </div>
  );
}
