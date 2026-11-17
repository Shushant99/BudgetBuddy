import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessages } from '../api';
import { money } from '../utils';
import TransactionRow from '../components/TransactionRow';
import BudgetDonut from '../components/BudgetDonut';
import MoneyDonut from '../components/MoneyDonut';
import BudgetChecklist from '../components/BudgetChecklist';
import AlertStrip from '../components/AlertStrip';

function Stat({ label, value, note }) {
  return (
    <article className="card stat">
      <small>{label}</small>
      <strong>{money(value)}</strong>
      {note && <small>{note}</small>}
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
  const load = useCallback(() => api('/dashboard/').then(setD), []);

  useEffect(() => {
    load().catch((e) => setError(errorMessages(e)[0]));
  }, [load]);

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
            
      <AlertStrip />

      {notice && <p className="alert info">{notice}</p>}

      <div className="dash-layout">
        <div className="dash-main">
          <section className="stats">
            <Stat
              label="Available balance"
              value={d.monthly_balance}
              note={Number(d.carried_over) ? `Includes ${money(d.carried_over)} carried over` : undefined}
            />
            <Stat label="Money in" value={d.monthly_income} />
            <Stat label="Money out" value={d.monthly_expenses} />
            <Stat label="Saved this month" value={d.monthly_savings} note={`${money(d.total_saved)} saved in total`} />
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
        </div>

        <aside className="dash-aside">
          <MoneyDonut allocation={d.allocation} carriedOver={d.carried_over} />
          <BudgetChecklist items={d.budget_checklist} onChange={load} />
          <BudgetDonut total={d.budget_total} spent={d.budget_spent} overCount={d.budgets_over} />
        </aside>
      </div>
    </>
  );
}