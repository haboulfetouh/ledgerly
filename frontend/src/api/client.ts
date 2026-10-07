import { keycloak } from "../auth/keycloak";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (keycloak.isTokenExpired(10)) {
    await keycloak.updateToken(10);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      Authorization: `Bearer ${keycloak.token}`,
      ...init.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/** For pre-login endpoints only (tenant branding) — no auth header, no
 * token-refresh logic, since there may be no session at all yet.
 */
async function publicRequest<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export interface TenantPublic {
  name: string;
  slug: string;
  primary_color: string;
  has_logo: boolean;
}

export interface TenantMe extends TenantPublic {
  id: string;
  plan: string;
}

export interface PlatformTenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
  created_at: string;
}

export interface TenantStats {
  invoices_total: number;
  invoices_processed: number;
  invoices_needs_review: number;
  invoices_exception: number;
  invoices_posted: number;
  user_count: number;
  erp_connected: boolean;
}

export interface PlatformTenantDetail extends PlatformTenant {
  admin_email: string | null;
  stats: TenantStats;
}

export interface Me {
  subject: string;
  tenant_id: string;
  roles: string[];
  email: string | null;
  modules: string[];
}

export interface InvoiceListItem {
  id: string;
  vendor_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  currency: string | null;
  total_amount: number | null;
  status: string;
  created_at: string;
}

export interface AiOutput {
  id: string;
  stage: string;
  model_name: string;
  confidence_overall: number | null;
  field_confidences: Record<string, number> | null;
  created_at: string;
}

export interface InvoiceLineItem {
  id: string;
  description: string | null;
  quantity: number | null;
  unit_price: number | null;
  line_total: number | null;
}

export interface MatchRecord {
  id: string;
  status: string;
  discrepancy_detail: string | null;
  explanation: string | null;
  resolved_by: string | null;
  resolution_action: string | null;
  resolution_reason: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface ApprovalRecord {
  id: string;
  approver_subject: string;
  decision: string;
  comment: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface InvoiceDetail extends InvoiceListItem {
  due_date: string | null;
  subtotal: number | null;
  tax_amount: number | null;
  po_number: string | null;
  source_filename: string;
  needs_review_reason: string | null;
  processing_error: string | null;
  line_items: InvoiceLineItem[];
  ai_outputs: AiOutput[];
  match_records: MatchRecord[];
  approval_records: ApprovalRecord[];
}

export interface InvoiceFieldsUpdate {
  vendor_name?: string | null;
  invoice_number?: string | null;
  invoice_date?: string | null;
  due_date?: string | null;
  currency?: string | null;
  subtotal?: number | null;
  tax_amount?: number | null;
  total_amount?: number | null;
  po_number?: string | null;
}

export interface ConfigField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  help_text: string | null;
}

export interface ConnectorType {
  connector_type: string;
  display_name: string;
  implemented: boolean;
  config_schema: ConfigField[];
}

export interface ErpConnection {
  id: string;
  connector_type: string;
  display_name: string;
  status: string;
  last_tested_at: string | null;
  last_test_result: string | null;
  created_at: string;
}

export interface ConnectionTestStep {
  name: string;
  success: boolean;
  detail: string | null;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  steps: ConnectionTestStep[];
}

export interface AuditLogEvent {
  id: string;
  actor_subject: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  created_at: string;
}

export interface DashboardMetrics {
  invoices_processed: number;
  needs_review: number;
  touchless_rate: number | null;
  avg_cost_per_invoice: number | null;
  exception_count: number;
  exception_aging_days_avg: number | null;
  pending_approval_count: number;
}

export interface RolePermissions {
  modules: string[];
  matrix: Record<string, string[]>;
}

export interface TenantUser {
  id: string;
  email: string | null;
  full_name: string;
  enabled: boolean;
  roles: string[];
}

export const api = {
  me: () => request<Me>("/auth/me"),
  getRolePermissions: () => request<RolePermissions>("/admin/role-permissions"),
  updateRolePermissions: (matrix: Record<string, string[]>) =>
    request<RolePermissions>("/admin/role-permissions", { method: "PUT", body: JSON.stringify({ matrix }) }),
  listUsers: () => request<TenantUser[]>("/admin/users"),
  inviteUser: (payload: { email: string; password: string; role: string; full_name?: string }) =>
    request<TenantUser>("/admin/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (id: string, payload: { role?: string; enabled?: boolean }) =>
    request<TenantUser>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteUser: (id: string) => request<void>(`/admin/users/${id}`, { method: "DELETE" }),
  updateBranding: (primaryColor: string, logo?: File) => {
    const formData = new FormData();
    formData.append("primary_color", primaryColor);
    if (logo) formData.append("logo", logo);
    return request<TenantMe>("/admin/branding", { method: "PUT", body: formData });
  },
  getPublicTenant: (slug: string) => publicRequest<TenantPublic>(`/public/tenants/${slug}`),
  getTenantMe: () => request<TenantMe>("/tenants/me"),
  listInvoices: (statuses?: string[]) => {
    const qs = statuses?.length ? `?${statuses.map((s) => `status=${s}`).join("&")}` : "";
    return request<InvoiceListItem[]>(`/invoices${qs}`);
  },
  getInvoice: (id: string) => request<InvoiceDetail>(`/invoices/${id}`),
  getDocumentUrl: (id: string) => request<{ url: string; filename: string }>(`/invoices/${id}/document-url`),
  uploadInvoice: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<{ id: string; status: string }>("/invoices", {
      method: "POST",
      body: formData,
    });
  },
  updateInvoiceFields: (id: string, payload: InvoiceFieldsUpdate) =>
    request<InvoiceDetail>(`/invoices/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  runMatching: (id: string) =>
    request<{ id: string; status: string }>(`/invoices/${id}/run-matching`, { method: "POST" }),
  resolveException: (id: string, action: "accept" | "override" | "escalate", reason?: string) =>
    request<InvoiceDetail>(`/invoices/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ action, reason }),
    }),
  approveInvoice: (id: string, comment?: string) =>
    request<InvoiceDetail>(`/invoices/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  rejectInvoice: (id: string, comment?: string) =>
    request<InvoiceDetail>(`/invoices/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  listConnectorTypes: () => request<ConnectorType[]>("/admin/erp-connectors/types"),
  listErpConnections: () => request<ErpConnection[]>("/admin/erp-connectors"),
  createErpConnection: (payload: { connector_type: string; display_name: string; config: Record<string, string> }) =>
    request<ErpConnection>("/admin/erp-connectors", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteErpConnection: (id: string) =>
    request<void>(`/admin/erp-connectors/${id}`, { method: "DELETE" }),
  getErpConnectionConfig: (id: string) =>
    request<{ config: Record<string, string> }>(`/admin/erp-connectors/${id}/config`),
  updateErpConnection: (id: string, payload: { display_name?: string; config?: Record<string, string> }) =>
    request<ErpConnection>(`/admin/erp-connectors/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  testErpConnection: (id: string) =>
    request<ConnectionTestResult>(`/admin/erp-connectors/${id}/test`, {
      method: "POST",
    }),
  listAuditLog: () => request<AuditLogEvent[]>("/audit-log"),
  downloadAuditLogCsv: async () => {
    if (keycloak.isTokenExpired(10)) {
      await keycloak.updateToken(10);
    }
    const response = await fetch(`${BASE_URL}/audit-log/export`, {
      headers: { Authorization: `Bearer ${keycloak.token}` },
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ledgerly-audit-log.csv";
    link.click();
    URL.revokeObjectURL(url);
  },
  getDashboardMetrics: () => request<DashboardMetrics>("/dashboard/metrics"),
  listPlatformTenants: () => request<PlatformTenant[]>("/platform/tenants"),
  createPlatformTenant: (payload: { name: string; slug: string; admin_email: string; admin_password: string }) =>
    request<PlatformTenant>("/platform/tenants", { method: "POST", body: JSON.stringify(payload) }),
  getPlatformTenant: (id: string) => request<PlatformTenantDetail>(`/platform/tenants/${id}`),
  updatePlatformTenantPlan: (id: string, plan: string) =>
    request<PlatformTenant>(`/platform/tenants/${id}`, { method: "PATCH", body: JSON.stringify({ plan }) }),
  resetTenantAdminPassword: (id: string, password: string) =>
    request<void>(`/platform/tenants/${id}/reset-admin-password`, { method: "POST", body: JSON.stringify({ password }) }),
};
