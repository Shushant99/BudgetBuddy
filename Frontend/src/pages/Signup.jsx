import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { errorMessages } from '../api';
import Errors from '../components/Errors';

export default function Signup() {
  const { signup } = useAuth();
  const [form, setForm] = useState({ full_name: '', email: '', password: '' });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const onChange = (e) => setForm((current) => ({ ...current, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setErrors([]);
    if (form.password !== confirmPassword) {
      setErrors(['Your passwords do not match.']);
      return;
    }
    setBusy(true);
    try {
      await signup({ ...form, full_name: form.full_name.trim(), email: form.email.trim() });
    } catch (err) {
      setErrors(errorMessages(err));
      setBusy(false);
    }
  };

  return (
    <main className="auth-page auth-page-signup">
      <section className="auth-showcase" aria-label="Budget Buddy introduction">
        <Link className="auth-brand" to="/"> <span className="auth-brand-mark">B</span> budgetbuddy</Link>
        <div className="auth-showcase-copy">
          <span className="auth-kicker">A FRESH START</span>
          <h1>Build better<br />money <em>habits.</em></h1>
          <p>Bring your income, spending and savings goals together in one calm, simple space.</p>
          <div className="auth-benefits">
            <div><span>↗</span><p><strong>Know where it goes</strong><small>See your spending clearly.</small></p></div>
            <div><span>◎</span><p><strong>Stay on track</strong><small>Set budgets that work for you.</small></p></div>
            <div><span>✳</span><p><strong>Save with purpose</strong><small>Turn goals into progress.</small></p></div>
          </div>
        </div>
        <p className="auth-showcase-foot">Small steps today. Stronger finances tomorrow.</p>
      </section>

      <section className="auth-form-side">
        <div className="auth-mobile-brand"><span className="auth-brand-mark">B</span> budgetbuddy</div>
        <form className="auth-form" onSubmit={onSubmit}>
          <span className="auth-kicker">GET STARTED — IT'S FREE</span>
          <h2>Create your account</h2>
          <p className="auth-subtitle">A few details and you're ready to take control.</p>
          <Errors messages={errors} />
          <label className="auth-field">Full name
            <input name="full_name" autoComplete="name" placeholder="Your name" value={form.full_name} onChange={onChange} required />
          </label>
          <label className="auth-field">Email address
            <input type="email" name="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={onChange} required />
          </label>
          <label className="auth-field">Password
            <span className="auth-password-wrap">
              <input type={showPassword ? 'text' : 'password'} name="password" autoComplete="new-password" placeholder="Create a password" value={form.password} onChange={onChange} required />
              <button className="auth-toggle" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button>
            </span>
          </label>
          <label className="auth-field">Confirm password
            <input type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="Enter your password again" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
          </label>
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? 'Creating account…' : 'Create account'} <span aria-hidden="true">→</span></button>
          <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
        </form>
        <p className="auth-legal">Your account details are used to keep your budget private.</p>
      </section>
    </main>
  );
}
