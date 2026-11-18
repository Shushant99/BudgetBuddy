import { useEffect, useState } from 'react';
import { api, errorMessages } from '../api';

// Lets the user choose which alerts are also sent to their email address, and send a test email.
export default function EmailSettings() {
  const [settings, setSettings] = useState(null);
  const [status, setStatus] = useState({ kind: '', text: '' });
  const [sending, setSending] = useState(false);

  useEffect(() => {
    api('/email-settings/')
      .then(setSettings)
      .catch((e) => setStatus({ kind: 'error', text: errorMessages(e)[0] }));
  }, []);

  const update = async (field, value) => {
    const previous = settings;
    setSettings({ ...settings, [field]: value }); // show the change straight away
    setStatus({ kind: '', text: '' });
    try {
      setSettings(await api('/email-settings/', { method: 'PATCH', body: { [field]: value } }));
    } catch (e) {
      setSettings(previous);
      setStatus({ kind: 'error', text: errorMessages(e)[0] });
    }
  };

  const sendTest = async () => {
    setSending(true);
    setStatus({ kind: '', text: '' });
    try {
      const res = await api('/email-settings/test/', { method: 'POST' });
      setStatus({ kind: res.delivered ? 'ok' : 'info', text: res.detail });
    } catch (e) {
      setStatus({ kind: 'error', text: errorMessages(e)[0] });
    } finally {
      setSending(false);
    }
  };

  if (!settings) {
    return status.text ? <p className="alert error">{status.text}</p> : null;
  }

  return (
    <section className="panel email-settings">
      <div className="email-head">
        <div>
          <h2>Email alerts</h2>
          <small>Sent to <strong>{settings.email}</strong></small>
        </div>
        <button className="ghost" onClick={sendTest} disabled={sending}>
          {sending ? 'Sending…' : 'Send test email'}
        </button>
      </div>

      {!settings.configured && (
        <p className="email-warning">Email delivery is not set up on this server yet, so nothing is being sent.</p>
      )}

      <div className="email-options">
        <label>
          <input
            type="checkbox"
            checked={settings.email_alerts}
            onChange={(e) => update('email_alerts', e.target.checked)}
          />
          <span>
            <strong>Email me important alerts</strong>
            <small>Budget warnings, overspending, savings goals and account updates.</small>
          </span>
        </label>
        <label className={settings.email_alerts ? '' : 'off'}>
          <input
            type="checkbox"
            checked={settings.email_transactions}
            disabled={!settings.email_alerts}
            onChange={(e) => update('email_transactions', e.target.checked)}
          />
          <span>
            <strong>Also email every income and expense</strong>
            <small>A receipt for each transaction you add.</small>
          </span>
        </label>
      </div>

      {status.text && (
        <p className={`alert ${status.kind === 'error' ? 'error' : 'info'} email-status`}>{status.text}</p>
      )}
    </section>
  );
}