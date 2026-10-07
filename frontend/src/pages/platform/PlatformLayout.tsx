import { NavLink, Outlet } from "react-router-dom";
import clsx from "clsx";
import { logout } from "../../auth/keycloak";

export function PlatformLayout() {
  return (
    <div className="flex h-full">
      <aside className="flex w-64 flex-col justify-between border-r border-surface-border bg-surface-raised p-6">
        <div>
          <div className="mb-10 flex items-center gap-2">
            <img src="/logo-icon.png" alt="Ledgerly" className="h-9 w-9 object-contain" />
            <div>
              <div className="text-base font-bold tracking-tight text-slate-900">Ledgerly</div>
              <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">Platform</div>
            </div>
          </div>
          <nav className="flex flex-col gap-1">
            <NavLink
              to="/platform/tenants"
              className={({ isActive }) =>
                clsx(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-500 hover:bg-surface-sunken hover:text-slate-900",
                )
              }
            >
              Tenants
            </NavLink>
          </nav>
        </div>
        <button
          onClick={() => logout("/platform/login")}
          className="rounded-lg border border-surface-border px-3 py-2 text-left text-sm text-slate-600 hover:bg-surface-sunken"
        >
          Sign out
        </button>
      </aside>
      <main className="flex-1 overflow-y-auto bg-surface px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}
