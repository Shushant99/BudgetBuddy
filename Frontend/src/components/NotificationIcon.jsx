
const PATHS = {
  income: <path d="M12 5v14M6 13l6 6 6-6" />,
  expense: <path d="M12 19V5M6 11l6-6 6 6" />,
  budget: <><path d="M21 12a9 9 0 1 1-9-9" /><path d="M12 3v9h9" /></>,
  savings: <path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" />,
  warning: <><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18v.01" /></>,
  account: <><circle cx="12" cy="8" r="4" /><path d="M4 21c1-4 4-6 8-6s7 2 8 6" /></>,
  general: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.01" /></>,
};

// Round icon whose colour follows the notification level (info / success / warning / danger).
export default function NotificationIcon({ kind, level = 'info' }) {
  return (
    <span className={`notif-icon tone-${level}`}>
      <svg
        viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      >
        {PATHS[kind] || PATHS.general}
      </svg>
    </span>
  );
}

