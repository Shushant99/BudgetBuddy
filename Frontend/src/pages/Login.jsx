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

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors([]);
    try {
      await login(form.email, form.password);
    } catch (err) {
      setErrors(errorMessages(err));
      setBusy(false);
    }
  };

  return (
    <div className="center">
      <form className="card" onSubmit={onSubmit}>
        <h1>Welcome back</h1>
        <Errors messages={errors} />
        <label>Email address
          <input type="email" name="email" value={form.email} onChange={onChange} required />
        </label>
        <label>Password
          <input type="password" name="password" value={form.password} onChange={onChange} required />
        </label>
        <button disabled={busy}>{busy ? 'Logging in…' : 'Log in'}</button>
        <p>New here? <Link to="/signup">Create an account</Link></p>
      </form>
    </div>
  );
}