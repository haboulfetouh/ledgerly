import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";

export function AuditLog() {
  const { data: events, isLoading } = useQuery({
    queryKey: ["audit-log"],
    queryFn: api.listAuditLog,
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Audit Log</h1>
          <p className="mt-1 text-sm text-slate-500">
            Every match, override, and approval event — immutable and exportable.
          </p>
        </div>
        <button
          onClick={() => api.downloadAuditLogCsv()}
          className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-slate-700 hover:bg-surface-sunken"
        >
          Export CSV
        </button>
      </div>

      <Card className="mt-6 overflow-hidden !p-0">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading…</div>
        ) : events && events.length > 0 ? (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-3 font-medium">When</th>
                <th className="px-6 py-3 font-medium">Actor</th>
                <th className="px-6 py-3 font-medium">Action</th>
                <th className="px-6 py-3 font-medium">Entity</th>
                <th className="px-6 py-3 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id} className="border-b border-surface-border last:border-0">
                  <td className="px-6 py-4 text-slate-500">{new Date(event.created_at).toLocaleString()}</td>
                  <td className="px-6 py-4 text-slate-600">{event.actor_subject ?? "system"}</td>
                  <td className="px-6 py-4 font-medium text-slate-900">{event.action}</td>
                  <td className="px-6 py-4 text-slate-500">{event.entity_type}/{event.entity_id.slice(0, 8)}</td>
                  <td className="max-w-md truncate px-6 py-4 text-slate-500" title={JSON.stringify(event.after)}>
                    {JSON.stringify(event.after)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6 text-sm text-slate-500">No audit events yet.</div>
        )}
      </Card>
    </div>
  );
}
