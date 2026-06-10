import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { KeyRound, ShieldCheck } from "lucide-react";
import { forgotPassword } from "../services/api";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    const response = await forgotPassword(email);
    setMessage(response.message);
    setResetUrl(response.reset_url || "");
    setSubmitting(false);
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark"><ShieldCheck size={22} /></span>
          <div>
            <p className="eyebrow">Account recovery</p>
            <h1>Reset Access</h1>
          </div>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          <h2>Forgot Password</h2>
          <label>
            <span>Email</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
          </label>
          {message && <p className="form-success">{message}</p>}
          {resetUrl && (
            <p className="reset-link-box">
              Dev reset link:
              <a href={resetUrl}>{resetUrl}</a>
            </p>
          )}
          <button className="primary-button" disabled={submitting}>
            <KeyRound size={18} />
            {submitting ? "Generating..." : "Generate reset link"}
          </button>
          <p className="auth-switch"><Link to="/login">Back to login</Link></p>
        </form>
      </section>
    </main>
  );
}
