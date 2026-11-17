import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import NotificationIcon from '../components/NotificationIcon';
import { useNotifications } from '../notifications';

const isAlert = (n) => n.level === 'warning' || n.level === 'danger';

const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();

function dayLabel(iso) {
  const d = new Date(iso);
  const diff = Math.round((startOfDay(new Date()) - startOfDay(d)) / 86400000);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Yesterday';
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function timeAgo(iso) {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins} min ago`;
  if (mins < 1440) return `${Math.floor(mins / 60)} hr ago`;
  return new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
}

const EMPTY = {
  all: 'You have no notifications yet. Money in, money out and budget alerts will show up here.',
  unread: 'You are all caught up.',
  alerts: 'No warnings right now.',
};

export default function Notifications() {
  const { items, unread, loaded, markRead, markAllRead, remove, clearAll } = useNotifications();
  const navigate = useNavigate();
  const [tab, setTab] = useState('all');

  const tabs = [
    ['all', 'All', items.length],
    ['unread', 'Unread', unread],
    ['alerts', 'Alerts', items.filter(isAlert).length],
  ];
  const shown = items.filter((n) => (tab === 'unread' ? !n.is_read : tab === 'alerts' ? isAlert(n) : true));

  // Group by day, keeping the newest first.
  const groups = [];
  shown.forEach((n) => {
    const label = dayLabel(n.created_at);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.items.push(n);
    else groups.push({ label, items: [n] });
  });

  const open = (n) => {
    if (!n.is_read) markRead(n.id);
    if (n.link) navigate(n.link);
  };

  const confirmClear = () => {
    if (window.confirm('Delete all notifications?')) clearAll();
  };

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">{unread ? `${unread} unread` : 'All caught up'}</p>
          <h1>Notifications</h1>
        </div>
        <div className="notif-actions">
          <button className="ghost" onClick={markAllRead} disabled={!unread}>Mark all as read</button>
          <button className="ghost" onClick={confirmClear} disabled={!items.length}>Clear all</button>
        </div>
      </header>

      <div className="notif-tabs" role="group" aria-label="Filter notifications">
        {tabs.map(([key, label, count]) => (
          <button key={key} aria-pressed={tab === key} onClick={() => setTab(key)}>
            {label}<span>{count}</span>
          </button>
        ))}
      </div>

      {!loaded && <p>Loading…</p>}
      {loaded && !shown.length && <p className="panel">{EMPTY[tab]}</p>}

      {groups.map((g) => (
        <section key={g.label}>
          <h2 className="notif-day">{g.label}</h2>
          <ul className="notif-list">
            {g.items.map((n) => (
              <li key={n.id} className={`notif ${n.level} ${n.is_read ? '' : 'unread'}`}>
                <button className="notif-main" onClick={() => open(n)}>
                  <NotificationIcon kind={n.kind} level={n.level} />
                  <span className="notif-body">
                    <strong>{n.title}</strong>
                    <span>{n.message}</span>
                    <small>{timeAgo(n.created_at)}</small>
                  </span>
                  {!n.is_read && <span className="unread-dot" role="img" aria-label="Unread" />}
                </button>
                <button className="notif-x" aria-label={`Delete: ${n.title}`} onClick={() => remove(n.id)}>×</button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}