import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessages } from '../api';
import { money } from '../utils';

export default function SavingsGoals() {
  const [goals, setGoals] = useState(null);
  const [amounts, setAmounts] = useState({});
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => api('/savings-goals/').then(setGoals), []);
  useEffect(() => { load(); }, [load]);

  const contribute = async (goal) => {
    try {
      const res = await api(`/savings-goals/${goal.id}/contribute/`, {
        method: 'POST',
        body: { amount: amounts[goal.id] },
      });
      setMsg({ type: 'info', text: res.detail });
      setAmounts({ ...amounts, [goal.id]: '' });
      load();
    } catch (e) {
      setMsg({ type: 'error', text: errorMessages(e).join(' ') });
    }
  };

  if (!goals) return <p>Loading…</p>;
  const active = goals.filter((g) => g.status === 'active');
  const completed = goals.filter((g) => g.status === 'completed');

  return (
    <>
      <header className="page-header">
        <h1>Savings goals</h1>
        <Link className="btn" to="/add-record?record_type=goal">＋ Create a goal</Link>
      </header>

      {msg && <p className={`alert ${msg.type}`}>{msg.text}</p>}

      <h2>Active goals</h2>
      {active.length === 0 && <p>You don't have any active goals yet.</p>}
      {active.map((g) => (
        <article key={g.id} className="card" style={{ marginBottom: 12 }}>
          <strong>{g.name}</strong>
          <div className="progress"><span style={{ width: `${g.percent}%` }} /></div>
          <small>
            {money(g.current_amount)} / {money(g.target_amount)} · {money(g.remaining_amount)} remaining
            {g.target_date && ` · Target ${g.target_date}`}
          </small>
          <div className="filters" style={{ marginTop: 12 }}>
            <input
              type="number" min="0.01" step="0.01" placeholder="₹ 0.00"
              value={amounts[g.id] || ''}
              onChange={(e) => setAmounts({ ...amounts, [g.id]: e.target.value })}
            />
            <button onClick={() => contribute(g)}>Add savings</button>
          </div>
        </article>
      ))}

      {completed.length > 0 && (
        <>
          <h2>Completed goals</h2>
          {completed.map((g) => (
            <article key={g.id} className="card" style={{ marginBottom: 12 }}>
              <strong>✓ {g.name}</strong>
              <small>{money(g.current_amount)} / {money(g.target_amount)}</small>
            </article>
          ))}
        </>
      )}
    </>
  );
}