import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";
import { Card } from "../../components/Card";
import { Modal } from "../../components/Modal";

const PLANS = ["starter", "growth", "enterprise"];

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-slate-900">{value}</div>
    </Card>
  );
}

function ResetPasswordModal({
  tenantId,
  open,
  onOpenChange,
}: {
  tenantId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [password, setPassword] = useState("");
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.resetTenantAdminPassword(tenantId, password),
    onSuccess: () => setSuccess(true),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <Modal
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          setPassword("");
          setSuccess(false);
          setError(null);
        }
        onOpenChange(o);
      }}
      title="Reset admin password"
    >
      {success ? (
        <p className="text-sm text-brand-700">Password reset. Share the new password with the tenant securely.</p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <p className="text-sm text-slate-500">
            This resets the password for every user holding the Admin role in this workspace.
          </p>
          <div>
            <label className="mb-1 block text-sm text-slate-600">New password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
            />
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
          >
            {mutation.isPending ? "Resetting…" : "Reset password"}
          </button>
        </form>
      )}
    </Modal>
  );
}

export function TenantDetail() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const queryClient = useQueryClient();
  const [resetModalOpen, setResetModalOpen] = useState(false);

  const { data: tenant, isLoading } = useQuery({
    queryKey: ["platform-tenant", tenantId],
    queryFn: () => api.getPlatformTenant(tenantId!),
    enabled: !!tenantId,
  });

  const planMutation = useMutation({
    mutationFn: (plan: string) => api.updatePlatformTenantPlan(tenantId!, plan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-tenant", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["platform-tenants"] });
    },
  });

  if (isLoading || !tenant) {
    return <div className="text-sm text-slate-500">Loading…</div>;
  }

  return (
    <div>
      <Link to="/platform/tenants" className="text-sm text-slate-500 hover:text-slate-900">
        ← Back to tenants
      </Link>

      <div className="mt-2 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{tenant.name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            /t/{tenant.slug} · {tenant.admin_email ?? "no admin user found"}
          </p>
        </div>
        <button
          onClick={() => setResetModalOpen(true)}
          className="rounded-lg border border-surface-border px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-surface-sunken"
        >
          Reset admin password
        </button>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Invoices processed" value={String(tenant.stats.invoices_processed)} />
        <StatTile label="Needs review" value={String(tenant.stats.invoices_needs_review)} />
        <StatTile label="Exceptions" value={String(tenant.stats.invoices_exception)} />
        <StatTile label="Posted to ERP" value={String(tenant.stats.invoices_posted)} />
        <StatTile label="Users" value={String(tenant.stats.user_count)} />
        <StatTile label="ERP connected" value={tenant.stats.erp_connected ? "Yes" : "No"} />
      </div>

      <Card className="mt-6 max-w-sm">
        <div className="text-sm font-medium text-slate-900">Subscription plan</div>
        <p className="mt-1 text-xs text-slate-500">Controls billing tier — no feature gating tied to this yet.</p>
        <select
          value={tenant.plan}
          onChange={(e) => planMutation.mutate(e.target.value)}
          disabled={planMutation.isPending}
          className="mt-3 w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
        >
          {PLANS.map((p) => (
            <option key={p} value={p}>
              {p[0].toUpperCase() + p.slice(1)}
            </option>
          ))}
        </select>
      </Card>

      <ResetPasswordModal tenantId={tenant.id} open={resetModalOpen} onOpenChange={setResetModalOpen} />
    </div>
  );
}
