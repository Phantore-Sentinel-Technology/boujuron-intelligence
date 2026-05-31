import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ShieldPlus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types";

const roles: UserRole[] = ["Admin", "Fraud Analyst", "Investigator", "Read-Only Auditor"];

export function Register() {
  const { user, register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("Fraud Analyst");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await register(name, email, password, role);
      navigate("/", { replace: true });
    } catch {
      setError("Could not create account. Check the details and try again.");
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
          <label>
            <span>Role</span>
            <select value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
              {roles.map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button" disabled={submitting}>
            <ShieldPlus size={18} />
            {submitting ? "Creating..." : "Create account"}
          </button>
          <p className="auth-switch">Already registered? <Link to="/login">Sign in</Link></p>
        </form>
      </section>
    </main>
  );
}
