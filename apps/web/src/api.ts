// Per-run token is isolated to this browser tab; no localStorage or URL query string.
export const API = location.port === '5173' ? 'http://127.0.0.1:8765' : location.origin;
const fragmentToken=new URLSearchParams(location.hash.slice(1)).get('token');
// Per-tab session storage survives refresh. Tokens are invalid after the launcher exits.
export const sessionToken=fragmentToken||sessionStorage.getItem('locallingua.session')||'';
if(fragmentToken)sessionStorage.setItem('locallingua.session',fragmentToken);
if (location.hash) history.replaceState(null, '', location.pathname);
export function request(path: string, body?: unknown) {
  return fetch(API + path, {method: body === undefined ? 'GET' : 'POST',
    headers: {'Authorization': `Bearer ${sessionToken}`, 'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body)});
}
