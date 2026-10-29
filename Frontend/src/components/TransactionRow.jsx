import { fmtDate, money } from '../utils';

export default function TransactionRow({ t }) {
  const incoming = t.kind === 'income';
  return (
    <article className="row">
      <span className={`pill ${t.kind}`}>{t.kind}</span>
      <span className="grow">
        <strong>{t.title}</strong>
        <small>{t.detail} · {fmtDate(t.date)}</small>
      </span>
      <strong className={incoming ? 'plus' : 'minus'}>
        {incoming ? '+' : '−'}{money(t.amount)}
      </strong>
    </article>
  );
}