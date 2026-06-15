import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ShieldPlus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
export function Register() {
  const { user, register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [searchParams] = useSearchParams();
  const [inviteToken, setInviteToken] = useState(searchParams.get("invite") || "");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await register(name, email, password, "Read-Only Auditor", inviteToken);
      setSuccess(true);
      window.setTimeout(() => {
        navigate("/login", { replace: true, state: { registeredEmail: email } });
      }, 1400);
    } catch {
      setError("Could not create account. Check your invite token, email, and password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark"><ShieldPlus size={22} /></span>
          <div>
            <p className="eyebrow">Secure operations access</p>
            <h1>Create Account</h1>
          </div>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          <label>
            <span>Invite Token</span>
            <input value={inviteToken} onChange={(event) => setInviteToken(event.target.value.toUpperCase())} placeholder="BJRN-XXXX-XXXX-XXXX" required />
          </label>
          <label>
            <span>Name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>
          <label>
            <span>Email</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
          </label>
          <label>
            <span>Password</span>
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" minLength={8} required />
          </label>
          {error && <p className="form-error">{error}</p>}
          <p className="auth-note">Registration is invite-only. Your role is assigned by the invite.</p>
          <button className="primary-button" disabled={submitting}>
            <ShieldPlus size={18} />
            {submitting ? "Creating..." : "Create account"}
          </button>
          <p className="auth-switch">Already registered? <Link to="/login">Sign in</Link></p>
        </form>
      </section>
      {success && (
        <div className="toast-success" role="status">
          Registered successfully. Redirecting to login...
        </div>
      )}
    </main>
  );
}
