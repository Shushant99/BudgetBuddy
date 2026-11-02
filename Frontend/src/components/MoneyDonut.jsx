import { Fragment } from 'react';
import { Link } from 'react-router-dom';
import { money } from '../utils';

const SIZE = 120;
const RADIUS = 53;
const CIRC = 2 * Math.PI * RADIUS;

const SPENT = '#475569';
const SAVED = 'var(--green)';
// Colours for the money reserved for each budget category (in order of size).
const RESERVED = ['#8b5cf6', '#06b6d4', '#f59e0b', '#ec4899', '#14b8a6'];
const MAX_RESERVED = RESERVED.length;

const whole = (v) => '₹ ' + Math.round(v).toLocaleString('en-IN');

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

// Splits everything available this month (income + what was carried over) into
// spent, saved, reserved for budgets (per category) and free money.
export default function MoneyDonut({ allocation, carriedOver = 0 }) {
  const a = allocation || {};
  const available = Number(a.available) || 0;
  const spent = Number(a.spent) || 0;
  const saved = Number(a.saved) || 0;
  const free = Number(a.free) || 0;

  if (available <= 0) {
    return (
      <section className="panel donut-panel">
        <h2>Where your money goes</h2>
        <p>Add your income to see how it is split between spending, savings and budgets.</p>
        <Link to="/add-record">Add income</Link>
      </section>
    );
  }

  // Reserved money per budget category; anything past the colour palette is grouped.
  const reserved = (a.reserved || [])
    .map((r) => ({ label: r.label, amount: Number(r.amount) || 0 }))
    .filter((r) => r.amount > 0);
  const shown = reserved.slice(0, MAX_RESERVED);
  const rest = reserved.slice(MAX_RESERVED).reduce((sum, r) => sum + r.amount, 0);
  if (rest > 0) shown.push({ label: 'Other budgets', amount: rest });

  const segments = [
    { label: 'Spent', amount: spent, color: SPENT },
    { label: 'Saved', amount: saved, color: SAVED },
    ...shown.map((r, i) => ({ label: r.label, amount: r.amount, color: RESERVED[i] || '#94a3b8', reserved: true })),
  ].filter((s) => s.amount > 0);

  const committed = segments.reduce((sum, s) => sum + s.amount, 0);
  const overCommitted = committed > available;
  const base = Math.max(available, committed); // the ring is a share of this total

  let cursor = 0;
  const arcs = segments.map((s) => {
    const share = s.amount / base;
    const arc = { ...s, start: cursor, share };
    cursor += share;
    return arc;
  });

  const rows = overCommitted ? segments : [...segments, { label: 'Free to use', amount: free, color: 'var(--line)' }];
  const pctOf = (v) => Math.round((v / base) * 100);

  return (
    <section className="panel donut-panel">
      <h2>Where your money goes</h2>
      <small>This month, incl. carried over</small>

      <div
        className="donut"
        role="img"
        aria-label={`Of ${money(available)} available: ${rows.map((r) => `${r.reserved ? 'reserved for ' : ''}${r.label} ${money(r.amount)}`).join(', ')}`}
      >
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} aria-hidden="true">
          <g transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}>
            <circle className="donut-track" cx={SIZE / 2} cy={SIZE / 2} r={RADIUS} />
            {arcs.map((s) => <Arc key={s.label} start={s.start} share={s.share} color={s.color} />)}
          </g>
        </svg>
        <div className="donut-center">
          <strong className="donut-amount">{whole(available)}</strong>
          <small>available</small>
        </div>
      </div>

      <ul className="donut-legend">
        {rows.map((r, i) => (
          <Fragment key={r.label}>
            {r.reserved && !rows[i - 1]?.reserved && <li className="legend-group">Reserved for budgets</li>}
            <li className={r.reserved ? 'sub' : undefined}>
              <span className="dot" style={{ background: r.color }} />
              <span>{r.label}<small className="pct">{pctOf(r.amount)}%</small></span>
              <span className="amt">{money(r.amount)}</span>
            </li>
          </Fragment>
        ))}
      </ul>

      <div className="donut-total">
        <span>Total available</span>
        <strong>{money(available)}</strong>
      </div>
      {Number(carriedOver) !== 0 && (
        <small className="donut-sub">Includes {money(carriedOver)} carried over from earlier months</small>
      )}

      {overCommitted && (
        <p className="donut-note">
          Spent, saved and reserved money is {money(committed - available)} more than you have available.
        </p>
      )}
    </section>
  );
}