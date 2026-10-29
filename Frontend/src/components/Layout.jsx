import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../AuthContext';

const links = [
  ['/dashboard', 'Overview'],
  ['/add-record', 'Add a record'],
  ['/transactions', 'Transactions'],
  ['/savings-goals', 'Savings goals'],
];

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <aside className="sidebar">
        <h2>Budget Buddy</h2>
        <nav>
          {links.map(([to, label]) => (
            <NavLink key={to} to={to}>{label}</NavLink>
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