import { getStoredWorkspaceId, workspaceHeaders } from "@/lib/workspaceStore";

const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

function withWorkspace(init?: RequestInit): RequestInit {
  const h = new Headers(init?.headers);
  const ws = workspaceHeaders() as Record<string, string>;
  for (const [k, v] of Object.entries(ws)) {
    h.set(k, v);
  }
  return { ...init, headers: h };
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      const j = JSON.parse(text) as { detail?: unknown };
      if (typeof j.detail === "string") detail = j.detail;
      else if (Array.isArray(j.detail)) detail = JSON.stringify(j.detail);
    } catch {
      /* use raw */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export type ValidationIssue = {
  code: string;
  message: string;
  severity: "info" | "warning" | "error";
};

export type InvoiceValidation = {
  is_valid: boolean;
  issues: ValidationIssue[];
  fraud_flags: string[];
};

export type InvoiceLineItem = {
  description: string | null;
  quantity: number | null;
  unit_price: number | null;
  amount: number | null;
  taxable_value?: number | null;
  gst_rate_pct?: number | null;
  cgst_amount?: number | null;
  sgst_amount?: number | null;
  igst_amount?: number | null;
  cess_amount?: number | null;
};

export type InvoiceStatus = "processing" | "completed" | "failed";

export type InvoiceRecord = {
  id: string;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  vendor_name: string | null;
  total_amount: number | null;
  tax_amount: number | null;
  currency: string | null;
  line_items: InvoiceLineItem[];
  category: string | null;
  category_confidence: number | null;
  validation: InvoiceValidation;
  created_at: string;
  mime_type: string | null;
  status: InvoiceStatus;
  original_filename: string | null;
  processing_error: string | null;
};

export type InvoiceCreateResult = {
  invoice: InvoiceRecord;
  extraction_backend: string | null;
  raw_text_length: number | null;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatRequestBody = {
  message: string;
  invoice_ids?: string[] | null;
  history?: ChatMessage[];
};

export type ChatSourceCitation = {
  invoice_id: string;
  vendor_name: string | null;
  invoice_number: string | null;
  total_amount: number | null;
  category: string | null;
  text_excerpt: string;
  via: "semantic_search" | "knowledge_graph";
};

export type ChatResponse = {
  answer: string;
  source_invoice_ids: string[];
  source_citations?: ChatSourceCitation[];
  suggested_follow_ups: string[];
};

export type CategorySpend = {
  category: string;
  total_amount: number;
  invoice_count: number;
};

export type VendorTop = {
  vendor_name: string;
  total_amount: number;
  invoice_count: number;
};

export type MonthlySpend = {
  month: string;
  total_amount: number;
  invoice_count: number;
};

export type AnalyticsDashboard = {
  invoice_count: number;
  total_spend: number;
  total_tax: number;
  overdue_count: number;
  due_within_7d_count: number;
  by_category: CategorySpend[];
  top_vendors: VendorTop[];
  monthly: MonthlySpend[];
};

export type WorkspaceRecord = {
  id: string;
  name: string;
  created_at: string;
};

export type NotificationRecord = {
  id: string;
  kind: "due_soon" | "overdue";
  invoice_id: string;
  vendor_name: string | null;
  due_date: string | null;
  message: string;
  created_at: string;
  read: boolean;
};

export async function fetchWorkspaces(): Promise<WorkspaceRecord[]> {
  const res = await fetch(`${base}/api/v1/workspaces`);
  return parseJson<WorkspaceRecord[]>(res);
}

export async function createWorkspace(name: string): Promise<WorkspaceRecord> {
  const res = await fetch(`${base}/api/v1/workspaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name.trim() }),
  });
  return parseJson<WorkspaceRecord>(res);
}

export async function fetchInvoices(limit = 50): Promise<InvoiceRecord[]> {
  const safe = Math.min(Math.max(limit, 1), 200);
  const res = await fetch(`${base}/api/v1/invoices?limit=${safe}`, withWorkspace());
  return parseJson<InvoiceRecord[]>(res);
}

export async function fetchInvoice(id: string): Promise<InvoiceRecord> {
  const res = await fetch(`${base}/api/v1/invoices/${encodeURIComponent(id)}`, withWorkspace());
  return parseJson<InvoiceRecord>(res);
}

export async function uploadInvoice(file: File): Promise<InvoiceCreateResult> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${base}/api/v1/invoices/upload`, withWorkspace({ method: "POST", body: fd }));
  return parseJson<InvoiceCreateResult>(res);
}

export async function chatInvoices(body: ChatRequestBody): Promise<ChatResponse> {
  const res = await fetch(
    `${base}/api/v1/chat/invoices`,
    withWorkspace({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: body.message,
        invoice_ids: body.invoice_ids ?? null,
        history: body.history ?? [],
      }),
    }),
  );
  return parseJson<ChatResponse>(res);
}

export function invoicesExportUrl(format: "json" | "csv" | "xlsx", limit = 2000): string {
  const safe = Math.min(Math.max(limit, 1), 5000);
  const ws = getStoredWorkspaceId();
  const q = new URLSearchParams({ format, limit: String(safe) });
  if (ws?.trim()) q.set("workspace_id", ws.trim());
  return `${base}/api/v1/invoices/export?${q.toString()}`;
}

export async function fetchAnalyticsDashboard(topVendors = 8): Promise<AnalyticsDashboard> {
  const res = await fetch(`${base}/api/v1/analytics/dashboard?top_vendors=${topVendors}`, withWorkspace());
  return parseJson<AnalyticsDashboard>(res);
}

export async function fetchNotifications(limit = 100): Promise<NotificationRecord[]> {
  const res = await fetch(`${base}/api/v1/notifications?limit=${limit}`, withWorkspace());
  return parseJson<NotificationRecord[]>(res);
}

export async function markNotificationRead(id: string): Promise<NotificationRecord> {
  const res = await fetch(
    `${base}/api/v1/notifications/${encodeURIComponent(id)}/read`,
    withWorkspace({ method: "PATCH" }),
  );
  return parseJson<NotificationRecord>(res);
}
