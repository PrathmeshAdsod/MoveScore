/**
 * ChipSelector — Compact pill/chip multi-select with "+ More" expand.
 *
 * Matches the Hugging Face provider selector style from the reference image:
 * - Small rounded pills with subtle border
 * - Selected: dark filled background
 * - First N items visible, "+ More" expands inline
 * - No hover tooltips (intentionally removed per plan)
 */

"use client";

import { useState } from "react";

interface ChipSelectorProps {
  options: string[];
  selected: string | null;
  onSelect: (value: string | null) => void;
  initialVisibleCount?: number;
  multiSelect?: boolean;
}

export default function ChipSelector({
  options,
  selected,
  onSelect,
  initialVisibleCount = 6,
}: ChipSelectorProps) {
  const [expanded, setExpanded] = useState(false);

  const visibleOptions = expanded ? options : options.slice(0, initialVisibleCount);
  const hasMore = options.length > initialVisibleCount;

  const handleClick = (option: string) => {
    onSelect(selected === option ? null : option);
  };

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem", alignItems: "center" }}>
      {visibleOptions.map((option) => (
        <button
          key={option}
          type="button"
          className={`chip${selected === option ? " selected" : ""}`}
          onClick={() => handleClick(option)}
          aria-pressed={selected === option}
        >
          {option}
        </button>
      ))}

      {hasMore && (
        <button
          type="button"
          className="chip-more"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          {expanded ? "Show less" : `+${options.length - initialVisibleCount} more`}
        </button>
      )}
    </div>
  );
}
