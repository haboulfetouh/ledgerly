import Keycloak from "keycloak-js";

const STORAGE_KEY = "ledgerly_tokens";

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL;
const REALM = import.meta.env.VITE_KEYCLOAK_REALM;
const CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID;

export const keycloak = new Keycloak({
  url: KEYCLOAK_URL,
  realm: REALM,
  clientId: CLIENT_ID,
});

if (import.meta.env.DEV) {
  // dev-only escape hatch for manual API testing from the browser console
  (window as unknown as { __keycloak: Keycloak }).__keycloak = keycloak;
}

interface StoredTokens {
  token: string;
  refreshToken: string;
  idToken: string;
}

function readStoredTokens(): StoredTokens | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredTokens;
  } catch {
    return null;
  }
}

function persistTokens(): void {
  if (!keycloak.token || !keycloak.refreshToken || !keycloak.idToken) return;
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ token: keycloak.token, refreshToken: keycloak.refreshToken, idToken: keycloak.idToken }),
  );
}

function clearStoredTokens(): void {
  localStorage.removeItem(STORAGE_KEY);
}

let initPromise: Promise<boolean> | null = null;

/** Boots the Keycloak instance without ever forcing a redirect — each
 * tenant (and the platform portal) has its own in-app login page instead
 * of Keycloak's hosted one. If tokens were persisted from a previous
 * password-grant login, hydrate the session from them; otherwise the app
 * just boots unauthenticated and the router decides which login page to show.
 */
export function initKeycloak(): Promise<boolean> {
  if (!initPromise) {
    const stored = readStoredTokens();
    keycloak.onAuthRefreshSuccess = persistTokens;
    keycloak.onAuthLogout = clearStoredTokens;

    initPromise = keycloak
      .init({
        onLoad: undefined,
        checkLoginIframe: false,
        ...(stored ?? {}),
      })
      .then((authenticated) => {
        if (stored && !authenticated) {
          // stored refresh token was no longer valid — drop it
          clearStoredTokens();
        }
        return authenticated;
      });
  }
  return initPromise;
}

/** Resource Owner Password Credentials grant against Keycloak's token
 * endpoint, used by our own branded login pages in place of a redirect to
 * Keycloak's hosted UI. Persists tokens and hard-reloads so the single
 * `keycloak.init()` call above picks them up cleanly on boot — keycloak-js
 * doesn't support re-hydrating a live instance with new tokens post-init.
 */
export async function passwordLogin(username: string, password: string): Promise<void> {
  const response = await fetch(`${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "password",
      client_id: CLIENT_ID,
      username,
      password,
    }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error_description || "Invalid email or password.");
  }

  const data = await response.json();
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ token: data.access_token, refreshToken: data.refresh_token, idToken: data.id_token }),
  );
}

export function logout(redirectTo: string): void {
  const stored = readStoredTokens();
  clearStoredTokens();
  if (stored?.refreshToken) {
    // best-effort session revocation — logout must not hang on this
    fetch(`${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ client_id: CLIENT_ID, refresh_token: stored.refreshToken }),
    }).catch(() => {});
  }
  window.location.href = redirectTo;
}

export function hasRole(role: string): boolean {
  return keycloak.hasRealmRole(role);
}

export function tenantIdFromToken(): string | undefined {
  return (keycloak.tokenParsed as { tenant_id?: string } | undefined)?.tenant_id;
}
