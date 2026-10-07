import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { RequirePlatformAuth, RequireTenantAuth } from "./components/RequireAuth";
import { TenantProviderRoute } from "./context/TenantContext";
import { Approvals } from "./pages/Approvals";
import { AuditLog } from "./pages/AuditLog";
import { Dashboard } from "./pages/Dashboard";
import { Exceptions } from "./pages/Exceptions";
import { InvoiceDetail } from "./pages/InvoiceDetail";
import { Invoices } from "./pages/Invoices";
import { Landing } from "./pages/Landing";
import { TenantLogin } from "./pages/TenantLogin";
import { ErpConnectors } from "./pages/admin/ErpConnectors";
import { Branding } from "./pages/admin/Branding";
import { RolePermissions } from "./pages/admin/RolePermissions";
import { Users } from "./pages/admin/Users";
import { CreateTenant } from "./pages/platform/CreateTenant";
import { PlatformLayout } from "./pages/platform/PlatformLayout";
import { PlatformLogin } from "./pages/platform/PlatformLogin";
import { TenantDetail } from "./pages/platform/TenantDetail";
import { Tenants } from "./pages/platform/Tenants";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />

      <Route path="/platform/login" element={<PlatformLogin />} />
      <Route
        path="/platform"
        element={
          <RequirePlatformAuth>
            <PlatformLayout />
          </RequirePlatformAuth>
        }
      >
        <Route index element={<Navigate to="tenants" replace />} />
        <Route path="tenants" element={<Tenants />} />
        <Route path="tenants/new" element={<CreateTenant />} />
        <Route path="tenants/:tenantId" element={<TenantDetail />} />
      </Route>

      <Route path="/t/:tenantSlug" element={<TenantProviderRoute />}>
        <Route path="login" element={<TenantLogin />} />
        <Route
          element={
            <RequireTenantAuth>
              <Layout />
            </RequireTenantAuth>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="invoices" element={<Invoices />} />
          <Route path="invoices/:id" element={<InvoiceDetail />} />
          <Route path="exceptions" element={<Exceptions />} />
          <Route path="approvals" element={<Approvals />} />
          <Route path="audit-log" element={<AuditLog />} />
          <Route path="admin/erp-connectors" element={<ErpConnectors />} />
          <Route path="admin/role-permissions" element={<RolePermissions />} />
          <Route path="admin/users" element={<Users />} />
          <Route path="admin/branding" element={<Branding />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
