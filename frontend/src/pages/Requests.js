import { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const BRANCH_LABELS = {
  engineering: "Engineering",
  commerce: "Commerce",
  architecture: "Architecture",
};

const STATUS_COLORS = {
  pending:  { bg: "rgba(124,106,247,0.12)", border: "rgba(124,106,247,0.3)", color: "#a78bfa" },
  approved: { bg: "rgba(34,197,94,0.1)",   border: "rgba(34,197,94,0.3)",   color: "#22c55e" },
  denied:   { bg: "rgba(239,68,68,0.1)",   border: "rgba(239,68,68,0.3)",   color: "#ef4444" },
};

const STATUS_ICONS = { pending: "⏳", approved: "✅", denied: "❌" };

export default function Requests() {
  const [tab, setTab]               = useState("incoming"); // "incoming" | "sent"
  const [incoming, setIncoming]     = useState([]);
  const [sent, setSent]             = useState([]);
  const [loadingIn, setLoadingIn]   = useState(true);
  const [loadingSent, setLoadingSent] = useState(true);
  const [acting, setActing]         = useState(null); // request_id being approved/denied

  const navigate  = useNavigate();
  const branch    = localStorage.getItem("branch");
  const username  = localStorage.getItem("username");
  const logout    = () => { localStorage.clear(); navigate("/"); };

  const fetchIncoming = useCallback(async () => {
    setLoadingIn(true);
    try {
      const res = await API.get("access-requests/incoming/");
      setIncoming(res.data);
    } catch { /* ignore */ }
    finally { setLoadingIn(false); }
  }, []);

  const fetchSent = useCallback(async () => {
    setLoadingSent(true);
    try {
      const res = await API.get("access-requests/my/");
      setSent(res.data);
    } catch { /* ignore */ }
    finally { setLoadingSent(false); }
  }, []);

  useEffect(() => { fetchIncoming(); fetchSent(); }, [fetchIncoming, fetchSent]);

  const handleApprove = async (requestId) => {
    setActing(requestId);
    try {
      await API.post(`access-requests/${requestId}/approve/`);
      setIncoming(prev => prev.filter(r => r.request_id !== requestId));
    } catch (err) {
      alert(err.response?.data?.error || "Failed to approve.");
    } finally { setActing(null); }
  };

  const handleDeny = async (requestId) => {
    setActing(requestId);
    try {
      await API.post(`access-requests/${requestId}/deny/`);
      setIncoming(prev => prev.filter(r => r.request_id !== requestId));
    } catch (err) {
      alert(err.response?.data?.error || "Failed to deny.");
    } finally { setActing(null); }
  };

  const pendingCount = incoming.length;

  return (
    <div className="dash-page">
      <header className="dash-header">
        <span className="dash-logo">DocVault</span>
        <div className="dash-nav">
          <button className="nav-link" onClick={() => navigate("/search")}>Search</button>
          <button className="nav-link" onClick={() => navigate("/upload")}>Upload</button>
          <button className="nav-link active">Requests</button>
          <span className="nav-user">
            <span className="branch-chip">{BRANCH_LABELS[branch] || branch}</span>
            {username}
          </span>
          <button className="nav-logout" onClick={logout}>Logout</button>
        </div>
      </header>

      <main className="dash-main">
        {/* Page header */}
        <div style={{ marginBottom: 28 }}>
          <h1 className="search-title">Access Requests</h1>
          <p className="search-sub">
            Manage cross-branch document access — approve incoming requests or track your own.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="req-tabs">
          <button
            className={`req-tab ${tab === "incoming" ? "active" : ""}`}
            onClick={() => setTab("incoming")}
          >
            Incoming
            {pendingCount > 0 && (
              <span className="req-badge">{pendingCount}</span>
            )}
          </button>
          <button
            className={`req-tab ${tab === "sent" ? "active" : ""}`}
            onClick={() => setTab("sent")}
          >
            Sent
            {sent.length > 0 && (
              <span className="req-badge req-badge-muted">{sent.length}</span>
            )}
          </button>
        </div>

        {/* ── INCOMING ── */}
        {tab === "incoming" && (
          <div className="req-panel">
            {loadingIn ? (
              <div className="docs-loading"><span className="spinner dark" /></div>
            ) : incoming.length === 0 ? (
              <div className="empty-state" style={{ paddingTop: 48 }}>
                <div className="empty-icon">📬</div>
                <p>No pending access requests for your documents.</p>
              </div>
            ) : (
              <div className="req-list">
                {incoming.map(r => (
                  <div key={r.request_id} className="req-card">
                    <div className="req-card-left">
                      <span className="req-file-icon">📄</span>
                      <div className="req-info">
                        <span className="req-filename">{r.filename}</span>
                        <span className="req-meta">
                          Requested by <strong>{r.requester_username}</strong>
                          {" · "}
                          <span className="req-branch-chip">{BRANCH_LABELS[r.requester_branch] || r.requester_branch}</span>
                          {" · "}{r.created_at}
                        </span>
                      </div>
                    </div>
                    <div className="req-actions">
                      <button
                        className="req-approve-btn"
                        onClick={() => handleApprove(r.request_id)}
                        disabled={acting === r.request_id}
                      >
                        {acting === r.request_id
                          ? <span className="spinner" style={{ width: 14, height: 14 }} />
                          : "✓ Approve"}
                      </button>
                      <button
                        className="req-deny-btn"
                        onClick={() => handleDeny(r.request_id)}
                        disabled={acting === r.request_id}
                      >
                        {acting === r.request_id
                          ? <span className="spinner" style={{ width: 14, height: 14 }} />
                          : "✕ Deny"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── SENT ── */}
        {tab === "sent" && (
          <div className="req-panel">
            {loadingSent ? (
              <div className="docs-loading"><span className="spinner dark" /></div>
            ) : sent.length === 0 ? (
              <div className="empty-state" style={{ paddingTop: 48 }}>
                <div className="empty-icon">📤</div>
                <p>You haven't requested access to any documents yet.</p>
              </div>
            ) : (
              <div className="req-list">
                {sent.map(r => {
                  const st = STATUS_COLORS[r.status] || STATUS_COLORS.pending;
                  return (
                    <div key={r.request_id} className="req-card">
                      <div className="req-card-left">
                        <span className="req-file-icon">📄</span>
                        <div className="req-info">
                          <span className="req-filename">{r.filename}</span>
                          <span className="req-meta">
                            Owner: <strong>{r.owner_username}</strong>
                            {" · "}
                            <span className="req-branch-chip">{BRANCH_LABELS[r.doc_branch] || r.doc_branch}</span>
                            {" · Sent "}{r.created_at}
                          </span>
                          {r.status !== "pending" && (
                            <span className="req-meta" style={{ marginTop: 2 }}>
                              Updated: {r.updated_at}
                            </span>
                          )}
                        </div>
                      </div>
                      <span
                        className="req-status-pill"
                        style={{
                          background: st.bg,
                          border: `1px solid ${st.border}`,
                          color: st.color,
                        }}
                      >
                        {STATUS_ICONS[r.status]} {r.status.charAt(0).toUpperCase() + r.status.slice(1)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}