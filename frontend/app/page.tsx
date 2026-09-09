import Link from "next/link";

export default function LandingPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "4rem 1.5rem",
      }}
    >
      <div style={{ maxWidth: "520px", width: "100%", textAlign: "center" }}>
        {/* Logo / wordmark */}
        <div
          style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--text-light)",
            marginBottom: "2.5rem",
          }}
        >
          Agentic Cinema
        </div>

        {/* Hero headline */}
        <h1
          style={{
            fontSize: "clamp(2rem, 5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.04em",
            lineHeight: 1.1,
            marginBottom: "1.25rem",
          }}
        >
          Dance first.
          <br />
          Music second.
        </h1>

        {/* Subhead */}
        <p
          style={{
            color: "var(--text-muted)",
            fontSize: "1.0625rem",
            lineHeight: 1.65,
            marginBottom: "2rem",
          }}
        >
          Upload your choreography and get original music
          <br />
          composed around your movement.
        </p>

        {/* CTA */}
        <Link href="/create" className="btn btn-primary" style={{ fontSize: "1rem", padding: "0.625rem 1.75rem" }}>
          Start Creating →
        </Link>

        {/* Workflow comparison */}
        <div
          style={{
            marginTop: "3rem",
            padding: "1.25rem 1.5rem",
            borderRadius: "var(--radius)",
            border: "1px solid var(--border)",
            background: "var(--surface)",
            textAlign: "left",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
            }}
          >
            <div>
              <div className="text-small" style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
                Normal workflow
              </div>
              <div className="text-small text-muted">
                Music → Choreography
              </div>
            </div>
            <div>
              <div className="text-small" style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
                Our workflow
              </div>
              <div className="text-small" style={{ color: "var(--text)" }}>
                Choreography → Music
              </div>
            </div>
          </div>
        </div>

        {/* 3-step summary */}
        <div
          style={{
            marginTop: "2rem",
            display: "flex",
            gap: "0.5rem",
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          {[
            "1. Upload your choreography",
            "2. Choose your vibe",
            "3. Generate and download",
          ].map((step) => (
            <div
              key={step}
              className="text-small text-muted"
              style={{
                padding: "0.375rem 0.75rem",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-chip)",
              }}
            >
              {step}
            </div>
          ))}
        </div>

        {/* Footer note */}
        <div
          className="text-light text-small"
          style={{ marginTop: "3rem" }}
        >
          Powered by Gemini · Lyria · Google ADK
          <br />
          Built with IBM Bob
        </div>
      </div>
    </main>
  );
}
