import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type InvoiceFieldsUpdate } from "../api/client";
import { hasRole } from "../auth/keycloak";
import { Card } from "../components/Card";
import { DocumentViewerModal } from "../components/DocumentViewerModal";
import { StatusBadge } from "../components/StatusBadge";
import { useTenantPath } from "../context/TenantContext";

function ConfidencePill({ value }: { value: number | undefined }) {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  return (
    <span className={clsx("ml-2 text-xs font-medium", pct >= 90 ? "text-brand-600" : "text-amber-600")}>
      {pct}%
    </span>
  );
}

function Field({
  label,
  value,
  confidence,
}: {
  label: string;
  value: string | number | null | undefined;
  confidence?: number;
}) {
  return (
    <div className="flex items-center justify-between border-b border-surface-border py-3 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-900">
        {value ?? "—"}
        <ConfidencePill value={confidence} />
      </span>
    </div>
  );
}

function EditableField({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string | number | null;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-surface-border py-2 last:border-0">
      <label className="text-sm text-slate-500">{label}</label>
      <input
        type={type}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="w-48 rounded-md border border-surface-border bg-surface px-2 py-1 text-right text-sm text-slate-900"
      />
    </div>
  );
}

const ACTION_LABELS: Record<string, string> = {
  accept: "Accept (reject invoice)",
  override: "Override & proceed",
  escalate: "Escalate to accountant manager",
};

function ExceptionActions({ invoiceId }: { invoiceId: string }) {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (action: "accept" | "override" | "escalate") => api.resolveException(invoiceId, action, reason || undefined),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <Card className="mt-6">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Resolve exception</h2>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason (required for override / escalate)"
        rows={2}
        className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
      />
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {(["accept", "override", "escalate"] as const).map((action) => (
          <button
            key={action}
            disabled={mutation.isPending}
            onClick={() => mutation.mutate(action)}
            className="rounded-lg border border-surface-border px-3 py-2 text-sm font-medium text-slate-700 hover:bg-surface-sunken disabled:opacity-60"
          >
            {ACTION_LABELS[action]}
          </button>
        ))}
      </div>
    </Card>
  );
}

function ApprovalActions({ invoiceId }: { invoiceId: string }) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const approve = useMutation({
    mutationFn: () => api.approveInvoice(invoiceId, comment || undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] }),
    onError: (err: Error) => setError(err.message),
  });
  const reject = useMutation({
    mutationFn: () => api.rejectInvoice(invoiceId, comment || undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] }),
    onError: (err: Error) => setError(err.message),
  });

  if (!hasRole("accountant_manager") && !hasRole("admin")) {
    return (
      <Card className="mt-6">
        <p className="text-sm text-slate-500">Waiting on an accountant manager or admin to approve this invoice.</p>
      </Card>
    );
  }

  return (
    <Card className="mt-6">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Approval</h2>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Comment (optional)"
        rows={2}
        className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
      />
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}
      <div className="mt-3 flex gap-2">
        <button
          disabled={approve.isPending || reject.isPending}
          onClick={() => approve.mutate()}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
        >
          Approve
        </button>
        <button
          disabled={approve.isPending || reject.isPending}
          onClick={() => reject.mutate()}
          className="rounded-lg border border-rose-200 px-4 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-60"
        >
          Reject
        </button>
      </div>
    </Card>
  );
}

export function InvoiceDetail() {
  const { id } = useParams<{ id: string }>();
  const tenantPath = useTenantPath();
  const queryClient = useQueryClient();
  const [edited, setEdited] = useState<InvoiceFieldsUpdate>({});
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [awaitingMatch, setAwaitingMatch] = useState(false);
  const [docViewerOpen, setDocViewerOpen] = useState(false);

  const { data: invoice, isLoading } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => api.getInvoice(id!),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === "processing" || awaitingMatch ? 1500 : false,
  });

  // Matching runs asynchronously in a worker — keep polling past the single
  // post-mutation refetch until the status actually moves off needs_review,
  // otherwise the UI can show a stale "Needs Review" for a race-condition window.
  useEffect(() => {
    if (invoice && invoice.status !== "needs_review") {
      setAwaitingMatch(false);
    }
  }, [invoice?.status]);

  useEffect(() => {
    if (invoice && invoice.status === "needs_review") {
      setEdited({
        vendor_name: invoice.vendor_name,
        invoice_number: invoice.invoice_number,
        invoice_date: invoice.invoice_date,
        due_date: invoice.due_date,
        currency: invoice.currency,
        subtotal: invoice.subtotal,
        tax_amount: invoice.tax_amount,
        total_amount: invoice.total_amount,
        po_number: invoice.po_number,
      });
    }
  }, [invoice?.id, invoice?.status]);

  const confirmMutation = useMutation({
    mutationFn: async () => {
      await api.updateInvoiceFields(id!, edited);
      return api.runMatching(id!);
    },
    onSuccess: () => {
      setConfirmError(null);
      setAwaitingMatch(true);
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
    },
    onError: (err: Error) => setConfirmError(err.message),
  });

  if (isLoading || !invoice) {
    return <div className="text-sm text-slate-500">Loading…</div>;
  }

  const extraction = invoice.ai_outputs.find((o) => o.stage === "extraction");
  const confidences = extraction?.field_confidences ?? {};
  const latestMatch = invoice.match_records[0];
  const isEditing = invoice.status === "needs_review";

  return (
    <div>
      <Link to={tenantPath("invoices")} className="text-sm text-slate-500 hover:text-slate-900">
        ← Back to invoices
      </Link>

      <div className="mt-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">{invoice.vendor_name ?? invoice.source_filename}</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setDocViewerOpen(true)}
            className="text-sm font-medium text-brand-600 hover:underline"
          >
            View original document
          </button>
          <StatusBadge status={invoice.status} />
        </div>
      </div>

      {invoice.needs_review_reason && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {invoice.needs_review_reason}
        </div>
      )}
      {invoice.processing_error && (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {invoice.processing_error}
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Extracted fields</h2>
          {isEditing ? (
            <>
              <EditableField label="Vendor" value={edited.vendor_name ?? ""} onChange={(v) => setEdited((e) => ({ ...e, vendor_name: v }))} />
              <EditableField label="Invoice number" value={edited.invoice_number ?? ""} onChange={(v) => setEdited((e) => ({ ...e, invoice_number: v }))} />
              <EditableField label="Invoice date" type="date" value={edited.invoice_date ?? ""} onChange={(v) => setEdited((e) => ({ ...e, invoice_date: v }))} />
              <EditableField label="Due date" type="date" value={edited.due_date ?? ""} onChange={(v) => setEdited((e) => ({ ...e, due_date: v }))} />
              <EditableField label="PO number" value={edited.po_number ?? ""} onChange={(v) => setEdited((e) => ({ ...e, po_number: v }))} />
              <EditableField label="Currency" value={edited.currency ?? ""} onChange={(v) => setEdited((e) => ({ ...e, currency: v }))} />
              <EditableField
                label="Total amount"
                type="number"
                value={edited.total_amount ?? ""}
                onChange={(v) => setEdited((e) => ({ ...e, total_amount: v === "" ? null : Number(v) }))}
              />
              {confirmError && <p className="mt-2 text-sm text-rose-600">{confirmError}</p>}
              <button
                disabled={confirmMutation.isPending}
                onClick={() => confirmMutation.mutate()}
                className="mt-4 w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
              >
                {confirmMutation.isPending ? "Saving & matching…" : "Confirm fields & run matching"}
              </button>
            </>
          ) : (
            <>
              <Field label="Vendor" value={invoice.vendor_name} confidence={confidences.vendor_name} />
              <Field label="Invoice number" value={invoice.invoice_number} confidence={confidences.invoice_number} />
              <Field label="Invoice date" value={invoice.invoice_date} confidence={confidences.invoice_date} />
              <Field label="Due date" value={invoice.due_date} confidence={confidences.due_date} />
              <Field label="PO number" value={invoice.po_number} confidence={confidences.po_number} />
              <Field
                label="Total amount"
                value={invoice.total_amount != null ? `${invoice.currency ?? ""} ${invoice.total_amount.toLocaleString()}` : null}
                confidence={confidences.total_amount}
              />
            </>
          )}
        </Card>

        <Card>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Line items</h2>
          {invoice.line_items.length === 0 ? (
            <p className="text-sm text-slate-500">No line items extracted.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2 font-medium">Description</th>
                  <th className="pb-2 font-medium">Qty</th>
                  <th className="pb-2 font-medium">Unit price</th>
                  <th className="pb-2 font-medium">Total</th>
                </tr>
              </thead>
              <tbody>
                {invoice.line_items.map((item) => (
                  <tr key={item.id} className="border-t border-surface-border">
                    <td className="py-2 text-slate-700">{item.description ?? "—"}</td>
                    <td className="py-2 text-slate-600">{item.quantity ?? "—"}</td>
                    <td className="py-2 text-slate-600">{item.unit_price ?? "—"}</td>
                    <td className="py-2 text-slate-600">{item.line_total ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      {latestMatch && (
        <Card className="mt-6">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Match result</h2>
          <div className="flex items-center gap-2">
            <StatusBadge status={latestMatch.status} />
          </div>
          {latestMatch.discrepancy_detail && (
            <p className="mt-3 text-sm text-slate-600">{latestMatch.discrepancy_detail}</p>
          )}
          {latestMatch.explanation && (
            <div className="mt-3 rounded-lg border border-surface-border bg-surface px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">AI explanation</p>
              <p className="mt-1 text-sm text-slate-700">{latestMatch.explanation}</p>
            </div>
          )}
          {latestMatch.resolution_action && (
            <p className="mt-3 text-xs text-slate-500">
              Resolved: {latestMatch.resolution_action} — {latestMatch.resolution_reason ?? "no reason given"}
            </p>
          )}
        </Card>
      )}

      {invoice.status === "exception" && <ExceptionActions invoiceId={invoice.id} />}
      {(invoice.status === "matched" || invoice.status === "matched_tolerance") && (
        <ApprovalActions invoiceId={invoice.id} />
      )}

      {invoice.approval_records.length > 0 && (
        <Card className="mt-6">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Approval history</h2>
          {invoice.approval_records.map((a) => (
            <p key={a.id} className="text-sm text-slate-600">
              {a.decision} · {a.comment ?? "no comment"} · {new Date(a.created_at).toLocaleString()}
            </p>
          ))}
        </Card>
      )}

      {extraction && (
        <Card className="mt-6">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">AI extraction metadata</h2>
          <p className="text-sm text-slate-500">
            Model <span className="text-slate-700">{extraction.model_name}</span> · overall confidence
            <ConfidencePill value={extraction.confidence_overall ?? undefined} /> · {new Date(extraction.created_at).toLocaleString()}
          </p>
        </Card>
      )}

      <DocumentViewerModal invoiceId={invoice.id} open={docViewerOpen} onOpenChange={setDocViewerOpen} />
    </div>
  );
}
