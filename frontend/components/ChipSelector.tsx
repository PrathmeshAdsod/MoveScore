/**
 * ChipSelector — Compact pill/chip selector with "+ More" expand.
 *
 * Matches the Hugging Face provider selector style from the reference image:
 * - Small rounded pills with subtle border
 * - Selected: dark filled background
 * - Hover: slightly darker surface
 * - First N items visible; "+ X more" expands inline
 * - Optional 1-2 sentence tooltip shown on hover via CSS .chip-wrap / .chip-tooltip
 */

"use client";

import { useState } from "react";

export interface ChipOption {
  label: string;
  tooltip?: string;
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
      {visible.map((opt) => (
        <div key={opt.label} className="chip-wrap">
          <button
            type="button"
            className={`chip${selected === opt.label ? " selected" : ""}`}
            onClick={() => handleClick(opt.label)}
            aria-pressed={selected === opt.label}
          >
            {opt.label}
          </button>
          {opt.tooltip && (
            <span className="chip-tooltip" role="tooltip">
              {opt.tooltip}
            </span>
          )}
        </div>
      ))}

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
