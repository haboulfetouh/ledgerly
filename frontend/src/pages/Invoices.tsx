import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { ProcessInvoiceModal } from "../components/ProcessInvoiceModal";
import { StatusBadge } from "../components/StatusBadge";
import { useTenantPath } from "../context/TenantContext";

export function Invoices() {
  const tenantPath = useTenantPath();
  const [modalOpen, setModalOpen] = useState(false);

  const { data: invoices, isLoading } = useQuery({
    queryKey: ["invoices"],
    queryFn: api.listInvoices,
    refetchInterval: 4000, // simple polling until a live extraction status finishes
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Invoices</h1>
          <p className="mt-1 text-sm text-slate-500">
            Every invoice ingested this month, with its match status.
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
        >
          Process new invoice
        </button>
      </div>

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
                <th className="px-6 py-3 font-medium">Received</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr
                  key={invoice.id}
                  className="border-b border-surface-border last:border-0 hover:bg-surface-sunken"
                >
                  <td className="px-6 py-4">
                    <Link to={tenantPath(`invoices/${invoice.id}`)} className="font-medium text-slate-900 hover:underline">
                      {invoice.vendor_name ?? "—"}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-slate-600">{invoice.invoice_number ?? "—"}</td>
                  <td className="px-6 py-4 text-slate-600">
                    {invoice.total_amount != null
                      ? `${invoice.currency ?? ""} ${invoice.total_amount.toLocaleString()}`
                      : "—"}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={invoice.status} />
                  </td>
                  <td className="px-6 py-4 text-slate-500">
                    {new Date(invoice.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6 text-sm text-slate-500">No invoices in this view.</div>
        )}
      </Card>

      <ProcessInvoiceModal open={modalOpen} onOpenChange={setModalOpen} />
    </div>
  );
}
