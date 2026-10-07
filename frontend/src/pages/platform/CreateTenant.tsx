import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { Card } from "../../components/Card";

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function CreateTenant() {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: api.createPlatformTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-tenants"] });
      navigate("/platform/tenants");
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="text-2xl font-semibold text-slate-900">Onboard a tenant</h1>
      <p className="mt-1 text-sm text-slate-500">Creates the workspace and its first admin user.</p>

      <Card className="mt-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            mutation.mutate({ name, slug, admin_email: adminEmail, admin_password: adminPassword });
          }}
          className="space-y-4"
        >
          <div>
            <label className="mb-1 block text-sm text-slate-600">Organization name</label>
            <input
              required
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (!slugTouched) setSlug(slugify(e.target.value));
              }}
              className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-600">Workspace URL</label>
            <div className="flex items-center rounded-lg border border-surface-border bg-surface">
              <span className="pl-3 text-sm text-slate-400">/t/</span>
              <input
                required
                value={slug}
                onChange={(e) => {
                  setSlug(slugify(e.target.value));
                  setSlugTouched(true);
                }}
                className="w-full rounded-lg bg-transparent px-1 py-2 text-sm text-slate-900 outline-none"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-600">First admin email</label>
            <input
              type="email"
              required
              value={adminEmail}
              onChange={(e) => setAdminEmail(e.target.value)}
              className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-600">First admin password</label>
            <input
              type="password"
              required
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
            />
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
          >
            {mutation.isPending ? "Creating…" : "Create tenant"}
          </button>
        </form>
      </Card>
    </div>
  );
}
