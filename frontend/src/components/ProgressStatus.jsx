import { Check, ExternalLink, X } from "lucide-react";
import { useState } from "react";
import { PROGRESS_STATUSES, progressStatusOf } from "../progressStatus";

export function PublishedLink({ url, size = 14, className = "ghost-icon-button" }) {
  if (!url) return null;
  return (
    <a
      className={className}
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      title={`Open published post: ${url}`}
      onClick={(event) => event.stopPropagation()}
    >
      <ExternalLink size={size} />
    </a>
  );
}

// Segmented In progress / Done / Published control. Choosing "Published" asks
// for an optional link before saving; the other two save immediately.
// onChange receives a PATCH payload and should resolve to the updated record.
export function ProgressStatusControl({ status, publishedUrl, onChange }) {
  const [editingUrl, setEditingUrl] = useState(false);
  const [url, setUrl] = useState(publishedUrl || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const save = async (payload) => {
    setSaving(true);
    setError("");
    try {
      const updated = await onChange(payload);
      // An older backend ignores unknown fields and answers 200 with the record
      // unchanged; surface that instead of silently snapping back to the old status.
      if (updated?.progress_status !== payload.progress_status) {
        throw new Error("The server didn't save the status. Restart the backend so it picks up the latest code.");
      }
      setEditingUrl(false);
    } catch (err) {
      setError(err.message || "Could not update status.");
    } finally {
      setSaving(false);
    }
  };

  const choose = (value) => {
    if (value === "published") {
      setUrl(publishedUrl || "");
      setEditingUrl(true);
      return;
    }
    setEditingUrl(false);
    if (value !== status) save({ progress_status: value });
  };

  const submitPublished = () =>
    save({ progress_status: "published", published_url: url.trim() || null });

  return (
    <div className="progress-control">
      <div className="progress-segments" role="radiogroup" aria-label="Status">
        {PROGRESS_STATUSES.map((option) => {
          const active = editingUrl ? option.value === "published" : option.value === status;
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={active}
              className={`progress-segment ${option.value}${active ? " active" : ""}`}
              disabled={saving}
              onClick={() => choose(option.value)}
            >
              <span className={`status-dot ${option.value}`} />
              {option.label}
            </button>
          );
        })}
      </div>

      {editingUrl ? (
        <div className="progress-url-row">
          <input
            className="name-session-input"
            type="url"
            inputMode="url"
            placeholder="Link to where it was posted (optional)"
            maxLength={1000}
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") submitPublished(); }}
            disabled={saving}
            autoFocus
          />
          <button className="primary-button" onClick={submitPublished} disabled={saving}>
            <Check size={15} /> {saving ? "Saving…" : "Mark published"}
          </button>
          <button
            className="ghost-icon-button"
            title="Cancel"
            onClick={() => { setEditingUrl(false); setError(""); }}
            disabled={saving}
          >
            <X size={16} />
          </button>
        </div>
      ) : (
        status === "published" && (
          <div className="progress-published-note">
            {publishedUrl ? (
              <a href={publishedUrl} target="_blank" rel="noopener noreferrer">
                {publishedUrl} <ExternalLink size={12} />
              </a>
            ) : (
              <span>No link saved.</span>
            )}
            <button className="text-button" onClick={() => choose("published")}>
              {publishedUrl ? "Edit link" : "Add link"}
            </button>
          </div>
        )
      )}

      {error && <p className="progress-error">{error}</p>}
    </div>
  );
}

export function ProgressStatusModal({ title, item, onChange, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <button className="modal-close ghost-icon-button" onClick={onClose}><X size={18} /></button>
        <h2>Update status</h2>
        <p className="progress-modal-subtitle">{title}</p>
        <ProgressStatusControl
          status={progressStatusOf(item)}
          publishedUrl={item.published_url}
          onChange={async (payload) => {
            const updated = await onChange(payload);
            if (updated?.progress_status === payload.progress_status) onClose();
            return updated;
          }}
        />
      </div>
    </div>
  );
}
