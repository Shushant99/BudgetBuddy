import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { NotificationContext } from '../notifications';
import NotificationIcon from './NotificationIcon';

const POLL_MS = 30000;   // how often to check for new notifications
const TOAST_MS = 6000;   // how long a pop-up stays on screen
const MAX_TOASTS = 3;

// Loads the user's notifications, keeps them fresh, and shows a pop-up for new ones.
export default function NotificationProvider({ children }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [toasts, setToasts] = useState([]);
  const lastSeen = useRef(null); // highest notification id already seen
  const onList = useRef(false);  // no pop-ups while the full list is open

  useEffect(() => {
    onList.current = pathname === '/notifications';
  }, [pathname]);

  const dismissToast = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  const refresh = useCallback(
    () => api('/notifications/', { params: { limit: 50 } })
      .then((data) => {
        setItems(data.results);
        setUnread(data.unread_count);
        setLoaded(true);

        const newest = data.results.reduce((max, n) => Math.max(max, n.id), 0);
        if (lastSeen.current !== null) {
          const fresh = data.results.filter((n) => n.id > lastSeen.current && !n.is_read).slice(0, MAX_TOASTS);
          if (fresh.length && !onList.current) {
            setToasts((t) => [...fresh, ...t].slice(0, MAX_TOASTS));
            fresh.forEach((n) => setTimeout(() => dismissToast(n.id), TOAST_MS));
          }
        }
        lastSeen.current = Math.max(lastSeen.current ?? 0, newest);
      })
      .catch(() => {}), // ignore: the next poll will try again
    [dismissToast],
  );

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, POLL_MS);
    const onVisible = () => { if (!document.hidden) refresh(); };
    window.addEventListener('bb:changed', refresh); // fired by api() after any change the user makes
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(timer);
      window.removeEventListener('bb:changed', refresh);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [refresh]);

  const markRead = useCallback((id) => {
    setItems((list) => list.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    return api(`/notifications/${id}/read/`, { method: 'POST' }).catch(refresh);
  }, [refresh]);

  const markAllRead = useCallback(() => {
    setItems((list) => list.map((n) => ({ ...n, is_read: true })));
    setUnread(0);
    return api('/notifications/read-all/', { method: 'POST' }).catch(refresh);
  }, [refresh]);

  const remove = useCallback((id) => {
    setItems((list) => list.filter((n) => n.id !== id));
    return api(`/notifications/${id}/`, { method: 'DELETE' }).catch(refresh);
  }, [refresh]);

  const clearAll = useCallback(() => {
    setItems([]);
    setUnread(0);
    return api('/notifications/', { method: 'DELETE' }).catch(refresh);
  }, [refresh]);

  const openToast = (n) => {
    markRead(n.id);
    dismissToast(n.id);
    navigate(n.link || '/notifications');
  };

  return (
    <NotificationContext.Provider value={{ items, unread, loaded, refresh, markRead, markAllRead, remove, clearAll }}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((n) => (
          <div key={n.id} className={`toast ${n.level}`}>
            <button className="toast-main" onClick={() => openToast(n)}>
              <NotificationIcon kind={n.kind} level={n.level} />
              <span>
                <strong>{n.title}</strong>
                <span>{n.message}</span>
              </span>
            </button>
            <button className="toast-x" aria-label="Dismiss" onClick={() => dismissToast(n.id)}>×</button>
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
}