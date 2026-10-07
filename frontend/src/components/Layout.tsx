import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";
import { hasRole, keycloak, logout } from "../auth/keycloak";
import { useTenant, useTenantPath } from "../context/TenantContext";

export function Layout() {
  const { branding, logoUrl, slug } = useTenant();
  const tenantPath = useTenantPath();
  const initials = (keycloak.tokenParsed?.email as string | undefined)
    ?.slice(0, 2)
    .toUpperCase();

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: api.me });
  const modules = me?.modules ?? [];
  const has = (module: string) => modules.includes(module);
  const isAdmin = hasRole("admin");

  const navItems = [
    { to: tenantPath(""), label: "Dashboard", end: true },
    ...(has("invoices") ? [{ to: tenantPath("invoices"), label: "Invoices" }] : []),
    ...(has("exceptions") ? [{ to: tenantPath("exceptions"), label: "Exceptions" }] : []),
    ...(has("approvals") ? [{ to: tenantPath("approvals"), label: "Approvals" }] : []),
    ...(has("audit_log") ? [{ to: tenantPath("audit-log"), label: "Audit Log" }] : []),
    ...(has("erp_connectors") ? [{ to: tenantPath("admin/erp-connectors"), label: "ERP Connectors" }] : []),
    ...(has("users") ? [{ to: tenantPath("admin/users"), label: "Users" }] : []),
    ...(isAdmin ? [{ to: tenantPath("admin/role-permissions"), label: "Role Permissions" }] : []),
    ...(has("branding") ? [{ to: tenantPath("admin/branding"), label: "Branding" }] : []),
  ];

  const accountConsoleUrl = `${import.meta.env.VITE_KEYCLOAK_URL}/realms/${import.meta.env.VITE_KEYCLOAK_REALM}/account`;

  return (
    <div className="flex h-full">
      <aside className="flex w-64 flex-col justify-between border-r border-surface-border bg-surface-raised p-6">
        <div>
          <div className="mb-10 flex items-center gap-2">
            <img src={logoUrl ?? "/logo-icon.png"} alt={branding.name} className="h-9 w-9 object-contain" />
            <div>
              <div className="text-base font-bold tracking-tight text-slate-900">{branding.name}</div>
              <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                Invoice-to-Pay, Automated
              </div>
            </div>
          </div>
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  clsx(
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-500 hover:bg-surface-sunken hover:text-slate-900",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="flex flex-col gap-2">
          <a
            href={accountConsoleUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 rounded-lg border border-surface-border px-3 py-2 text-left text-sm text-slate-600 hover:bg-surface-sunken"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-[11px] font-semibold text-brand-700">
              {initials ?? "?"}
            </span>
            My profile
          </a>
          <button
            onClick={() => logout(`/t/${slug}/login`)}
            className="rounded-lg border border-surface-border px-3 py-2 text-left text-sm text-slate-600 hover:bg-surface-sunken"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-surface px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}
