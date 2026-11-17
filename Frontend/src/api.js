const TOKEN_KEY = 'bb_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

export class ApiError extends Error {
  constructor(status, errors) {
    super('Request failed');
    this.status = status;
    this.errors = errors;
  }
}

export async function api(path, { method = 'GET', body, params } = {}) {
  const qs = new URLSearchParams(Object.entries(params || {}).filter(([, v]) => v)).toString();
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;

  const res = await fetch(`/api${path}${qs ? `?${qs}` : ''}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = res.status === 204 ? null : await res.json().catch(() => null);

  if (!res.ok) {
    if (res.status === 401 && token) {
      setToken(null);
      localStorage.removeItem('bb_user');
      window.location.href = '/login';
    }
    throw new ApiError(res.status, data || {});
  }
    if (method !== 'GET') window.dispatchEvent(new Event('bb:changed')); 
  
  return data;
}

export function errorMessages(err) {
  const out = Object.entries(err?.errors || {}).flatMap(([key, val]) =>
    (Array.isArray(val) ? val : [String(val)]).map((m) =>
      key === 'non_field_errors' || key === 'detail' ? m : `${key.replace(/_/g, ' ')}: ${m}`
    )
  );
  return out.length ? out : ['Something went wrong. Please try again.'];
}
// Downloads a file from the API (e.g. a CSV report) using the logged-in user's token.
export async function downloadFile(path, params = {}, fallbackName = 'download') {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  const token = getToken();
  const res = await fetch(`/api${path}${qs ? `?${qs}` : ''}`, {
    headers: token ? { Authorization: `Token ${token}` } : {},
  });
  if (!res.ok) {
    if (res.status === 401 && token) {
      setToken(null);
      localStorage.removeItem('bb_user');
      window.location.href = '/login';
    }
    throw new ApiError(res.status, await res.json().catch(() => ({})));
  }
  const name = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') || '')?.[1] || fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}