import type { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";
import { hasRole, keycloak } from "../auth/keycloak";
import { useTenant } from "../context/TenantContext";

export function RequireTenantAuth({ children }: PropsWithChildren) {
  const { slug } = useTenant();
  if (!keycloak.authenticated) {
    return <Navigate to={`/t/${slug}/login`} replace />;
  }
  // platform_admin has no tenant_id and manages tenants exclusively via
  // /platform/* — it must never land inside a tenant's own workspace, where
  // every tenant-scoped query would silently run with a null tenant_id.
  if (hasRole("platform_admin")) {
    return <Navigate to="/platform" replace />;
  }
  return <>{children}</>;
}

export function RequirePlatformAuth({ children }: PropsWithChildren) {
  if (!keycloak.authenticated || !hasRole("platform_admin")) {
    return <Navigate to="/platform/login" replace />;
  }
  return <>{children}</>;
}
