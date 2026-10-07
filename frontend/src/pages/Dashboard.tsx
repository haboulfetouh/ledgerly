import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";

function KpiTile({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-slate-900">{value}</div>
    </Card>
  );
}

export function Dashboard() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ["dashboard-metrics"],
    queryFn: api.getDashboardMetrics,
    refetchInterval: 10000,
  });

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
      <p className="mt-1 text-sm text-slate-500">
        Every invoice ingested this month, with its match status.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Invoices processed" value={isLoading ? "…" : String(metrics?.invoices_processed ?? 0)} />
        <KpiTile label="Needs review" value={isLoading ? "…" : String(metrics?.needs_review ?? 0)} />
        <KpiTile
          label="Touchless rate"
          value={isLoading || metrics?.touchless_rate == null ? "—" : `${metrics.touchless_rate}%`}
        />
        <KpiTile label="Open exceptions" value={isLoading ? "…" : String(metrics?.exception_count ?? 0)} />
        <KpiTile
          label="Avg. exception age"
          value={isLoading || metrics?.exception_aging_days_avg == null ? "—" : `${metrics.exception_aging_days_avg}d`}
        />
        <KpiTile label="Pending approval" value={isLoading ? "…" : String(metrics?.pending_approval_count ?? 0)} />
      </div>

      {!isLoading && metrics?.invoices_processed === 0 && (
        <Card className="mt-8">
          <p className="text-sm text-slate-500">
            No data yet — your first invoices will appear here.
          </p>
        </Card>
      )}
    </div>
  );
}
