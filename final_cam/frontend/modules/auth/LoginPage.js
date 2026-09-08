"use client";
import { useState } from "react";
import { BOBMark, Icon } from "../../shared/ui";
const API = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

function LoginPage({ onLogin }) {
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!employeeId.trim() || !password) return setError("Enter your Employee ID and password.");
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: employeeId.trim(), password })
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || "Login failed");
      if (remember) localStorage.setItem("bob_cam_user", JSON.stringify(data.user));
      else sessionStorage.setItem("bob_cam_user", JSON.stringify(data.user));
      onLogin(data.user);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <div className="auth-page">
    <div className="auth-brand-panel">
      <div className="auth-brand">
        <BOBMark />
        <div><strong>बैंक ऑफ बड़ौदा</strong><b>Bank of Baroda</b><span>India's International Bank</span></div>
      </div>
      <div className="auth-copy">
        <div className="auth-eyebrow">CREDIT APPRAISAL</div>
        <h1>CAM <em>AI</em> Platform</h1>
        <p>Credit Appraisal Management</p>
        <div className="auth-line" />
        <div className="auth-security"><div className="security-icon"><Icon name="shield" /></div><strong>Secure. Trusted. Reliable.</strong><span>Your secure access to the CAM AI Platform</span></div>
      </div>
      <div className="bank-line-art"><span>BOB</span><i></i><i></i><i></i></div>
      <div className="auth-features"><span><Icon name="shield" /><b>Bank-grade<br/>Security</b></span><span><Icon name="file" /><b>Encrypted<br/>Connection</b></span><span><Icon name="users" /><b>Authorized<br/>Access Only</b></span></div>
    </div>
    <div className="auth-form-panel">
      <form className="login-card" onSubmit={submit}>
        <div className="mobile-logo"><BOBMark small /><strong>Bank of Baroda</strong></div>
        <div className="login-heading"><h2>Welcome Back!</h2><p>Please sign in to continue</p></div>
        <label>Employee ID</label>
        <div className="login-input"><Icon name="users" /><input value={employeeId} onChange={e=>setEmployeeId(e.target.value)} placeholder="Enter Employee ID" autoComplete="username" /></div>
        <label>Password</label>
        <div className="login-input"><Icon name="shield" /><input type={showPassword ? "text" : "password"} value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter Password" autoComplete="current-password" /><button type="button" onClick={()=>setShowPassword(!showPassword)}>{showPassword ? "Hide" : "Show"}</button></div>
        <div className="login-options"><label className="remember"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)} /><span>Remember me</span></label><button type="button" className="link-btn" onClick={()=>setError("Please contact the bank support/helpdesk for password reset.")}>Forgot Password?</button></div>
        {error && <div className="login-error">{error}</div>}
        <button className="login-primary" disabled={busy}>{busy ? "Signing in…" : "LOGIN"}</button>
        <div className="or-line"><span>OR</span></div>
        <button type="button" className="login-sso" onClick={()=>setError("Bank SSO integration is ready to be connected here.")}><Icon name="shield" /> LOGIN WITH SSO</button>
        <div className="secure-box"><Icon name="shield" /><div><strong>Secure Access</strong><span>All activities are monitored and protected.<br/>For authorized users only.</span></div></div>
      </form>
      <div className="auth-footer">This is a secure system. Unauthorized access is prohibited.<span>© 2026 Bank of Baroda. All rights reserved.</span></div>
    </div>
  </div>;
}

const menuItems = [
  ["Dashboard", "home"], ["CAM Proposals", "file"], ["Borrowers", "users"], ["Documents", "file"],
  ["MCA & External Data", "building"], ["Policy & Compliance", "shield"], ["AI Assistant", "spark"],
  ["Reports & Analytics", "chart"], ["Notifications", "bell"], ["Audit Trail", "file"], ["User Management", "users"], ["Settings", "settings"]
];


export default LoginPage;