import { ArrowLeft, Check, Mic, Square, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { api } from "../services/api";

const formatDate = (value) =>
  new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));

function ProviderToggle({ provider, onChange }) {
  return (
    <div className="capture-privacy-toggle">
      <span className="capture-privacy-label">Processing:</span>
      <button
        type="button"
        className={`capture-privacy-btn${provider === "ollama" ? " active" : ""}`}
        onClick={() => onChange("ollama")}
        title="Stays on your machine — nothing sent to the cloud"
      >
        🔒 Local (Ollama)
      </button>
      <button
        type="button"
        className={`capture-privacy-btn${provider === "openai" ? " active" : ""}`}
        onClick={() => onChange("openai")}
        title="Sends text to OpenAI's cloud API"
      >
        ☁️ Cloud (OpenAI)
      </button>
    </div>
  );
}

export function QuickCapture({ standalone, onBack }) {
  const [provider, setProvider] = useState("ollama");
  const [phase, setPhase] = useState("idle"); // idle | transcribing | transcribed | polishing | polished | saving | saved
  const [rawText, setRawText] = useState("");
  const [cleanProse, setCleanProse] = useState("");
  const [structuredBreakdown, setStructuredBreakdown] = useState("");
  const [selectedOutput, setSelectedOutput] = useState("prose"); // "prose" | "structured"
  const [captureName, setCaptureName] = useState("");
  const [error, setError] = useState("");
  const [savedCaptures, setSavedCaptures] = useState([]);
  const [loadingCaptures, setLoadingCaptures] = useState(true);

  const recorder = useAudioRecorder(async (blob) => {
    setPhase("transcribing");
    setError("");
    try {
      const result = await api.transcribe(blob, null);
      setRawText(result.text || "");
      setPhase("transcribed");
    } catch {
      setError("Transcription failed. Please try again.");
      setPhase("idle");
    }
  });

  useEffect(() => {
    loadCaptures();
  }, []);

  const loadCaptures = async () => {
    setLoadingCaptures(true);
    try {
      const result = await api.listCaptures();
      setSavedCaptures(result.captures || []);
    } catch {
      // Non-fatal — list just won't show
    } finally {
      setLoadingCaptures(false);
    }
  };

  const handlePolish = async () => {
    if (!rawText.trim()) return;
    setPhase("polishing");
    setError("");
    try {
      const result = await api.polishCapture(rawText, provider);
      setCleanProse(result.clean_prose);
      setStructuredBreakdown(result.structured_breakdown);
      setPhase("polished");
    } catch (err) {
      setError(err.message || "Polishing is currently unavailable. You can still save the raw transcription.");
      setPhase("transcribed");
    }
  };

  const handleSave = async () => {
    if (!captureName.trim()) return;
    setPhase("saving");
    setError("");
    const textToSave =
      phase === "polished"
        ? selectedOutput === "prose"
          ? cleanProse
          : structuredBreakdown
        : rawText;

    try {
      await api.saveCapture({
        name: captureName.trim(),
        raw_transcription: rawText,
        clean_prose: cleanProse || null,
        structured_breakdown: structuredBreakdown || null,
        llm_provider: cleanProse ? provider : null,
      });
      setPhase("saved");
      await loadCaptures();
    } catch {
      setError("Save failed. Please try again.");
      setPhase(cleanProse ? "polished" : "transcribed");
    }
  };

  const handleCaptureAnother = () => {
    setPhase("idle");
    setRawText("");
    setCleanProse("");
    setStructuredBreakdown("");
    setCaptureName("");
    setSelectedOutput("prose");
    setError("");
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteCapture(id);
      setSavedCaptures((prev) => prev.filter((c) => c.id !== id));
    } catch {
      setError("Could not delete capture. Please try again.");
    }
  };

  const canSave =
    captureName.trim().length > 0 &&
    (rawText.trim().length > 0) &&
    phase !== "saving";

  const isWorking = ["transcribing", "polishing", "saving"].includes(phase);

  return (
    <div className={`capture-shell${standalone ? " capture-standalone" : ""}`}>
      <div className="capture-page page-shell">

        {/* Header */}
        <div className="capture-header">
          {standalone ? (
            <a className="capture-back-link" href="/">
              <ArrowLeft size={15} /> Dashboard
            </a>
          ) : (
            <button className="text-button" onClick={onBack}>
              <ArrowLeft size={15} /> Back to Dashboard
            </button>
          )}
          <div className="capture-title-block">
            <span className="eyebrow">Quick Capture</span>
            <h1>Capture an idea</h1>
            <p className="capture-subtitle">
              Record your thoughts, transcribe them locally, then polish with AI.
            </p>
          </div>
          <ProviderToggle provider={provider} onChange={setProvider} />
        </div>

        {/* Error banner */}
        {error && (
          <div className="error-banner capture-error">
            {error}
            <button className="ghost-icon-button" onClick={() => setError("")} style={{ marginLeft: "auto" }}>
              <X size={14} />
            </button>
          </div>
        )}

        {/* Main capture card */}
        <div className="capture-card">

          {/* Step 1 — Record */}
          <div className="capture-step">
            <span className="capture-step-label">1 — Record</span>
            <div className={`answer-box${recorder.recording ? " recording" : ""}`}>
              <textarea
                className="capture-textarea"
                placeholder={
                  phase === "idle"
                    ? "Record your idea using the button below, or type directly here…"
                    : phase === "transcribing"
                    ? "Transcribing…"
                    : ""
                }
                value={rawText}
                onChange={(e) => { setRawText(e.target.value); if (phase === "idle") setPhase("transcribed"); }}
                disabled={isWorking || recorder.recording}
                style={{ minHeight: 160 }}
              />
              <div className="answer-tools">
                <span>
                  {phase === "transcribing" && <span className="spinner-label">⏳ Transcribing…</span>}
                  {recorder.recording && <span style={{ color: "var(--coral)", fontWeight: 600 }}>● {recorder.seconds}s</span>}
                  {phase === "transcribed" && rawText && <span style={{ color: "var(--forest)" }}>✓ Ready to polish</span>}
                </span>
                <div style={{ display: "flex", gap: 8 }}>
                  {rawText && !recorder.recording && phase !== "transcribing" && (
                    <button
                      className="ghost-icon-button"
                      title="Clear"
                      onClick={() => { setRawText(""); setCleanProse(""); setStructuredBreakdown(""); setPhase("idle"); }}
                    >
                      <X size={15} />
                    </button>
                  )}
                  {recorder.recording ? (
                    <button className="record-button active" onClick={recorder.stop}>
                      <Square size={13} fill="currentColor" /> Stop &nbsp;{recorder.seconds}s
                    </button>
                  ) : (
                    <button
                      className="record-button"
                      onClick={recorder.start}
                      disabled={isWorking}
                    >
                      <Mic size={14} /> Record
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Step 2 — Polish */}
          {(phase === "transcribed" || phase === "polishing" || phase === "polished" || phase === "saving" || phase === "saved") && rawText && (
            <div className="capture-step">
              <span className="capture-step-label">2 — Polish</span>
              {phase === "polished" || phase === "saving" || phase === "saved" ? (
                <div className="capture-outputs">
                  <div className="capture-output-tabs">
                    <button
                      className={`capture-output-tab${selectedOutput === "prose" ? " active" : ""}`}
                      onClick={() => setSelectedOutput("prose")}
                    >
                      Clean Prose
                    </button>
                    <button
                      className={`capture-output-tab${selectedOutput === "structured" ? " active" : ""}`}
                      onClick={() => setSelectedOutput("structured")}
                    >
                      Structured Breakdown
                    </button>
                    <span className="capture-provider-badge">{provider === "ollama" ? "🔒 Local" : "☁️ OpenAI"}</span>
                  </div>
                  <textarea
                    className="capture-output-textarea"
                    value={selectedOutput === "prose" ? cleanProse : structuredBreakdown}
                    onChange={(e) => selectedOutput === "prose"
                      ? setCleanProse(e.target.value)
                      : setStructuredBreakdown(e.target.value)
                    }
                    disabled={phase === "saving" || phase === "saved"}
                  />
                </div>
              ) : (
                <button
                  className="primary-button"
                  onClick={handlePolish}
                  disabled={phase === "polishing" || !rawText.trim()}
                >
                  {phase === "polishing" ? <><span className="spinner-label">⏳ Polishing…</span></> : <><Mic size={15} /> Polish with AI</>}
                </button>
              )}
            </div>
          )}

          {/* Step 3 — Save */}
          {(phase === "transcribed" || phase === "polished" || phase === "saving") && (
            <div className="capture-step">
              <span className="capture-step-label">3 — Save</span>
              {phase === "saved" ? null : (
                <div className="capture-save-row">
                  <input
                    className="name-session-input capture-name-input"
                    type="text"
                    placeholder="Name this capture…"
                    maxLength={200}
                    value={captureName}
                    onChange={(e) => setCaptureName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && canSave) handleSave(); }}
                    disabled={phase === "saving"}
                  />
                  <button
                    className="primary-button"
                    onClick={handleSave}
                    disabled={!canSave}
                  >
                    {phase === "saving" ? "Saving…" : <><Check size={15} /> Save</>}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Saved confirmation */}
          {phase === "saved" && (
            <div className="capture-saved-confirm">
              <span style={{ color: "var(--forest)", fontWeight: 600 }}>✓ Saved: {captureName}</span>
              <button className="secondary-button" onClick={handleCaptureAnother} style={{ marginLeft: "auto" }}>
                <Mic size={14} /> Capture Another
              </button>
            </div>
          )}
        </div>

        {/* Saved captures list */}
        <div className="capture-history">
          <div className="section-heading" style={{ marginBottom: 16 }}>
            <div>
              <span className="kicker">Previously saved</span>
              <h2 style={{ fontSize: 26 }}>Your captures</h2>
            </div>
          </div>
          {loadingCaptures ? (
            <p className="quiet">Loading…</p>
          ) : savedCaptures.length === 0 ? (
            <p className="quiet">No captures yet. Record your first idea above.</p>
          ) : (
            <div className="session-list">
              {savedCaptures.map((capture) => (
                <div key={capture.id} className="session-row-wrap">
                  <div className="session-row" style={{ cursor: "default" }}>
                    <span className="status-dot completed" />
                    <span className="session-copy">
                      <strong>{capture.name}</strong>
                      <small>
                        {formatDate(capture.created_at)}
                        {capture.llm_provider && (
                          <span className="capture-history-badge">
                            &nbsp;·&nbsp;{capture.llm_provider === "ollama" ? "🔒 Local" : "☁️ OpenAI"}
                          </span>
                        )}
                      </small>
                    </span>
                  </div>
                  <button
                    className="ghost-icon-button"
                    style={{ marginRight: 10 }}
                    title="Delete capture"
                    onClick={() => handleDelete(capture.id)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

// Made with Bob
