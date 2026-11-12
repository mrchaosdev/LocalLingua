// Token stays in memory; no localStorage, query string or external requests.
export const API = location.port === '5173' ? 'http://127.0.0.1:8765' : location.origin;
export const sessionToken = new URLSearchParams(location.hash.slice(1)).get('token') || '';
if (location.hash) history.replaceState(null, '', location.pathname);
export function request(path: string, body?: unknown) {
  return fetch(API + path, {method: body === undefined ? 'GET' : 'POST',
    headers: {'Authorization': `Bearer ${sessionToken}`, 'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body)});
}
