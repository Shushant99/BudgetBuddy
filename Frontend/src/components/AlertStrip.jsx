import { Link } from 'react-router-dom';
import { useNotifications } from '../notifications';
import NotificationIcon from './NotificationIcon';

// Unread warnings and alerts, shown at the top of the dashboard.
export default function AlertStrip() {
  const { items, markRead } = useNotifications();
  const alerts = items.filter((n) => !n.is_read && (n.level === 'warning' || n.level === 'danger')).slice(0, 3);
  if (!alerts.length) return null;

  return (
    <section className="alert-strip" aria-label="Alerts">
      {alerts.map((n) => (
        <div key={n.id} className={`alert-item ${n.level}`}>
          <NotificationIcon kind={n.kind} level={n.level} />
          <div className="alert-text">
            <strong>{n.title}</strong>
            <span>{n.message}</span>
          </div>
          <button className="ghost" onClick={() => markRead(n.id)}>Dismiss</button>
        </div>
      ))}
      <Link className="more" to="/notifications">View all notifications</Link>
    </section>
  );
}