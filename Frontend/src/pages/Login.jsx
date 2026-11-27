import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { errorMessages } from '../api';
import Errors from '../components/Errors';

export default function Login() {
  const { login } = useAuth();
  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const onChange = (e) => setForm((current) => ({ ...current, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors([]);
    try {
      await login(form.email.trim(), form.password);
    } catch (err) {
      setErrors(errorMessages(err));
      setBusy(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-showcase" aria-label="Budget Buddy introduction">
        <Link className="auth-brand" to="/"> <span className="auth-brand-mark">B</span> budgetbuddy</Link>
        <div className="auth-showcase-copy">
          <span className="auth-kicker">YOUR MONEY, IN FOCUS</span>
          <h1>Make every<br />rupee <em>count.</em></h1>
          <p>A clearer picture of your money starts with one simple habit: keeping track.</p>
          <div className="auth-preview" aria-hidden="true">
            <div className="auth-preview-top"><span>Monthly overview</span><span className="auth-preview-dot">●</span></div>
            <div className="auth-preview-amount">₹24,850 <small>available balance</small></div>
            <div className="auth-preview-bars"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
            <div className="auth-preview-legend"><span><b /> Income</span><span><b /> Expenses</span></div>
          </div>
        </div>
        <p className="auth-showcase-foot">Spend with intention. Save with confidence.</p>
      </section>

      <section className="auth-form-side">
        <div className="auth-mobile-brand"><span className="auth-brand-mark">B</span> budgetbuddy</div>
        <form className="auth-form" onSubmit={onSubmit}>
          <span className="auth-kicker">WELCOME BACK</span>
          <h2>Sign in to your account</h2>
          <p className="auth-subtitle">Pick up where you left off. Your finances are waiting.</p>
          <Errors messages={errors} />
          <label className="auth-field">Email address
            <input type="email" name="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={onChange} required />
          </label>
          <label className="auth-field">Password
            <span className="auth-password-wrap">
              <input type={showPassword ? 'text' : 'password'} name="password" autoComplete="current-password" placeholder="Enter your password" value={form.password} onChange={onChange} required />
              <button className="auth-toggle" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button>
            </span>
          </label>
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'} <span aria-hidden="true">→</span></button>
          <p className="auth-switch">Don't have an account? <Link to="/signup">Create one</Link></p>
        </form>
        <p className="auth-legal">By continuing, you agree to use Budget Buddy responsibly.</p>
      </section>
    </main>
  );
}
