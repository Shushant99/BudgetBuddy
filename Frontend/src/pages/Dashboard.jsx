import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessages } from '../api';
import { money } from '../utils';
import TransactionRow from '../components/TransactionRow';

function Stat({ label, value }) {
  return (
    <article className="card stat">
      <small>{label}</small>
      <strong>{money(value)}</strong>
    </article>
  );
}

function Bar({ percent }) {
  return <div className="progress"><span style={{ width: `${percent}%` }} /></div>;
}

export default function Dashboard() {
  const [d, setD] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    api('/dashboard/').then(setD).catch((e) => setError(errorMessages(e)[0]));
  }, []);

  const requestPremium = async () => {
    try {
      const res = await api('/premium-request/', { method: 'POST' });
      setNotice(res.detail);
      setD({ ...d, upgrade_status: 'pending' });
    } catch (e) {
      setNotice(errorMessages(e)[0]);
    }
  };

  if (error) return <p className="alert error">{error}</p>;
  if (!d) return <p>Loading…</p>;

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">{new Date().toLocaleDateString('en-IN', { dateStyle: 'full' })}</p>
          <h1>Welcome{d.first_name ? `, ${d.first_name}` : ''}</h1>
        </div>
        <Link className="btn" to="/add-record">＋ Add record</Link>
      </header>

      {notice && <p className="alert info">{notice}</p>}

      <section className="stats">
        <Stat label="Monthly balance" value={d.monthly_balance} />
        <Stat label="Money in" value={d.monthly_income} />
        <Stat label="Money out" value={d.monthly_expenses} />
        <Stat label="Saved this month" value={d.monthly_savings} />
        <Stat label="Budget set aside" value={d.budget_total} />
      </section>

      <div className="grid">
        <section className="panel">
          <h2>Recent transactions</h2>
          {d.transactions.length
            ? d.transactions.map((t) => <TransactionRow key={t.id} t={t} />)
            : <p>Add an income or expense to see your activity.</p>}
          <p><Link to="/transactions">View all</Link></p>
        </section>

        <section className="panel">
          <h2>Active budgets</h2>
          {d.budgets.length ? d.budgets.map((b) => (
            <div key={b.id}>
              <strong>{b.category}</strong> <small>{b.percent}% used</small>
              <Bar percent={b.percent} />
              <small>{money(b.spent)} of {money(b.amount)}</small>
            </div>
          )) : <p>No active budgets yet.</p>}
        </section>

        <section className="panel">
          <h2>Savings goals</h2>
          {d.goals.length ? d.goals.map((g) => (
            <div key={g.id}>
              <strong>{g.name}</strong>
              <Bar percent={g.percent} />
              <small>{money(g.current_amount)} / {money(g.target_amount)}</small>
            </div>
          )) : <p>Your active savings goals will appear here.</p>}
          <p><Link to="/savings-goals">Manage goals</Link></p>
        </section>

        <section className="panel">
          <h2>Money insights {d.is_premium && '✦'}</h2>
          {d.is_premium ? (
            d.category_spending.length ? d.category_spending.map((c) => (
              <div key={c.label}>
                <strong>{c.label}</strong> <small>{money(c.amount)}</small>
                <Bar percent={c.percent} />
              </div>
            )) : <p>Add expenses to see this month's breakdown.</p>
          ) : d.upgrade_status === 'pending' ? (
            <p>Your Premium request is awaiting review.</p>
          ) : (
            <>
              <p>Premium unlocks a monthly category breakdown.</p>
              {d.upgrade_status === 'rejected' && <small>Your previous request was declined.</small>}
              <button onClick={requestPremium}>Request an upgrade</button>
            </>
          )}
        </section>
      </div>
    </>
  );
}