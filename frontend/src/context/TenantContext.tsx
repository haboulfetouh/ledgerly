import { createContext, useContext, useEffect, useState } from "react";
import { Outlet, useParams } from "react-router-dom";
import { api, type TenantPublic } from "../api/client";
import { keycloak } from "../auth/keycloak";

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

interface TenantContextValue {
  slug: string;
  branding: TenantPublic;
  logoUrl: string | null;
}

const TenantContext = createContext<TenantContextValue | null>(null);

export function useTenant(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error("useTenant() must be used within a tenant route");
  return ctx;
}

/** Prefixes a path with the current tenant's slug, e.g. useTenantPath()("invoices") -> "/t/acme/invoices" */
export function useTenantPath() {
  const { slug } = useTenant();
  return (path: string) => `/t/${slug}/${path}`.replace(/\/+$/, "").replace("//", "/");
}

function NotFoundWorkspace({ slug }: { slug: string }) {
  return (
    <div className="flex h-screen items-center justify-center bg-surface px-4 text-center">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">No workspace called "{slug}"</h1>
        <p className="mt-2 text-sm text-slate-500">Check the URL your admin sent you, or contact them for a new invite.</p>
      </div>
    </div>
  );
}

/** Layout route for everything under /t/:tenantSlug — resolves branding
 * for the pre-login page and provides it (plus the slug) to every child
 * route via context, instead of threading it through props.
 */
export function TenantProviderRoute() {
  const { tenantSlug } = useParams<{ tenantSlug: string }>();
  const [branding, setBranding] = useState<TenantPublic | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!tenantSlug) return;
    setBranding(null);
    setNotFound(false);
    api
      .getPublicTenant(tenantSlug)
      .then(setBranding)
      .catch(() => setNotFound(true));
  }, [tenantSlug]);

  // If we're authenticated but the token belongs to a different tenant
  // than this URL, the user followed the wrong workspace link — send them
  // to the one their account actually belongs to.
  useEffect(() => {
    if (!keycloak.authenticated || !tenantSlug) return;
    api.getTenantMe().then((me) => {
      if (me.slug !== tenantSlug) {
        window.location.href = window.location.pathname.replace(`/t/${tenantSlug}`, `/t/${me.slug}`);
      }
    });
  }, [tenantSlug]);

  if (notFound) return <NotFoundWorkspace slug={tenantSlug ?? ""} />;
  if (!branding) return <div className="flex h-screen items-center justify-center text-sm text-slate-400">Loading…</div>;

  const logoUrl = branding.has_logo ? `${BASE_URL}/public/tenants/${branding.slug}/logo` : null;

  return (
    <TenantContext.Provider value={{ slug: branding.slug, branding, logoUrl }}>
      <Outlet />
    </TenantContext.Provider>
  );
}
