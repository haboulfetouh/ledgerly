import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { Card } from "../../components/Card";
import { useTenant } from "../../context/TenantContext";

export function Branding() {
  const { branding, logoUrl } = useTenant();
  const [color, setColor] = useState(branding.primary_color);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.updateBranding(color, logoFile ?? undefined),
    onSuccess: () => {
      // TenantContext resolves branding once on mount — reload picks up the change everywhere (sidebar, login page).
      window.location.reload();
    },
  });

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-semibold text-slate-900">Branding</h1>
      <p className="mt-1 text-sm text-slate-500">Whitelabel this workspace's logo and accent color.</p>

      <Card className="mt-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
          className="space-y-5"
        >
          <div>
            <label className="mb-2 block text-sm text-slate-600">Logo</label>
            <div className="flex items-center gap-4">
              <img
                src={preview ?? logoUrl ?? "/logo-icon.png"}
                alt="Current logo"
                className="h-14 w-14 rounded-lg border border-surface-border object-contain p-1"
              />
              <input
                type="file"
                accept="image/png,image/jpeg,image/svg+xml"
                onChange={(e) => {
                  const file = e.target.files?.[0] ?? null;
                  setLogoFile(file);
                  setPreview(file ? URL.createObjectURL(file) : null);
                }}
                className="text-sm text-slate-600"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm text-slate-600">Primary color</label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="h-10 w-14 cursor-pointer rounded border border-surface-border bg-transparent"
              />
              <span className="text-sm text-slate-500">{color}</span>
            </div>
            <p className="mt-1 text-xs text-slate-400">Used on this workspace's login page button.</p>
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
          >
            {mutation.isPending ? "Saving…" : "Save branding"}
          </button>
        </form>
      </Card>
    </div>
  );
}
