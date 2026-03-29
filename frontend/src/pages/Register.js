import { useState } from "react";
import API from "../api";
import { useNavigate, Link } from "react-router-dom";
import "./Auth.css";

const BRANCHES = [
  { value: "engineering", label: "Engineering" },
  { value: "commerce", label: "Commerce" },
  { value: "architecture", label: "Architecture" },
];

export default function Register() {
  const [data, setData] = useState({ username: "", password: "", branch: "engineering" });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const validate = () => {
    const e = {};
    if (!data.username.trim()) e.username = "Username is required.";
    if (data.password.length < 6) e.password = "Password must be at least 6 characters.";
    if (!data.branch) e.branch = "Please select a branch.";
    return e;
  };

  const handleSubmit = async () => {
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    setLoading(true);
    try {
      await API.post("register/", data);
      navigate("/", { state: { registered: true } });
    } catch (err) {
      const serverErrors = err.response?.data?.errors || {};
      setErrors(serverErrors);
    } finally {
      setLoading(false);
    }
  };

  const set = (field) => (e) => {
    setData((d) => ({ ...d, [field]: e.target.value }));
    setErrors((er) => ({ ...er, [field]: undefined }));
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-badge">DocVault</div>
        <h1 className="auth-title">Create Account</h1>
        <p className="auth-sub">Join your branch knowledge base</p>

        <div className="field">
          <label>Username</label>
          <input
            placeholder="Choose a username"
            value={data.username}
            onChange={set("username")}
            className={errors.username ? "error" : ""}
          />
          {errors.username && <span className="err-msg">{errors.username}</span>}
        </div>

        <div className="field">
          <label>Password</label>
          <input
            type="password"
            placeholder="Min. 6 characters"
            value={data.password}
            onChange={set("password")}
            className={errors.password ? "error" : ""}
          />
          {errors.password && <span className="err-msg">{errors.password}</span>}
        </div>

        <div className="field">
          <label>Branch</label>
          <select
            value={data.branch}
            onChange={set("branch")}
            className={errors.branch ? "error" : ""}
          >
            {BRANCHES.map((b) => (
              <option key={b.value} value={b.value}>{b.label}</option>
            ))}
          </select>
          <span className="field-hint">
            All your uploads will be stored under this branch. This cannot be changed later.
          </span>
          {errors.branch && <span className="err-msg">{errors.branch}</span>}
        </div>

        <button className="auth-btn" onClick={handleSubmit} disabled={loading}>
          {loading ? <span className="spinner" /> : "Create Account"}
        </button>

        <p className="auth-footer">
          Already have an account? <Link to="/">Sign in</Link>
        </p>
      </div>
    </div>
  );
}