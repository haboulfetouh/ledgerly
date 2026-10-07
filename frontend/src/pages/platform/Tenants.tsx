import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { Card } from "../../components/Card";

export function Tenants() {
  const { data: tenants, isLoading } = useQuery({
    queryKey: ["platform-tenants"],
    queryFn: api.listPlatformTenants,
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Tenants</h1>
          <p className="mt-1 text-sm text-slate-500">Every workspace onboarded on Ledgerly.</p>
        </div>
        <Link
          to="/platform/tenants/new"
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
        >
          Onboard tenant
        </Link>
      </div>

      <Card className="mt-6 overflow-hidden !p-0">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading…</div>
        ) : tenants && tenants.length > 0 ? (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-3 font-medium">Name</th>
                <th className="px-6 py-3 font-medium">Workspace URL</th>
                <th className="px-6 py-3 font-medium">Plan</th>
                <th className="px-6 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id} className="border-b border-surface-border last:border-0 hover:bg-surface-sunken">
                  <td className="px-6 py-4 font-medium text-slate-900">
                    <Link to={`/platform/tenants/${t.id}`} className="hover:underline">
                      {t.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-slate-600">/t/{t.slug}</td>
                  <td className="px-6 py-4 text-slate-600">{t.plan}</td>
                  <td className="px-6 py-4 text-slate-500">{new Date(t.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6 text-sm text-slate-500">No tenants yet.</div>
        )}
      </Card>
    </div>
  );
}
