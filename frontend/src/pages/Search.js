import { useState, useEffect, useRef } from "react";
import API from "../api";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const BRANCH_LABELS = { engineering: "Engineering", commerce: "Commerce", architecture: "Architecture" };
const IMAGE_EXTS    = new Set([".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"]);

function getExt(filename = "") { return ("." + filename.split(".").pop()).toLowerCase(); }
function isImageFile(filename) { return IMAGE_EXTS.has(getExt(filename)); }

function fileIcon(filename) {
  if (IMAGE_EXTS.has(getExt(filename))) return "🖼️";
  const ext = getExt(filename);
  if (ext === ".pdf")  return "📕";
  if (ext === ".docx") return "📝";
  if (ext === ".pptx") return "📊";
  if ([".xlsx", ".xls"].includes(ext)) return "📗";
  return "📄";
}

function AuthImage({ docId }) {
  const [src, setSrc]         = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(false);
  const urlRef                = useRef(null);

  useEffect(() => {
    let cancelled = false;
    API.get(`documents/${docId}/preview/`, { responseType: "blob" })
      .then(res => {
        if (cancelled) return;
        const url = URL.createObjectURL(res.data);
        urlRef.current = url;
        setSrc(url);
      })
      .catch(() => !cancelled && setError(true))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, [docId]);

  if (loading) return (
    <div style={imgBox}><span className="spinner dark" /></div>
  );
  if (error) return (
    <div style={{ ...imgBox, color: "var(--text-muted)", fontSize: 12 }}>Preview unavailable</div>
  );
  return (
    <div style={imgBox}>
      <img src={src} alt="" style={{ maxWidth: "100%", maxHeight: 180, objectFit: "contain", borderRadius: 6 }} />
    </div>
  );
}

const imgBox = {
  background: "rgba(0,0,0,0.25)", borderRadius: "10px 10px 0 0",
  minHeight: 160, display: "flex", alignItems: "center", justifyContent: "center",
};

function ResultRow({ result, userBranch, onRequestSent }) {
  const [requesting, setRequesting] = useState(false);
  const [requested, setRequested]   = useState(result.access_requested || false);
  const [approved, setApproved]     = useState(result.access_approved || false);

  const handleDownload = async () => {
    try {
      const res = await API.get(`documents/${result.doc_id}/download/`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url; a.download = result.filename; a.click();
      window.URL.revokeObjectURL(url);
    } catch { alert("Download failed."); }
  };

  const handleRequestAccess = async () => {
    setRequesting(true);
    try {
      await API.post(`documents/${result.doc_id}/request-access/`);
      setRequested(true);
      if (onRequestSent) onRequestSent();
    } catch (err) {
      const msg = err.response?.data?.error || "Request failed.";
      alert(msg);
      // If already approved based on server response, update state
      if (msg.includes("already have access")) setApproved(true);
    } finally {
      setRequesting(false);
    }
  };

  const imgResult = result.is_image || isImageFile(result.filename);

  if (imgResult && result.can_open) {
    return (
      <div className="doc-row can-open" style={{ flexDirection: "column", padding: 0, overflow: "hidden", alignItems: "stretch" }}>
        <AuthImage docId={result.doc_id} />
        <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="doc-icon">🖼️</span>
            <div className="doc-info">
              <span className="doc-filename">{result.filename}</span>
              <span className="doc-score">Branch: {result.branch} · Score: {result.score?.toFixed(2)}</span>
            </div>
          </div>
          <button className="open-btn" style={{ alignSelf: "flex-start" }} onClick={handleDownload}>
            ⬇ Download
          </button>
        </div>
      </div>
    );
  }

  // Locked document — show request access button
  const renderLockActions = () => {
    if (approved) {
      return <button className="open-btn" onClick={handleDownload}>⬇ Download</button>;
    }
    if (requested) {
      return <span className="request-pending-label">⏳ Request sent</span>;
    }
    return (
      <button
        className="request-access-btn"
        onClick={handleRequestAccess}
        disabled={requesting}
      >
        {requesting ? <span className="spinner" style={{ width: 14, height: 14 }} /> : "🔓 Request Access"}
      </button>
    );
  };

  return (
    <div className={`doc-row ${result.can_open ? "can-open" : "locked"}`}>
      <span className="doc-icon">{fileIcon(result.filename)}</span>
      <div className="doc-info">
        <span className="doc-filename">{result.filename}</span>
        <span className="doc-score">
          Branch: {result.branch} · Score: {result.score?.toFixed(2)}
          {approved && <span style={{ color: "var(--success)", marginLeft: 6 }}>· Access granted</span>}
        </span>
      </div>
      {result.can_open ? (
        <button className="open-btn" onClick={handleDownload}>⬇ Download</button>
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <span className="locked-label">🔒</span>
          {renderLockActions()}
        </div>
      )}
    </div>
  );
}

function groupByBranch(results, userBranch) {
  const groups = {};
  for (const r of results) {
    if (!groups[r.branch]) groups[r.branch] = [];
    groups[r.branch].push(r);
  }
  return Object.entries(groups).sort(([a], [b]) => {
    if (a === userBranch) return -1;
    if (b === userBranch) return 1;
    return a.localeCompare(b);
  });
}

const BRANCH_COLORS = {
  engineering:  { color: "#7c6af7", dot: "#7c6af7" },
  commerce:     { color: "#22c55e", dot: "#22c55e" },
  architecture: { color: "#f59e0b", dot: "#f59e0b" },
};

export default function Search() {
  const [query, setQuery]       = useState("");
  const [results, setResults]   = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const navigate                = useNavigate();

  const branch   = localStorage.getItem("branch");
  const username = localStorage.getItem("username");

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true); setError("");
    try {
      const res = await API.get(`search/?q=${encodeURIComponent(query.trim())}`);
      const enriched = res.data.map(r => ({
        ...r,
        is_image: r.is_image ?? isImageFile(r.filename),
      }));
      setResults(enriched);
      setSearched(true);
    } catch (err) {
      setError(err.response?.data?.error || "Search failed.");
    } finally { setLoading(false); }
  };

  const logout = () => { localStorage.clear(); navigate("/"); };
  const groups  = groupByBranch(results, branch);

  return (
    <div className="dash-page">
      <header className="dash-header">
        <span className="dash-logo">DocVault</span>
        <div className="dash-nav">
          <button className="nav-link active">Search</button>
          <button className="nav-link" onClick={() => navigate("/upload")}>Upload</button>
          <button className="nav-link" onClick={() => navigate("/requests")}>
            Requests
          </button>
          <span className="nav-user">
            <span className="branch-chip">{BRANCH_LABELS[branch] || branch}</span>
            {username}
          </span>
          <button className="nav-logout" onClick={logout}>Logout</button>
        </div>
      </header>

      <main className="dash-main">
        <div className="search-hero">
          <h1 className="search-title">Search Documents</h1>
          <p className="search-sub">
            Search across all branches — including text extracted from images via OCR.
            Request access to documents from other branches.
          </p>

          <form className="search-bar" onSubmit={handleSearch}>
            <input
              className="search-input"
              type="text"
              placeholder="Type a word or phrase…"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            <button className="search-btn" type="submit" disabled={loading}>
              {loading ? <span className="spinner" /> : "Search"}
            </button>
          </form>
        </div>

        {error && <div className="error-banner" style={{ marginBottom: 20 }}>{error}</div>}

        {!searched && !loading && (
          <div className="empty-state">
            <div className="empty-icon">🔍</div>
            <p>Enter a search term to find documents across all branches.</p>
          </div>
        )}

        {searched && !loading && results.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <p>No results found for "{query}".</p>
          </div>
        )}

        {searched && results.length > 0 && (
          <>
            <p className="results-count">
              {results.length} result{results.length !== 1 ? "s" : ""} across {groups.length} branch{groups.length !== 1 ? "es" : ""}
            </p>

            {groups.map(([branchKey, docs]) => {
              const color = BRANCH_COLORS[branchKey] || { color: "#8888a0", dot: "#8888a0" };
              const isYours = branchKey === branch;

              const imgDocs   = docs.filter(d => (d.is_image || isImageFile(d.filename)) && d.can_open);
              const otherDocs = docs.filter(d => !(d.is_image || isImageFile(d.filename)) || !d.can_open);

              return (
                <div key={branchKey} className="branch-section">
                  <div className="branch-header" style={{ borderColor: color.color }}>
                    <span className="branch-dot" style={{ background: color.dot }} />
                    <span className="branch-name" style={{ color: color.color }}>
                      {BRANCH_LABELS[branchKey] || branchKey}
                    </span>
                    <span className="branch-count">({docs.length})</span>
                    {isYours && <span className="your-branch-tag">Your branch</span>}
                  </div>

                  {imgDocs.length > 0 && (
                    <div style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                      gap: 12, marginBottom: otherDocs.length > 0 ? 12 : 0,
                    }}>
                      {imgDocs.map(r => (
                        <ResultRow key={r.doc_id} result={r} userBranch={branch} />
                      ))}
                    </div>
                  )}

                  {otherDocs.length > 0 && (
                    <div className="doc-list">
                      {otherDocs.map(r => (
                        <ResultRow key={r.doc_id} result={r} userBranch={branch} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </main>
    </div>
  );
}