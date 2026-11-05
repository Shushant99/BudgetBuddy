import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useNotifications } from '../notifications';
import NotificationProvider from './NotificationProvider';

const links = [
  ['/dashboard', 'Overview'],
  ['/add-record', 'Add a record'],
  ['/transactions', 'Transactions'],
  ['/savings-goals', 'Savings goals'],
  ['/notifications', 'Notifications'],
];

function Shell() {
  const { user, logout } = useAuth();
  const { unread } = useNotifications();
  return (
    <div className="shell">
      <aside className="sidebar">
        <h2>Budget Buddy</h2>
        <nav>
          {links.map(([to, label]) => (
            <NavLink key={to} to={to}>
              {label}
              {to === '/notifications' && unread > 0 && (
                <span className="nav-badge" aria-label={`${unread} unread`}>{unread > 99 ? '99+' : unread}</span>
              )}
            </NavLink>
          ))}
          {user.is_staff && (
            <a href="http://127.0.0.1:8000/admin/" target="_blank" rel="noreferrer">Administration</a>
          )}
        </nav>
        <div className="sidebar-user">
          <strong>{user.name}</strong>
          <small>{user.email}</small>
          <button onClick={logout}>Log out</button>
        </div>
      </aside>
      <main className="content"><Outlet /></main>
    </div>
  );
}

export default function Layout() {
  return (
    <NotificationProvider>
      <Shell />
    </NotificationProvider>
  );
}