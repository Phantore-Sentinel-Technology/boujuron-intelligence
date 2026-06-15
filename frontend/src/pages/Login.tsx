import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { LogIn, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("analyst@boujuron.ai");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const routeState = location.state as { from?: { pathname: string }; registeredEmail?: string } | null;
  const from = routeState?.from?.pathname || "/";
  const registeredEmail = routeState?.registeredEmail;

  if (user) return <Navigate to={from} replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch {
      setError("Invalid email or password.");
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
            <p className="eyebrow">Fraud intelligence platform</p>
            <h1>Boujuron Intelligence</h1>
          </div>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          <h2>Analyst Login</h2>
          {registeredEmail && <p className="form-success">Registered successfully. Sign in with {registeredEmail}.</p>}
          <label>
            <span>Email</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
          </label>
          <label>
            <span>Password</span>
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
          </label>
          <Link className="forgot-link" to="/forgot-password">Forgot password?</Link>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button" disabled={submitting}>
            <LogIn size={18} />
            {submitting ? "Signing in..." : "Sign in"}
          </button>
          <p className="auth-switch">Need access? Ask an administrator for an invite link.</p>
        </form>
      </section>
    </main>
  );
}
