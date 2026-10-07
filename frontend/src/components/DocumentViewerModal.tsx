import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Modal } from "./Modal";

export function DocumentViewerModal({
  invoiceId,
  open,
  onOpenChange,
}: {
  invoiceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [doc, setDoc] = useState<{ url: string; filename: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setDoc(null);
    setError(null);
    api.getDocumentUrl(invoiceId).then(setDoc).catch((err) => setError(err.message));
  }, [open, invoiceId]);

  const isPdf = doc?.filename.toLowerCase().endsWith(".pdf");

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={doc?.filename ?? "Original document"} maxWidthClassName="max-w-3xl">
      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
      {!error && !doc && <div className="flex h-96 items-center justify-center text-sm text-slate-400">Loading document…</div>}
      {doc && !isPdf && (
        <img src={doc.url} alt={doc.filename} className="max-h-[70vh] w-full rounded-lg border border-surface-border object-contain" />
      )}
      {doc && isPdf && (
        <iframe src={doc.url} title={doc.filename} className="h-[70vh] w-full rounded-lg border border-surface-border" />
      )}
    </Modal>
  );
}
