export default function Errors({ messages }) {
  if (!messages.length) return null;
  return (
    <ul className="alert error">
      {messages.map((m) => <li key={m}>{m}</li>)}
    </ul>
  );
}