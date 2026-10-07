import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../components/Card";

export function Landing() {
  const [slug, setSlug] = useState("");
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <img src="/logo-icon.png" alt="Ledgerly" className="mb-3 h-12 w-12 object-contain" />
          <h1 className="text-lg font-semibold text-slate-900">Ledgerly</h1>
          <p className="text-sm text-slate-500">Enter your workspace to continue</p>
        </div>
        <Card>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (slug.trim()) navigate(`/t/${slug.trim()}/login`);
            }}
            className="space-y-4"
          >
            <div>
              <label className="mb-1 block text-sm text-slate-600">Workspace URL</label>
              <div className="flex items-center rounded-lg border border-surface-border bg-surface focus-within:ring-1 focus-within:ring-brand-500">
                <span className="pl-3 text-sm text-slate-400">/t/</span>
                <input
                  autoFocus
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  placeholder="acme"
                  className="w-full rounded-lg bg-transparent px-1 py-2 text-sm text-slate-900 outline-none"
                />
              </div>
            </div>
            <button
              type="submit"
              className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
            >
              Continue
            </button>
          </form>
        </Card>
        <p className="mt-4 text-center text-xs text-slate-400">
          Ledgerly staff — <a href="/platform/login" className="underline">platform sign in</a>
        </p>
      </div>
    </div>
  );
}
