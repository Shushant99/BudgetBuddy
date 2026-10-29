import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessages } from '../api';
import Errors from '../components/Errors';
import TransactionRow from '../components/TransactionRow';

const EMPTY = { record_type: 'all', from_date: '', to_date: '' };

export default function Transactions() {
  const [filters, setFilters] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [errors, setErrors] = useState([]);

  useEffect(() => {
    api('/transactions/', { params: { ...filters, page } })
      .then((data) => { setResult(data); setErrors([]); })
      .catch((e) => setErrors(errorMessages(e)));
  }, [filters, page]);

  const update = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
    setPage(1);
  };

  return (
    <>
      <header className="page-header">
        <h1>Transaction history</h1>
        <Link className="btn" to="/add-record">＋ Add record</Link>
      </header>

      <div className="filters">
        <label>Type
          <select name="record_type" value={filters.record_type} onChange={update}>
            <option value="all">All</option>
            <option value="income">Income</option>
            <option value="expense">Expenses</option>
            <option value="savings">Savings</option>
          </select>
        </label>
        <label>From
          <input type="date" name="from_date" value={filters.from_date} onChange={update} />
        </label>
        <label>To
          <input type="date" name="to_date" value={filters.to_date} onChange={update} />
        </label>
        <button className="ghost" onClick={() => { setFilters(EMPTY); setPage(1); }}>Clear</button>
      </div>

      <Errors messages={errors} />

      <section className="panel">
        {!result ? <p>Loading…</p> : (
          <>
            <h2>{result.count} transaction{result.count === 1 ? '' : 's'}</h2>
            {result.results.map((t) => <TransactionRow key={t.id} t={t} />)}
            {result.num_pages > 1 && (
              <div className="pager">
                <button className="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
                <span>Page {result.page} of {result.num_pages}</span>
                <button className="ghost" disabled={page >= result.num_pages} onClick={() => setPage(page + 1)}>Next</button>
              </div>
            )}
          </>
        )}
      </section>
    </>
  );
}