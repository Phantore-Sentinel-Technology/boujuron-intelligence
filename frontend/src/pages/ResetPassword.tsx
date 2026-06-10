import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import { resetPassword } from "../services/api";

export function ResetPassword() {
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token") || "", [params]);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    try {
      await resetPassword(token, password);
      setSuccess("Password reset successfully. Redirecting to login...");
      window.setTimeout(() => navigate("/login", { replace: true }), 1200);
    } catch {
      setError("Reset link is invalid or expired.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark"><ShieldCheck size={22} /></span>
          <div>
            <p className="eyebrow">Secure recovery</p>
            <h1>New Password</h1>
          </div>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          <h2>Reset Password</h2>
          {!token && <p className="form-error">Missing reset token. Generate a new reset link.</p>}
          <label>
            <span>New Password</span>
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" minLength={8} required />
          </label>
          <label>
            <span>Confirm Password</span>
            <input value={confirm} onChange={(event) => setConfirm(event.target.value)} type="password" minLength={8} required />
          </label>
          {error && <p className="form-error">{error}</p>}
          {success && <p className="form-success">{success}</p>}
          <button className="primary-button" disabled={submitting || !token}>
            <LockKeyhole size={18} />
            {submitting ? "Resetting..." : "Reset password"}
          </button>
          <p className="auth-switch"><Link to="/login">Back to login</Link></p>
        </form>
      </section>
    </main>
  );
}
