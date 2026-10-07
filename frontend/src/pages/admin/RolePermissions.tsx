import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Card } from "../../components/Card";

const ROLE_LABELS: Record<string, string> = {
  bookkeeper: "Bookkeeper",
  accountant_manager: "Accountant Manager",
  auditor: "Auditor",
};

const MODULE_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  invoices: "Invoices",
  exceptions: "Exceptions",
  approvals: "Approvals",
  audit_log: "Audit Log",
  erp_connectors: "ERP Connectors",
  users: "Users",
  branding: "Branding",
};

export function RolePermissions() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["role-permissions"], queryFn: api.getRolePermissions });
  const [matrix, setMatrix] = useState<Record<string, string[]>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setMatrix(data.matrix);
  }, [data]);

  const mutation = useMutation({
    mutationFn: () => api.updateRolePermissions(matrix),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["role-permissions"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  function toggle(role: string, module: string) {
    setMatrix((m) => {
      const current = m[role] ?? [];
      const next = current.includes(module) ? current.filter((x) => x !== module) : [...current, module];
      return { ...m, [role]: next };
    });
  }

  if (isLoading || !data) {
    return <div className="text-sm text-slate-400">Loading…</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Role Permissions</h1>
      <p className="mt-1 text-sm text-slate-500">
        Control which pages each role can see. Admin always has full access and isn't shown here.
      </p>

      <Card className="mt-6 overflow-x-auto !p-0">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-6 py-3 font-medium">Module</th>
              {Object.keys(ROLE_LABELS).map((role) => (
                <th key={role} className="px-6 py-3 text-center font-medium">
                  {ROLE_LABELS[role]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.modules.map((module) => (
              <tr key={module} className="border-b border-surface-border last:border-0">
                <td className="px-6 py-3 font-medium text-slate-900">{MODULE_LABELS[module] ?? module}</td>
                {Object.keys(ROLE_LABELS).map((role) => (
                  <td key={role} className="px-6 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={(matrix[role] ?? []).includes(module)}
                      onChange={() => toggle(role, module)}
                      className="h-4 w-4 accent-brand-600"
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
        >
          {mutation.isPending ? "Saving…" : "Save changes"}
        </button>
        {saved && <span className="text-sm text-brand-600">Saved.</span>}
      </div>
    </div>
  );
}
