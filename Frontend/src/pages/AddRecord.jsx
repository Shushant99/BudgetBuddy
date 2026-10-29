import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, errorMessages } from '../api';
import Errors from '../components/Errors';

const CATEGORIES = [
  ['housing', 'Housing'], ['food', 'Food'], ['transport', 'Transport'],
  ['utilities', 'Utilities'], ['healthcare', 'Healthcare'], ['entertainment', 'Entertainment'],
  ['shopping', 'Shopping'], ['education', 'Education'], ['other', 'Other'],
];

const FORMS = {
  income: { label: 'Income', fields: [
    { name: 'source', label: 'Source', type: 'text' },
    { name: 'amount', label: 'Amount', type: 'number' },
    { name: 'received_on', label: 'Received on', type: 'date' },
    { name: 'notes', label: 'Notes', type: 'textarea', optional: true },
  ] },
  expense: { label: 'Expense', fields: [
    { name: 'category', label: 'Category', type: 'select' },
    { name: 'description', label: 'Description', type: 'text', optional: true },
    { name: 'amount', label: 'Amount', type: 'number' },
    { name: 'spent_on', label: 'Spent on', type: 'date' },
    { name: 'notes', label: 'Notes', type: 'textarea', optional: true },
  ] },
  budget: { label: 'Budget', fields: [
    { name: 'category', label: 'Category', type: 'select' },
    { name: 'amount', label: 'Amount', type: 'number' },
    { name: 'start_date', label: 'Start date', type: 'date' },
    { name: 'end_date', label: 'End date', type: 'date' },
  ] },
  goal: { label: 'Savings goal', fields: [
    { name: 'name', label: 'Goal name', type: 'text' },
    { name: 'target_amount', label: 'Target amount', type: 'number' },
    { name: 'current_amount', label: 'Already saved', type: 'number' },
    { name: 'target_date', label: 'Target date', type: 'date', optional: true },
  ] },
};

const today = () => new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD in local time

export default function AddRecord() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const start = FORMS[params.get('record_type')] ? params.get('record_type') : 'income';

  const [type, setType] = useState(start);
  const [values, setValues] = useState({
    received_on: today(), spent_on: today(), start_date: today(), current_amount: '0',
  });
  const [errors, setErrors] = useState([]);

  const onChange = (e) => setValues({ ...values, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    const body = { record_type: type };
    FORMS[type].fields.forEach(({ name }) => {
      if (values[name] !== undefined && values[name] !== '') body[name] = values[name];
    });
    try {
      await api('/records/', { method: 'POST', body });
      navigate(type === 'goal' ? '/savings-goals' : '/dashboard');
    } catch (err) {
      setErrors(errorMessages(err));
    }
  };

  return (
    <>
      <header className="page-header"><h1>Add a record</h1></header>
      <form className="card form" onSubmit={onSubmit}>
        <Errors messages={errors} />
        <label>What would you like to add?
          <select value={type} onChange={(e) => { setType(e.target.value); setErrors([]); }}>
            {Object.entries(FORMS).map(([key, f]) => (
              <option key={key} value={key}>{f.label}</option>
            ))}
          </select>
        </label>

        {FORMS[type].fields.map((f) => (
          <label key={f.name}>{f.label}
            {f.type === 'select' ? (
              <select name={f.name} value={values[f.name] || ''} onChange={onChange} required>
                <option value="">Select…</option>
                {CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            ) : f.type === 'textarea' ? (
              <textarea name={f.name} rows="3" value={values[f.name] || ''} onChange={onChange} />
            ) : (
              <input
                type={f.type}
                name={f.name}
                value={values[f.name] || ''}
                onChange={onChange}
                required={!f.optional}
                step={f.type === 'number' ? '0.01' : undefined}
                min={f.type === 'number' ? '0' : undefined}
              />
            )}
          </label>
        ))}
        <button>Save record</button>
      </form>
    </>
  );
}