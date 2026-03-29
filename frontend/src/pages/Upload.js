import { useState, useEffect, useCallback, useRef } from "react";
import API from "../api";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const BRANCH_LABELS = { engineering: "Engineering", commerce: "Commerce", architecture: "Architecture" };

const IMAGE_EXTS = new Set([".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"]);
const DOC_EXTS   = new Set([".pdf", ".docx", ".pptx", ".txt", ".xlsx", ".xls"]);
const ALL_TYPES  = [...IMAGE_EXTS, ...DOC_EXTS];

function getExt(filename = "") {
  return ("." + filename.split(".").pop()).toLowerCase();
}
function isImage(filename) { return IMAGE_EXTS.has(getExt(filename)); }

function fileIcon(filename) {
  const ext = getExt(filename);
  if (IMAGE_EXTS.has(ext)) return "🖼️";
  if (ext === ".pdf")  return "📕";
  if (ext === ".docx") return "📝";
  if (ext === ".pptx") return "📊";
  if ([".xlsx", ".xls"].includes(ext)) return "📗";
  return "📄";
}

export default function Upload() {
  const [file, setFile]               = useState(null);
  const [preview, setPreview]         = useState(null);
  const [uploading, setUploading]     = useState(false);
  const [dragOver, setDragOver]       = useState(false);
  const [status, setStatus]           = useState(null);
  const [myDocs, setMyDocs]           = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [deleting, setDeleting]       = useState(null);
  const inputRef                      = useRef();

  const branch   = localStorage.getItem("branch");
  const username = localStorage.getItem("username");
  const navigate = useNavigate();

  const fetchMyDocs = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const res = await API.get("my-documents/");
      setMyDocs(res.data);
    } catch { /* ignore */ }
    finally { setLoadingDocs(false); }
  }, []);

  useEffect(() => { fetchMyDocs(); }, [fetchMyDocs]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const pickFile = (f) => {
    const ext = getExt(f.name);
    if (!ALL_TYPES.includes(ext)) {
      setStatus({ type: "error", msg: `Unsupported format. Allowed: ${ALL_TYPES.join(", ")}` });
      return;
    }
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setStatus(null);
    setPreview(isImage(f.name) ? URL.createObjectURL(f) : null);
  };

  const clearFile = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null); setPreview(null); setStatus(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    if (e.dataTransfer.files[0]) pickFile(e.dataTransfer.files[0]);
  };

  const handleUpload = async () => {
    if (!file) { setStatus({ type: "error", msg: "Please select a file first." }); return; }
    setUploading(true); setStatus(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      await API.post("upload/", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setStatus({ type: "success", msg: `"${file.name}" uploaded to ${BRANCH_LABELS[branch] || branch}.` });
      clearFile();
      fetchMyDocs();
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.error || "Upload failed." });
    } finally { setUploading(false); }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    setDeleting(docId);
    try {
      await API.delete(`documents/${docId}/delete/`);
      setMyDocs(prev => prev.filter(d => d.doc_id !== docId));
    } catch (err) {
      alert(err.response?.data?.error || "Delete failed.");
    } finally { setDeleting(null); }
  };

  const logout = () => { localStorage.clear(); navigate("/"); };

  return (
    <div className="dash-page">
      <header className="dash-header">
        <span className="dash-logo">DocVault</span>
        <div className="dash-nav">
          <button className="nav-link" onClick={() => navigate("/search")}>Search</button>
          <button className="nav-link active" onClick={() => navigate("/upload")}>Upload</button>
          <span className="nav-user">
            <span className="branch-chip">{BRANCH_LABELS[branch] || branch}</span>
            {username}
          </span>
          <button className="nav-logout" onClick={logout}>Logout</button>
        </div>
      </header>

      <main className="dash-main">
        <div className="upload-card">
          <h2 className="card-title">Upload Document</h2>
          <p className="card-sub">
            Images (JPG, PNG, BMP, TIFF, WEBP) are OCR'd automatically so their text is searchable.
            Stored under <strong>{BRANCH_LABELS[branch] || branch}</strong>.
          </p>

          {/* ── Drop zone ── */}
          <div
            className={`drop-zone ${dragOver ? "active" : ""} ${file ? "has-file" : ""}`}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => !file && inputRef.current.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept={ALL_TYPES.join(",")}
              style={{ display: "none" }}
              onChange={e => e.target.files[0] && pickFile(e.target.files[0])}
            />

            {file ? (
              <div style={{ width: "100%", textAlign: "left" }}>

                {/* Image preview thumbnail */}
                {preview && (
                  <div style={{
                    width: "100%", maxHeight: 240, borderRadius: 10, overflow: "hidden",
                    marginBottom: 16, display: "flex", justifyContent: "center",
                    background: "rgba(0,0,0,0.25)",
                  }}>
                    <img
                      src={preview}
                      alt="preview"
                      style={{ maxWidth: "100%", maxHeight: 240, objectFit: "contain", display: "block" }}
                    />
                  </div>
                )}

                {/* File info row */}
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 26 }}>{fileIcon(file.name)}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p className="file-name" style={{ marginBottom: 2 }}>{file.name}</p>
                    <p className="file-size">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                  {isImage(file.name) && (
                    <span className="branch-chip" style={{ fontSize: 11 }}>🔍 OCR</span>
                  )}
                </div>

                <button
                  onClick={e => { e.stopPropagation(); clearFile(); }}
                  style={{
                    marginTop: 12, background: "none", border: "none",
                    color: "var(--text-muted)", fontSize: 12, cursor: "pointer",
                    textDecoration: "underline", padding: 0,
                  }}
                >
                  Remove file
                </button>
              </div>
            ) : (
              <>
                <div className="upload-icon">⬆</div>
                <p className="drop-label">Drag & drop or click to browse</p>
                <p className="drop-hint">Images · PDF · DOCX · PPTX · XLSX · TXT</p>
              </>
            )}
          </div>

          {status && (
            <div className={`status-msg ${status.type}`}>
              {status.type === "success" ? "✅ " : "❌ "}{status.msg}
            </div>
          )}

          <button className="upload-btn" onClick={handleUpload} disabled={uploading || !file}>
            {uploading
              ? <><span className="spinner" style={{ marginRight: 8 }} />Uploading…</>
              : `Upload to ${BRANCH_LABELS[branch] || branch}`}
          </button>
        </div>

        {/* ── My Documents ── */}
        <div className="my-docs-card">
          <div className="my-docs-header">
            <h3 className="my-docs-title">My Uploaded Documents</h3>
            <span className="my-docs-count">{myDocs.length} file{myDocs.length !== 1 ? "s" : ""}</span>
          </div>

          {loadingDocs ? (
            <div className="docs-loading"><span className="spinner dark" /></div>
          ) : myDocs.length === 0 ? (
            <div className="docs-empty">No documents uploaded yet.</div>
          ) : (
            <div className="my-doc-list">
              {myDocs.map(d => (
                <div key={d.doc_id} className="my-doc-row">
                  <div className="doc-icon">{fileIcon(d.filename)}</div>
                  <div className="doc-info">
                    <span className="doc-filename">{d.filename}</span>
                    <span className="doc-score">{d.uploaded_at}</span>
                  </div>
                  {(d.is_image || IMAGE_EXTS.has(getExt(d.filename))) && (
                    <span className="branch-chip" style={{ fontSize: 10, padding: "2px 8px" }}>OCR</span>
                  )}
                  <button
                    className="delete-btn"
                    onClick={() => handleDelete(d.doc_id, d.filename)}
                    disabled={deleting === d.doc_id}
                  >
                    {deleting === d.doc_id ? <span className="spinner" /> : "🗑 Delete"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}