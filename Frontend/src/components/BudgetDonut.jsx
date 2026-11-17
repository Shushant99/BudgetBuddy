import { Link } from 'react-router-dom';
import { money } from '../utils';

const SIZE = 120;
const STROKE = 14;
const RADIUS = (SIZE - STROKE) / 2;
const CIRC = 2 * Math.PI * RADIUS;

// One arc of the ring. `start` and `share` are fractions (0–1) of the full circle.
function Arc({ start, share, color }) {
  const len = Math.min(Math.max(share, 0), 1) * CIRC;
  if (len <= 0) return null;
  return (
    <circle
      className="donut-arc"
      cx={SIZE / 2}
      cy={SIZE / 2}
      r={RADIUS}
      stroke={color}
      strokeDasharray={`${len} ${CIRC - len}`}
      strokeDashoffset={-start * CIRC}
      style={{ '--circ': CIRC }}
    />
  );
}

export default function BudgetDonut({ total, spent, overCount = 0 }) {
  const budget = Number(total) || 0;
  const used = Number(spent) || 0;

  if (budget <= 0) {
    return (
      <section className="panel donut-panel">
        <h2>Budget overview</h2>
        <p>Set a budget to see how your spending compares to it.</p>
        <Link to="/add-record">Add a budget</Link>
      </section>
    );
  }

  const ratio = used / budget;
  const isOver = used > budget;
  const extra = Math.max(used - budget, 0);
  const pct = Math.round(ratio * 100);

  // Under budget: one arc showing how much of the budget is used.
  // Over budget: the ring represents everything spent, split into the part the
  // budget covered and the overspend.
  const tone = ratio >= 0.75 ? 'var(--amber)' : 'var(--brand)';
  const arcs = isOver
    ? [
        { start: 0, share: budget / used, color: 'var(--brand)' },
        { start: budget / used, share: extra / used, color: 'var(--red)' },
      ]
    : [{ start: 0, share: ratio, color: tone }];

  const rows = isOver
    ? [
        { color: 'var(--brand)', label: 'Within budget', value: budget },
        { color: 'var(--red)', label: 'Over budget by', value: extra },
      ]
    : [
        { color: tone, label: 'Spent', value: used },
        { color: 'var(--line)', label: 'Remaining', value: budget - used },
      ];

  return (
    <section className="panel donut-panel">
      <h2>Budget overview</h2>
      <small>All active budgets</small>

      <div
        className="donut"
        role="img"
        aria-label={`Spent ${money(used)} of ${money(budget)} budget, ${pct}%${isOver ? `, over by ${money(extra)}` : ''}`}
      >
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} aria-hidden="true">
          <g transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}>
            <circle className="donut-track" cx={SIZE / 2} cy={SIZE / 2} r={RADIUS} />
            {arcs.map((a, i) => <Arc key={i} {...a} />)}
          </g>
        </svg>
        <div className="donut-center">
          <strong className={isOver ? 'minus' : ''}>{pct}%</strong>
          <small>of budget spent</small>
        </div>
      </div>

      <ul className="donut-legend">
        {rows.map((r) => (
          <li key={r.label}>
            <span className="dot" style={{ background: r.color }} />
            <span>{r.label}</span>
            <span className={`amt ${r.label.startsWith('Over') ? 'minus' : ''}`}>{money(r.value)}</span>
          </li>
        ))}
      </ul>

      <div className="donut-total">
        <span>{isOver ? 'Total spent' : 'Total budget'}</span>
        <strong>{money(isOver ? used : budget)}</strong>
      </div>

      {overCount > 0 && (
        <p className="donut-note">
          {overCount === 1 ? '1 budget is over its limit' : `${overCount} budgets are over their limits`}
        </p>
      )}
    </section>
  );
}