import { useState } from "react";
import API from "../api";
import { useNavigate, Link, useLocation } from "react-router-dom";
import "./Auth.css";

export default function Login() {
  const [data, setData] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const justRegistered = location.state?.registered;

  const handleLogin = async () => {
    if (!data.username || !data.password) {
      setError("Both fields are required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("login/", data);
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("branch", res.data.branch);
      localStorage.setItem("username", res.data.username);
      navigate("/search");
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const set = (field) => (e) => {
    setData((d) => ({ ...d, [field]: e.target.value }));
    setError("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleLogin();
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-badge">DocVault</div>
        <h1 className="auth-title">Welcome Back</h1>
        <p className="auth-sub">Sign in to access your branch documents</p>

        {justRegistered && (
          <div className="success-banner">
            Account created successfully! Please sign in.
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}

        <div className="field">
          <label>Username</label>
          <input
            placeholder="Your username"
            value={data.username}
            onChange={set("username")}
            onKeyDown={handleKeyDown}
          />
        </div>

        <div className="field">
          <label>Password</label>
          <input
            type="password"
            placeholder="Your password"
            value={data.password}
            onChange={set("password")}
            onKeyDown={handleKeyDown}
          />
        </div>

        <button className="auth-btn" onClick={handleLogin} disabled={loading}>
          {loading ? <span className="spinner" /> : "Sign In"}
        </button>

        <p className="auth-footer">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  );
}