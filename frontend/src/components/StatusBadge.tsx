import clsx from "clsx";

const STATUS_STYLES: Record<string, string> = {
  processing: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200",
  needs_review: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
  extracted: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200",
  matched: "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200",
  matched_tolerance: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
  exception: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
  approved: "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200",
  posted: "bg-slate-100 text-slate-700 ring-1 ring-inset ring-slate-200",
  rejected: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
};

const STATUS_LABELS: Record<string, string> = {
  processing: "Processing",
  needs_review: "Needs Review",
  extracted: "Extracted",
  matched: "Matched",
  matched_tolerance: "Tolerance",
  exception: "Exception",
  approved: "Approved",
  posted: "Posted",
  rejected: "Rejected",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200",
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}
