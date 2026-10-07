import { useState } from "react";
import { passwordLogin } from "../auth/keycloak";
import { Card } from "../components/Card";
import { useTenant } from "../context/TenantContext";

export function TenantLogin() {
  const { slug, branding, logoUrl } = useTenant();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await passwordLogin(email, password);
      window.location.href = `/t/${slug}/`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          {logoUrl ? (
            <img src={logoUrl} alt={branding.name} className="mb-3 h-12 w-12 object-contain" />
          ) : (
            <img src="/logo-icon.png" alt="Ledgerly" className="mb-3 h-12 w-12 object-contain" />
          )}
          <h1 className="text-lg font-semibold text-slate-900">{branding.name}</h1>
          <p className="text-sm text-slate-500">Sign in to your workspace</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm text-slate-600">Email</label>
              <input
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-600">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
              />
            </div>
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              style={{ backgroundColor: branding.primary_color }}
              className="w-full rounded-lg px-4 py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-60"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </Card>
      </div>
    </div>
  );
}
