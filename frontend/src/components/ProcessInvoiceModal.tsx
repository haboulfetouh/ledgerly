import { useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type InvoiceDetail } from "../api/client";
import { useTenantPath } from "../context/TenantContext";
import { Modal } from "./Modal";

type Step = "pick" | "scanning" | "done" | "error";

interface FieldTag {
  label: string;
  className: string;
  delayMs: number;
}

const FIELD_TAGS: FieldTag[] = [
  { label: "Vendor", className: "left-4 top-4", delayMs: 300 },
  { label: "PO number", className: "right-4 top-4", delayMs: 700 },
  { label: "Invoice date", className: "right-4 top-16", delayMs: 1100 },
  { label: "Total amount", className: "right-4 bottom-4", delayMs: 1500 },
];

function ScanningPreview({ file }: { file: File }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const isImage = file.type.startsWith("image/");

  useEffect(() => {
    if (!isImage) return;
    const url = URL.createObjectURL(file);
    setObjectUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file, isImage]);

  return (
    <div className="relative overflow-hidden rounded-xl border border-surface-border bg-amber-50/40">
      <div className="absolute inset-0 z-10 animate-[scan_2.2s_ease-in-out_infinite] bg-gradient-to-b from-transparent via-amber-200/40 to-transparent" />
      {isImage && objectUrl ? (
        <img src={objectUrl} alt={file.name} className="max-h-80 w-full object-contain" />
      ) : (
        <div className="flex h-80 flex-col items-center justify-center gap-3 text-slate-400">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6" />
          </svg>
          <span className="text-sm font-medium text-slate-500">{file.name}</span>
        </div>
      )}
      {FIELD_TAGS.map((tag) => (
        <span
          key={tag.label}
          style={{ animationDelay: `${tag.delayMs}ms` }}
          className={clsx(
            "absolute z-20 animate-[fadeInTag_0.4s_ease-out_forwards] rounded-md bg-accent px-2 py-1 text-[11px] font-medium text-white opacity-0 shadow-raised",
            tag.className,
          )}
        >
          {tag.label}
        </span>
      ))}
    </div>
  );
}

function statusNote(invoice: InvoiceDetail): string {
  switch (invoice.status) {
    case "needs_review":
      return invoice.needs_review_reason ?? "Some fields need your review before this can proceed.";
    case "exception":
      return invoice.match_records[0]?.discrepancy_detail ?? "This invoice needs your attention.";
    case "matched":
    case "matched_tolerance":
      return "Matched cleanly against the purchase order and goods receipt. Sent to the approval queue — no further action needed.";
    default:
      return "Processed successfully.";
  }
}

export function ProcessInvoiceModal({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [step, setStep] = useState<Step>("pick");
  const [file, setFile] = useState<File | null>(null);
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const tenantPath = useTenantPath();

  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);

  // Polls explicitly rather than via useQuery's refetchInterval — this
  // component's lifetime is short and single-purpose (one upload, one
  // outcome), so a plain interval is simpler to reason about here than
  // wiring up the shared query cache's background-refetch behavior.
  useEffect(() => {
    if (!invoiceId || step !== "scanning") return;

    let cancelled = false;
    const poll = async () => {
      const result = await api.getInvoice(invoiceId);
      if (cancelled) return;
      setInvoice(result);
      if (result.status !== "processing") {
        setStep("done");
        queryClient.invalidateQueries({ queryKey: ["invoices"] });
        queryClient.invalidateQueries({ queryKey: ["dashboard-metrics"] });
      }
    };

    poll();
    const interval = setInterval(poll, 1200);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [invoiceId, step, queryClient]);

  function reset() {
    setStep("pick");
    setFile(null);
    setInvoiceId(null);
    setInvoice(null);
    setError(null);
  }

  async function handleFile(selected: File) {
    setFile(selected);
    setStep("scanning");
    try {
      const result = await api.uploadInvoice(selected);
      setInvoiceId(result.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStep("error");
    }
  }

  const extraction = invoice?.ai_outputs.find((o) => o.stage === "extraction");
  const confidences = extraction?.field_confidences ?? {};

  return (
    <Modal
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
      title="Process a new invoice"
      maxWidthClassName="max-w-xl"
    >
      <style>{`
        @keyframes scan { 0% { transform: translateY(-100%); } 100% { transform: translateY(400%); } }
        @keyframes fadeInTag { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {step === "pick" && (
        <div>
          <p className="mb-4 text-sm text-slate-500">
            Upload an invoice — Ledgerly AI will scan, extract, match and route it, live.
          </p>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              const dropped = e.dataTransfer.files?.[0];
              if (dropped) handleFile(dropped);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={clsx(
              "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors",
              dragActive ? "border-brand-400 bg-brand-50" : "border-surface-border hover:bg-surface-sunken",
            )}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-slate-400">
              <path d="M12 16V4M12 4l-4 4M12 4l4 4" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="text-sm font-medium text-slate-900">
              Drag &amp; drop an invoice here <br /> or <span className="text-brand-600 underline">browse your files</span>
            </p>
            <p className="text-xs text-slate-400">PDF, PNG or JPG — scanned or photographed invoices work fine</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,image/png,image/jpeg"
            className="hidden"
            onChange={(e) => {
              const selected = e.target.files?.[0];
              if (selected) handleFile(selected);
            }}
          />
        </div>
      )}

      {step === "scanning" && file && (
        <div>
          <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            Scanning document (OCR)
          </div>
          <ScanningPreview file={file} />
          <p className="mt-3 truncate text-xs text-slate-400">
            {file.name} · {(file.size / 1024).toFixed(0)} KB
          </p>
        </div>
      )}

      {step === "done" && invoice && (
        <div>
          <div className="space-y-1 divide-y divide-surface-border rounded-xl border border-surface-border">
            {[
              { label: "Vendor", value: invoice.vendor_name, confidence: confidences.vendor_name },
              { label: "Invoice number", value: invoice.invoice_number, confidence: confidences.invoice_number },
              { label: "Purchase order", value: invoice.po_number, confidence: confidences.po_number },
              {
                label: "Total amount",
                value: invoice.total_amount != null ? `${invoice.currency ?? ""} ${invoice.total_amount.toLocaleString()}` : null,
                confidence: confidences.total_amount,
              },
            ].map((row) => (
              <div key={row.label} className="flex items-center justify-between px-4 py-3">
                <span className="text-sm text-slate-500">{row.label}</span>
                <span className="text-sm font-medium text-slate-900">
                  {row.value ?? "—"}
                  {row.confidence != null && (
                    <span className="ml-2 text-xs font-medium text-brand-600">{Math.round(row.confidence * 100)}%</span>
                  )}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-lg border border-surface-border bg-surface-sunken px-4 py-3">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Ledgerly AI</p>
            <p className="text-sm text-slate-700">{statusNote(invoice)}</p>
          </div>

          <button
            onClick={() => {
              const id = invoice.id;
              reset();
              onOpenChange(false);
              navigate(tenantPath(`invoices/${id}`));
            }}
            className="mt-4 w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
          >
            View result
          </button>
        </div>
      )}

      {step === "error" && (
        <div>
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error ?? "Something went wrong."}
          </div>
          <button
            onClick={reset}
            className="mt-4 w-full rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-slate-700 hover:bg-surface-sunken"
          >
            Try again
          </button>
        </div>
      )}
    </Modal>
  );
}
