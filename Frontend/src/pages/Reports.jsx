import { useEffect, useState } from 'react';
import { useAuth } from '../AuthContext';
import { api, downloadFile, errorMessages } from '../api';
import Errors from '../components/Errors';
import { fmtDate, money } from '../utils';

const PRESETS = [
  ['this_month', 'This month'],
  ['last_month', 'Last month'],
  ['last_3', 'Last 3 months'],
  ['last_6', 'Last 6 months'],
  ['this_year', 'This year'],
  ['month', 'Pick a month'],
  ['custom', 'Custom range'],
];
const TYPES = [['all', 'All'], ['income', 'Income'], ['expense', 'Expenses'], ['savings', 'Savings']];
const CATEGORIES = [
  ['housing', 'Housing'], ['food', 'Food'], ['transport', 'Transport'],
  ['utilities', 'Utilities'], ['healthcare', 'Healthcare'], ['entertainment', 'Entertainment'],
  ['shopping', 'Shopping'], ['education', 'Education'], ['other', 'Other'],
];
// Chart / table columns: [field in the report, heading, kind]
const SERIES = [['income', 'Money in', 'income'], ['expenses', 'Money out', 'expense'], ['savings', 'Saved', 'savings']];
const KIND_LABEL = { income: 'Income', expense: 'Expense', savings: 'Savings' };
const PLOT_HEIGHT = 140; // px

const pad = (n) => String(n).padStart(2, '0');
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

// The last 3 years of months, newest first, for the "Pick a month" list.
const MONTHS = Array.from({ length: 36 }, (_, i) => {
  const d = new Date(new Date().getFullYear(), new Date().getMonth() - i, 1);
  return [`${d.getFullYear()}-${pad(d.getMonth() + 1)}`, d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })];
});

function rangeFor(preset, month, customFrom, customTo) {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  const monthRange = (year, mon, lastMon = mon) => [iso(new Date(year, mon, 1)), iso(new Date(year, lastMon + 1, 0))];
  switch (preset) {
    case 'this_month': return monthRange(y, m);
    case 'last_month': return monthRange(y, m - 1);
    case 'last_3': return monthRange(y, m - 2, m);
    case 'last_6': return monthRange(y, m - 5, m);
    case 'this_year': return monthRange(y, 0, 11);
    case 'month': {
      const [year, mon] = month.split('-').map(Number);
      return monthRange(year, mon - 1);
    }
    default: return [customFrom, customTo];
  }
}

// "▲ 12% vs previous period", green when the change is good news and red when it is not.
function Delta({ current, previous, upIsGood }) {
  const cur = Number(current);
  const prev = Number(previous);
  if (!prev) return <small className="delta flat">{cur ? 'Nothing in the previous period' : 'No activity'}</small>;
  const pct = Math.round(((cur - prev) / prev) * 100);
  if (pct === 0) return <small className="delta flat">Same as the previous period</small>;
  const up = pct > 0;
  return (
    <small className={`delta ${up === upIsGood ? 'good' : 'bad'}`}>
      {up ? '▲' : '▼'} {Math.abs(pct)}% vs previous period
    </small>
  );
}

export default function Reports() {
  const { user } = useAuth();
  const [preset, setPreset] = useState('this_month');
  const [month, setMonth] = useState(MONTHS[0][0]);
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [type, setType] = useState('all');
  const [category, setCategory] = useState('');
  const [result, setResult] = useState({ key: '', data: null, errors: [] });
  const [exporting, setExporting] = useState(false);
  const [exportErrors, setExportErrors] = useState([]);

  const [from, to] = rangeFor(preset, month, customFrom, customTo);
  const rangeError = from && to && from > to ? 'The start date must be on or before the end date.' : '';
  const ready = Boolean(from && to) && !rangeError;
  const key = `${from}|${to}|${type}|${category}`;

  useEffect(() => {
    if (!ready) return undefined;
    let stale = false;
    api('/reports/', { params: { from_date: from, to_date: to, record_type: type, category } })
      .then((data) => { if (!stale) setResult({ key, data, errors: [] }); })
      .catch((e) => { if (!stale) setResult({ key, data: null, errors: errorMessages(e) }); });
    return () => { stale = true; };
  }, [ready, from, to, type, category, key]);

  const d = result.data;
  const loading = ready && result.key !== key;

  const pickType = (value) => {
    setType(value);
    if (value !== 'expense') setCategory('');
  };

  const exportCsv = async () => {
    setExporting(true);
    setExportErrors([]);
    try {
      await downloadFile('/reports/export/', { from_date: from, to_date: to, record_type: type, category });
    } catch (e) {
      setExportErrors(errorMessages(e));
    } finally {
      setExporting(false);
    }
  };

  // What the report on screen is about (taken from the report itself, not from the form).
  const kind = d?.filters.record_type;
  const shownSeries = d ? SERIES.filter(([, , k]) => kind === 'all' || kind === k) : [];
  const showLeftOver = kind === 'all';

  let body = null;
  if (!ready) {
    body = <p className="panel">{rangeError || 'Choose a start and an end date to see the report.'}</p>;
  } else if (d) {
    const t = d.totals;
    const p = d.previous;
    const spendPerDay = Number(t.expenses) / d.period.days;
    const savingsRate = Number(t.income) ? Math.round((Number(t.savings) / Number(t.income)) * 100) : null;
    const maxBar = Math.max(1, ...d.by_month.flatMap((m) => shownSeries.map(([field]) => Number(m[field]))));

    body = (
      <div className={loading ? 'report loading' : 'report'}>
        <section className="print-only report-head">
          <h1>Budget Buddy: financial report</h1>
          <p>Prepared for {user.name} · generated {new Date(d.generated_at).toLocaleString('en-IN')}</p>
          <p>
            Period: {fmtDate(d.period.from_date)} to {fmtDate(d.period.to_date)}
            {' · '}Showing: {TYPES.find(([v]) => v === kind)[1]}
            {d.filters.category && ` · Category: ${CATEGORIES.find(([v]) => v === d.filters.category)?.[1]}`}
          </p>
        </section>

        <section className="stats">
          {SERIES.filter(([, , k]) => kind === 'all' || kind === k).map(([field, label, k]) => (
            <article key={field} className="card stat">
              <small>{label}</small>
              <strong>{money(t[field])}</strong>
              <Delta current={t[field]} previous={p[field]} upIsGood={k !== 'expense'} />
            </article>
          ))}
          {showLeftOver && (
            <article className="card stat">
              <small>Left over</small>
              <strong className={Number(t.left_over) < 0 ? 'minus' : ''}>{money(t.left_over)}</strong>
              <small>Money in − out − saved</small>
            </article>
          )}
        </section>

        <p className="report-insights">
          <span><strong>{d.transaction_count}</strong> transaction{d.transaction_count === 1 ? '' : 's'}</span>
          {Number(t.expenses) > 0 && <span>Average spending <strong>{money(spendPerDay)}</strong> per day</span>}
          {showLeftOver && savingsRate !== null && <span>Saved <strong>{savingsRate}%</strong> of income</span>}
          <span className="muted">Compared with {fmtDate(p.from_date)} to {fmtDate(p.to_date)}</span>
        </p>

        {d.transaction_count === 0 ? (
          <p className="panel">No transactions match these filters.</p>
        ) : (
          <>
            {d.by_month.length > 1 && (
              <section className="panel">
                <h2>Month by month</h2>
                <div className="legend">
                  {shownSeries.map(([field, label, k]) => <span key={field}><i className={`swatch ${k}`} />{label}</span>)}
                </div>
                <div className="mchart" role="img" aria-label="Bar chart of each month">
                  {d.by_month.map((m) => (
                    <div key={m.month} className="mgroup">
                      <div className="mbars">
                        {shownSeries.map(([field, label, k]) => {
                          const v = Number(m[field]);
                          return (
                            <span
                              key={field}
                              className={`mbar ${k}`}
                              title={`${m.label}: ${label} ${money(v)}`}
                              style={{ height: v ? Math.max(3, (v / maxBar) * PLOT_HEIGHT) : 0 }}
                            />
                          );
                        })}
                      </div>
                      <span className="mlabel">{m.label}</span>
                    </div>
                  ))}
                </div>
                <div className="table-scroll">
                  <table className="report-table">
                    <thead>
                      <tr>
                        <th>Month</th>
                        {shownSeries.map(([field, label]) => <th key={field} className="num">{label}</th>)}
                        {showLeftOver && <th className="num">Left over</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {d.by_month.map((m) => (
                        <tr key={m.month}>
                          <td>{m.label}</td>
                          {shownSeries.map(([field]) => <td key={field} className="num">{money(m[field])}</td>)}
                          {showLeftOver && (
                            <td className={`num ${Number(m.left_over) < 0 ? 'minus' : ''}`}>{money(m.left_over)}</td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td>Total</td>
                        {shownSeries.map(([field]) => <td key={field} className="num">{money(t[field])}</td>)}
                        {showLeftOver && <td className="num">{money(t.left_over)}</td>}
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </section>
            )}

            {d.by_category.length > 0 && (
              <section className="panel keep-together">
                <h2>Spending by category</h2>
                {d.by_category.map((c) => (
                  <div key={c.category} className="cat-row">
                    <div className="cat-line">
                      <strong>{c.label}</strong>
                      <span>{money(c.amount)} <small className="inline">· {c.percent}%</small></span>
                    </div>
                    <div className="progress"><span style={{ width: `${c.percent}%` }} /></div>
                  </div>
                ))}
              </section>
            )}

            <section className="panel">
              <h2>Transactions</h2>
              <div className="table-scroll">
                <table className="report-table">
                  <thead>
                    <tr>
                      <th>Date</th><th>Type</th><th>Category</th><th>Description</th><th className="num">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.transactions.map((tx) => (
                      <tr key={tx.id}>
                        <td>{fmtDate(tx.date)}</td>
                        <td><span className={`pill ${tx.kind}`}>{KIND_LABEL[tx.kind]}</span></td>
                        <td>{tx.category || '—'}</td>
                        <td>{tx.description || tx.category || KIND_LABEL[tx.kind]}</td>
                        <td className={`num ${tx.kind === 'income' ? 'plus' : 'minus'}`}>
                          {tx.kind === 'income' ? '+' : '−'}{money(tx.amount)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {d.truncated && (
                <p className="report-note">
                  Showing the newest {d.transactions.length} of {d.transaction_count} transactions.
                  Download the CSV to get all of them.
                </p>
              )}
            </section>
          </>
        )}
      </div>
    );
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Money in, money out and savings</p>
          <h1>Reports</h1>
        </div>
        <div className="report-actions">
          <button className="ghost" onClick={exportCsv} disabled={!ready || !d || exporting}>
            {exporting ? 'Preparing…' : 'Download CSV'}
          </button>
          <button onClick={() => window.print()} disabled={!ready || !d}>Print / Save as PDF</button>
        </div>
      </header>

      <section className="panel report-filters">
        <div className="chips" role="group" aria-label="Report period">
          {PRESETS.map(([value, label]) => (
            <button key={value} className="chip" aria-pressed={preset === value} onClick={() => setPreset(value)}>
              {label}
            </button>
          ))}
        </div>

        <div className="filters">
          {preset === 'month' && (
            <label>Month
              <select value={month} onChange={(e) => setMonth(e.target.value)}>
                {MONTHS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          )}
          {preset === 'custom' && (
            <>
              <label>From
                <input type="date" value={customFrom} onChange={(e) => setCustomFrom(e.target.value)} />
              </label>
              <label>To
                <input type="date" value={customTo} onChange={(e) => setCustomTo(e.target.value)} />
              </label>
            </>
          )}
          <label>Show
            <select value={type} onChange={(e) => pickType(e.target.value)}>
              {TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          {type === 'expense' && (
            <label>Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">All categories</option>
                {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          )}
        </div>
        {ready && <small>{fmtDate(from)} to {fmtDate(to)}{loading && ' · updating…'}</small>}
        {rangeError && <p className="alert error">{rangeError}</p>}
      </section>

      <Errors messages={[...result.errors, ...exportErrors]} />
      {ready && !d && !result.errors.length && <p>Loading…</p>}
      {body}
    </>
  );
}