import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "MoveScore — Dance first. Music second.",
  description:
    "Upload your choreography and get original AI-composed music built around your movement. Powered by Gemini and Lyria 3.5.",
};

const STEPS = [
  { num: "1", label: "Upload your dance video" },
  { num: "2", label: "Choose style, mood & energy" },
  { num: "3", label: "Generate and download" },
];

export default function LandingPage() {
  return (
    <main className="landing-hero">
      {/* Wordmark */}
      <div className="landing-wordmark">MoveScore</div>

      {/* Headline */}
      <h1 className="landing-headline">
        Dance first.
        <br />
        Music second.
      </h1>

      {/* Subhead */}
      <p className="landing-sub">
        Upload your choreography and get original music composed
        around your movement — hits, freezes, spins and all.
      </p>

      {/* CTA */}
      <Link href="/create" className="landing-cta" id="start-creating-btn">
        Start Creating
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </Link>

      {/* 3-step flow */}
      <div className="landing-steps">
        {STEPS.map((s) => (
          <div key={s.num} className="landing-step">
            <div className="landing-step-num">{s.num}</div>
            <div className="landing-step-text">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Comparison */}
      <div className="landing-compare">
        <div>
          <div className="landing-compare-label">Normal workflow</div>
          <div className="landing-compare-value">Music → Choreography</div>
        </div>
        <div>
          <div className="landing-compare-label">MoveScore</div>
          <div className="landing-compare-value ours">Choreography → Music</div>
        </div>
      </div>

      {/* Footer */}
      <div className="landing-footer">
        Powered by Gemini · Lyria 3.5 · Google ADK
      </div>
    </main>
  );
}
