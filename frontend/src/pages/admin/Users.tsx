import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { hasRole } from "../../auth/keycloak";
import { Card } from "../../components/Card";
import { Modal } from "../../components/Modal";

const ROLE_LABELS: Record<string, string> = {
  bookkeeper: "Bookkeeper",
  accountant_manager: "Accountant Manager",
  admin: "Admin",
  auditor: "Auditor",
};

function InviteUserModal({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("bookkeeper");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: api.inviteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
      setEmail("");
      setFullName("");
      setPassword("");
      setRole("bookkeeper");
      onOpenChange(false);
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Invite a user">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          mutation.mutate({ email, password, role, full_name: fullName });
        }}
        className="space-y-4"
      >
        <div>
          <label className="mb-1 block text-sm text-slate-600">Full name</label>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-600">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-600">Temporary password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-600">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-900"
          >
            {Object.entries(ROLE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
        >
          {mutation.isPending ? "Inviting…" : "Invite"}
        </button>
      </form>
    </Modal>
  );
}

export function Users() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const { data: users, isLoading } = useQuery({ queryKey: ["tenant-users"], queryFn: api.listUsers });
  const isAdmin = hasRole("admin");

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { role?: string; enabled?: boolean } }) =>
      api.updateUser(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tenant-users"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tenant-users"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Users</h1>
          <p className="mt-1 text-sm text-slate-500">Manage who has access to this workspace.</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setModalOpen(true)}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
          >
            Invite user
          </button>
        )}
      </div>

      <Card className="mt-6 overflow-hidden !p-0">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading…</div>
        ) : users && users.length > 0 ? (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-3 font-medium">Name</th>
                <th className="px-6 py-3 font-medium">Email</th>
                <th className="px-6 py-3 font-medium">Role</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-surface-border last:border-0">
                  <td className="px-6 py-4 font-medium text-slate-900">{u.full_name || "—"}</td>
                  <td className="px-6 py-4 text-slate-600">{u.email}</td>
                  <td className="px-6 py-4">
                    {isAdmin ? (
                      <select
                        value={u.roles[0] ?? ""}
                        onChange={(e) => updateMutation.mutate({ id: u.id, payload: { role: e.target.value } })}
                        className="rounded-md border border-surface-border bg-surface px-2 py-1 text-sm text-slate-900"
                      >
                        {Object.entries(ROLE_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      ROLE_LABELS[u.roles[0] ?? ""] ?? u.roles[0] ?? "—"
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {isAdmin ? (
                      <button
                        onClick={() => updateMutation.mutate({ id: u.id, payload: { enabled: !u.enabled } })}
                        className={u.enabled ? "text-brand-600" : "text-slate-400"}
                      >
                        {u.enabled ? "Active" : "Disabled"}
                      </button>
                    ) : (
                      <span className={u.enabled ? "text-brand-600" : "text-slate-400"}>
                        {u.enabled ? "Active" : "Disabled"}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {isAdmin && (
                      <button
                        onClick={() => deleteMutation.mutate(u.id)}
                        className="text-sm text-rose-600 hover:underline"
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6 text-sm text-slate-500">No users yet.</div>
        )}
      </Card>

      <InviteUserModal open={modalOpen} onOpenChange={setModalOpen} />
    </div>
  );
}
