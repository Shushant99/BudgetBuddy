import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessages } from '../api';
import { money } from '../utils';

// A tick list of the active budgets. Ticking one marks it as paid: the amount still
// unspent is recorded as an expense today. Unticking removes that expense again.
export default function BudgetChecklist({ items = [], onChange }) {
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');

  const toggle = async (item) => {
    setBusyId(item.id);
    setError('');
    try {
      await api(`/budgets/${item.id}/toggle-paid/`, { method: 'POST' });
      await onChange();
    } catch (e) {
      setError(errorMessages(e)[0]);
    } finally {
      setBusyId(null);
    }
  };

  if (!items.length) {
    return (
      <section className="panel checklist-panel">
        <h2>Budget checklist</h2>
        <p>Add a budget, like rent or food, and tick it off here once it is paid.</p>
        <Link to="/add-record?record_type=budget">Add a budget</Link>
      </section>
    );
  }

  const paidCount = items.filter((b) => b.paid).length;

  return (
    <section className="panel checklist-panel">
      <h2>Budget checklist</h2>
      <small>{paidCount} of {items.length} paid</small>

      {error && <p className="alert error checklist-error">{error}</p>}

      <ul className="checklist">
        {items.map((b) => {
          const left = Math.max(Number(b.amount) - Number(b.spent), 0);
          const locked = b.paid && !b.can_undo; // covered by expenses the user logged themselves
          // Show the new state straight away while the request runs; it reverts if the request fails.
          const paid = busyId === b.id ? !b.paid : b.paid;
          return (
            <li key={b.id} className={paid ? 'done' : undefined}>
              <label title={locked ? 'Already covered by expenses you logged' : undefined}>
                <input
                  type="checkbox"
                  checked={paid}
                  disabled={busyId !== null || locked}
                  onChange={() => toggle(b)}
                />
                <span className="check-text">
                  <strong>{b.category}</strong>
                  <small>
                    {paid ? (locked ? 'Paid from your expenses' : 'Paid') : `${money(left)} left to pay`}
                  </small>
                </span>
                <span className="amt">{money(b.amount)}</span>
              </label>
            </li>
          );
        })}
      </ul>

      <small className="checklist-hint">
        Ticking a budget records what is left of it as an expense today.
      </small>
    </section>
  );
}