import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { errorMessages } from '../api';
import Errors from '../components/Errors';

export default function Signup() {
  const { signup } = useAuth();
  const [form, setForm] = useState({ full_name: '', email: '', password: '' });
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors([]);
    try {
      await signup(form);
    } catch (err) {
      setErrors(errorMessages(err));
      setBusy(false);
    }
  };

  return (
    <div className="center">
      <form className="card" onSubmit={onSubmit}>
        <h1>Create your account</h1>
        <Errors messages={errors} />
        <label>Full name
          <input name="full_name" value={form.full_name} onChange={onChange} required />
        </label>
        <label>Email address
          <input type="email" name="email" value={form.email} onChange={onChange} required />
        </label>
        <label>Password
          <input type="password" name="password" value={form.password} onChange={onChange} required />
        </label>
        <button disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
        <p>Already registered? <Link to="/login">Log in</Link></p>
      </form>
    </div>
  );
}