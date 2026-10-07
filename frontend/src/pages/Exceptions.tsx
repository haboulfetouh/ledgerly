import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { useTenantPath } from "../context/TenantContext";

export function Exceptions() {
  const tenantPath = useTenantPath();
  const { data: invoices, isLoading } = useQuery({
    queryKey: ["invoices", ["exception"]],
    queryFn: () => api.listInvoices(["exception"]),
    refetchInterval: 5000,
  });

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Exceptions</h1>
      <p className="mt-1 text-sm text-slate-500">
        Invoices that need a human decision, oldest first.
      </p>

      <Card className="mt-6 overflow-hidden !p-0">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading…</div>
        ) : invoices && invoices.length > 0 ? (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-3 font-medium">Vendor</th>
                <th className="px-6 py-3 font-medium">Invoice</th>
                <th className="px-6 py-3 font-medium">Amount</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Opened</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id} className="border-b border-surface-border last:border-0 hover:bg-surface-sunken">
                  <td className="px-6 py-4">
                    <Link to={tenantPath(`invoices/${invoice.id}`)} className="font-medium text-slate-900 hover:underline">
                      {invoice.vendor_name ?? "—"}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-slate-600">{invoice.invoice_number ?? "—"}</td>
                  <td className="px-6 py-4 text-slate-600">
                    {invoice.total_amount != null ? `${invoice.currency ?? ""} ${invoice.total_amount.toLocaleString()}` : "—"}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={invoice.status} />
                  </td>
                  <td className="px-6 py-4 text-slate-500">{new Date(invoice.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6 text-sm text-slate-500">No open exceptions.</div>
        )}
      </Card>
    </div>
  );
}
