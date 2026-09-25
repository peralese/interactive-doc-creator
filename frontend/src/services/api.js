const API_BASE = import.meta.env.VITE_API_URL || "";

// MediaRecorder's actual output container varies by browser — Safari (iOS/macOS)
// never produces WebM, it records MP4/AAC. Naming the upload from the blob's real
// mimeType (rather than hardcoding .webm) keeps the stored file's extension honest.
const EXTENSION_BY_MIME_SUBTYPE = {
  webm: "webm",
  mp4: "mp4",
  ogg: "ogg",
  wav: "wav",
  aac: "aac",
  "x-m4a": "m4a",
  mpeg: "mp3",
};

function audioFileExtension(mimeType) {
  const subtype = (mimeType || "").split(";")[0].split("/")[1];
  return EXTENSION_BY_MIME_SUBTYPE[subtype] || "webm";
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP fallback message.
    }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  templates: () => request("/api/templates/"),
  ingestRequirements: ({ text, file }) => {
    const form = new FormData();
    if (text?.trim()) form.append("source_text", text.trim());
    if (file) form.append("source_file", file);
    return request("/api/templates/ingest", { method: "POST", body: form });
  },
  createTemplate: (template) =>
    request("/api/templates/", {
      method: "POST",
      body: JSON.stringify(template),
    }),
  sessions: (limit = 20) => request(`/api/sessions/?limit=${limit}`),
  createSession: (templateId, name, outputType) =>
    request("/api/sessions/", {
      method: "POST",
      body: JSON.stringify({ template_id: templateId, name: name || null, output_type: outputType || "report", metadata: {} }),
    }),
  renameSession: (id, name) =>
    request(`/api/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  updateSession: (id, patch) =>
    request(`/api/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  resumeSession: (id) => request(`/api/sessions/${id}/resume`),
  autosave: (id, data) =>
    request(`/api/sessions/${id}/autosave`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  questions: (sessionId, templateId) =>
    request("/api/questions/generate", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, template_id: templateId }),
    }),
  reviewSection: (sessionId, sectionId) =>
    request("/api/questions/section-review", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, section_id: sectionId }),
    }),
  saveResponse: (data) =>
    request("/api/responses/", { method: "POST", body: JSON.stringify(data) }),
  updateResponse: (id, answer) =>
    request(`/api/responses/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ answer }),
    }),
  transcribe: (blob, sessionId) => {
    const form = new FormData();
    form.append("audio", blob, `answer-${Date.now()}.${audioFileExtension(blob.type)}`);
    if (sessionId) form.append("session_id", sessionId);
    return request("/api/transcriptions/", { method: "POST", body: form });
  },
  preview: (sessionId) => request(`/api/documents/preview/${sessionId}`),
  generate: (sessionId) =>
    request("/api/documents/generate", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, format: "markdown" }),
    }),
  downloadUrl: (sessionId, format) =>
    `${API_BASE}/api/documents/download/${sessionId}?format=${format}`,
  polishCapture: (rawText, provider = "ollama") =>
    request("/api/captures/polish", {
      method: "POST",
      body: JSON.stringify({ raw_text: rawText, provider }),
    }),
  saveCapture: (capture) =>
    request("/api/captures/", {
      method: "POST",
      body: JSON.stringify(capture),
    }),
  listCaptures: (limit = 100) => request(`/api/captures/?limit=${limit}`),
  getCapture: (id) => request(`/api/captures/${id}`),
  updateCapture: (id, patch) =>
    request(`/api/captures/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  deleteCapture: (id) =>
    request(`/api/captures/${id}`, { method: "DELETE" }),
};
