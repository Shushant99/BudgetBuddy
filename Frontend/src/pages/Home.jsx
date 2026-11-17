import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="center">
      <div className="card">
        <h1>Budget Buddy</h1>
        <p>Track income, expenses, budgets and savings goals in one place.</p>
        <Link className="btn" to="/login">Log in</Link>
        <Link className="btn ghost" to="/signup">Sign up</Link>
      </div>
    </div>
  );
}