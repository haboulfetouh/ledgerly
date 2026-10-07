import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { api, type ConnectionTestResult, type ConnectorType, type ErpConnection } from "../../api/client";
import { Card } from "../../components/Card";
import { Modal } from "../../components/Modal";

function ConnectionStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    connected: "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200",
    error: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
    not_configured: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200",
  };
  const labels: Record<string, string> = {
    connected: "Connected",
    error: "Connection failed",
    not_configured: "Not tested yet",
  };
  return (
    <span className={clsx("rounded-full px-2.5 py-1 text-xs font-medium", styles[status])}>
      {labels[status] ?? status}
    </span>
  );
}

function ConnectorFormModal({
  open,
  onOpenChange,
  editing,
  onTestRequested,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editing: ErpConnection | null;
  onTestRequested: (connectionId: string) => void;
}) {
  const queryClient = useQueryClient();
  const [selectedType, setSelectedType] = useState<ConnectorType | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [config, setConfig] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [prefilling, setPrefilling] = useState(false);

  const { data: types } = useQuery({ queryKey: ["connector-types"], queryFn: api.listConnectorTypes });

  // Editing an existing connection: skip the type picker and prefill its
  // current (decrypted) config so a client can fix a typo without
  // re-entering every field from scratch.
  useEffect(() => {
    if (!open || !editing || !types) return;
    const type = types.find((t) => t.connector_type === editing.connector_type) ?? null;
    setSelectedType(type);
    setDisplayName(editing.display_name);
    setPrefilling(true);
    api
      .getErpConnectionConfig(editing.id)
      .then((res) => setConfig(res.config))
      .finally(() => setPrefilling(false));
  }, [open, editing, types]);

  function reset() {
    setSelectedType(null);
    setDisplayName("");
    setConfig({});
    setError(null);
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editing) {
        return api.updateErpConnection(editing.id, { display_name: displayName, config });
      }
      if (!selectedType) throw new Error("No connector type selected");
      return api.createErpConnection({ connector_type: selectedType.connector_type, display_name: displayName, config });
    },
    onSuccess: (connection) => {
      queryClient.invalidateQueries({ queryKey: ["erp-connections"] });
      reset();
      onOpenChange(false);
      onTestRequested(connection.id);
    },
    onError: (err: Error) => setError(err.message),
  });

  const title = editing ? `Edit ${editing.display_name}` : selectedType ? `Connect ${selectedType.display_name}` : "Connect an ERP";

  if (!editing && !selectedType) {
    return (
      <Modal open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }} title={title}>
        <p className="mb-4 text-sm text-slate-500">Choose which ERP this tenant uses.</p>
        <div className="grid grid-cols-2 gap-3">
          {(types ?? []).map((type) => (
            <button
              key={type.connector_type}
              disabled={!type.implemented}
              onClick={() => {
                setSelectedType(type);
                setDisplayName(type.display_name);
              }}
              className={clsx(
                "rounded-lg border px-4 py-3 text-left text-sm",
                type.implemented
                  ? "border-surface-border hover:border-brand-500 hover:bg-surface-sunken"
                  : "cursor-not-allowed border-surface-border/50 opacity-50",
              )}
            >
              <div className="font-medium text-slate-900">{type.display_name}</div>
              {!type.implemented && <div className="mt-1 text-xs text-slate-500">Coming soon</div>}
            </button>
          ))}
        </div>
      </Modal>
    );
  }

  if (!selectedType) {
    return (
      <Modal open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }} title={title}>
        <p className="text-sm text-slate-500">Loading…</p>
      </Modal>
    );
  }

  return (
    <Modal open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }} title={title}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          saveMutation.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <label className="mb-1 block text-sm text-slate-500">Display name</label>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
          />
        </div>
        {prefilling ? (
          <p className="text-sm text-slate-500">Loading current configuration…</p>
        ) : (
          selectedType.config_schema.map((field) => (
            <div key={field.name}>
              <label className="mb-1 block text-sm text-slate-500">{field.label}</label>
              <input
                type={field.type === "password" ? "password" : "text"}
                required={field.required}
                value={config[field.name] ?? ""}
                onChange={(e) => setConfig((c) => ({ ...c, [field.name]: e.target.value }))}
                className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
              />
              {field.help_text && <p className="mt-1 text-xs text-slate-500">{field.help_text}</p>}
            </div>
          ))
        )}

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <div className="flex justify-between pt-2">
          {editing ? (
            <span />
          ) : (
            <button type="button" onClick={() => setSelectedType(null)} className="text-sm text-slate-500 hover:text-slate-900">
              ← Back
            </button>
          )}
          <button
            type="submit"
            disabled={saveMutation.isPending || prefilling}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
          >
            {saveMutation.isPending ? "Saving…" : "Save & test connection"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

const STEP_REVEAL_DELAY_MS = 550;

function TestConnectionModal({
  connectionId,
  open,
  onOpenChange,
}: {
  connectionId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [revealedCount, setRevealedCount] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const mutation = useMutation({
    mutationFn: () => api.testErpConnection(connectionId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["erp-connections"] }),
  });

  useEffect(() => {
    if (!open || !connectionId) return;
    setRevealedCount(0);
    mutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, connectionId]);

  const result: ConnectionTestResult | undefined = mutation.data;
  const steps = result?.steps ?? [];

  useEffect(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    if (!result || steps.length === 0) return;
    steps.forEach((_, i) => {
      const t = setTimeout(() => setRevealedCount((c) => Math.max(c, i + 1)), i * STEP_REVEAL_DELAY_MS);
      timers.current.push(t);
    });
    return () => timers.current.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  const allStepsRevealed = steps.length === 0 || revealedCount >= steps.length;
  const showFinalBanner = !mutation.isPending && !!result && allStepsRevealed;

  return (
    <Modal
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          timers.current.forEach(clearTimeout);
          mutation.reset();
        }
        onOpenChange(o);
      }}
      title="Testing connection"
    >
      <div className="space-y-3">
        {mutation.isPending && steps.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            Running connection test…
          </div>
        )}

        {steps.slice(0, revealedCount).map((step, i) => (
          <div key={i} className="flex items-start gap-2 text-sm">
            {step.success ? (
              <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-brand-100 text-brand-700">✓</span>
            ) : (
              <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-rose-100 text-rose-700">✕</span>
            )}
            <div>
              <div className="font-medium text-slate-900">{step.name}</div>
              {step.detail && <div className="mt-0.5 text-xs text-slate-500">{step.detail}</div>}
            </div>
          </div>
        ))}

        {!!result && revealedCount < steps.length && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-transparent" />
            Checking {steps[revealedCount]?.name.toLowerCase()}…
          </div>
        )}

        {showFinalBanner && (
          <div
            className={clsx(
              "mt-2 rounded-lg px-4 py-3 text-sm font-medium",
              result!.success ? "bg-brand-50 text-brand-700" : "bg-rose-50 text-rose-700",
            )}
          >
            {result!.success ? "✓ Passed — " : "Failed — "}
            {result!.message}
          </div>
        )}

        {mutation.isError && (
          <div className="rounded-lg bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
            {(mutation.error as Error).message}
          </div>
        )}
      </div>
    </Modal>
  );
}

export function ErpConnectors() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ErpConnection | null>(null);
  const [testingConnectionId, setTestingConnectionId] = useState<string | null>(null);
  const [testModalOpen, setTestModalOpen] = useState(false);

  const { data: connections, isLoading } = useQuery({
    queryKey: ["erp-connections"],
    queryFn: api.listErpConnections,
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteErpConnection,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["erp-connections"] }),
  });

  function openTestModal(connectionId: string) {
    setTestingConnectionId(connectionId);
    setTestModalOpen(true);
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">ERP Connectors</h1>
          <p className="mt-1 text-sm text-slate-500">
            Connect the ERP system Ledgerly should match invoices against.
          </p>
        </div>
        <button
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
        >
          Connect an ERP
        </button>
      </div>

      <Card className="mt-6 overflow-hidden !p-0">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading…</div>
        ) : connections && connections.length > 0 ? (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-3 font-medium">Name</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Last test</th>
                <th className="px-6 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {connections.map((c) => (
                <tr key={c.id} className="border-b border-surface-border last:border-0">
                  <td className="px-6 py-4 font-medium text-slate-900">{c.display_name}</td>
                  <td className="px-6 py-4 text-slate-600">{c.connector_type}</td>
                  <td className="px-6 py-4"><ConnectionStatusBadge status={c.status} /></td>
                  <td className="max-w-xs truncate px-6 py-4 text-slate-500" title={c.last_test_result ?? ""}>
                    {c.last_test_result ?? "—"}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button onClick={() => openTestModal(c.id)} className="mr-3 text-sm text-brand-600 hover:underline">
                      Test
                    </button>
                    <button
                      onClick={() => {
                        setEditing(c);
                        setFormOpen(true);
                      }}
                      className="mr-3 text-sm text-slate-600 hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(c.id)}
                      className="text-sm text-rose-600 hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6 text-sm text-slate-500">No ERP connected yet.</div>
        )}
      </Card>

      <ConnectorFormModal open={formOpen} onOpenChange={setFormOpen} editing={editing} onTestRequested={openTestModal} />
      <TestConnectionModal connectionId={testingConnectionId} open={testModalOpen} onOpenChange={setTestModalOpen} />
    </div>
  );
}
