import { getCsrfToken } from "./csrf";
import type {
  AdminResponse,
  AdminUser,
  ApiErrorEnvelope,
  Category,
  ErrorCode,
  PaginatedList,
  Priority,
  Status,
  TicketAdminDetail,
  TicketAdminListItem,
  TicketCreateResponse,
  TicketCustomerDetail,
} from "./types";

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; code: ErrorCode; message: string; details: Record<string, unknown> };

interface FetchOptions extends RequestInit {
  /** Absolute origin override — Server Components must pass BACKEND_ORIGIN
   * directly; the Next.js rewrite only applies to real browser requests. */
  origin?: string;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<ApiResult<T>> {
  const { origin, ...init } = options;
  const url = origin ? `${origin}${path}` : path;

  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    return { ok: false, code: "server_error", message: "Could not reach the server.", details: {} };
  }

  if (response.status === 204) {
    return { ok: true, data: undefined as T };
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Not a JSON body (e.g. a file download, handled by callers via a plain URL).
  }

  if (!response.ok) {
    const envelope = body as Partial<ApiErrorEnvelope> | null;
    if (envelope?.error) {
      return {
        ok: false,
        code: envelope.error.code,
        message: envelope.error.message,
        details: envelope.error.details ?? {},
      };
    }
    return { ok: false, code: "server_error", message: "An unexpected error occurred.", details: {} };
  }

  return { ok: true, data: body as T };
}

function adminHeaders(extra?: HeadersInit): HeadersInit {
  const csrf = getCsrfToken();
  return { ...(csrf ? { "X-CSRFToken": csrf } : {}), ...extra };
}

// --- Error presentation — mapped centrally, per docs/FRONTEND.md §8. ---------
// Customer-facing screens must never show HTTP status codes or API error
// codes; this is the only place a code is translated into copy.

export interface ErrorPresentation {
  message: string;
  action?: "request-new-link" | "redirect-login" | "retry";
}

export const ERROR_PRESENTATION: Record<ErrorCode, ErrorPresentation> = {
  validation_error: { message: "Some fields need attention." },
  invalid_token: { message: "We couldn't find this report.", action: "request-new-link" },
  expired_token: { message: "This link has expired.", action: "request-new-link" },
  revoked_token: { message: "This link has been replaced.", action: "request-new-link" },
  permission_denied: { message: "Please sign in to continue.", action: "redirect-login" },
  not_found: { message: "We couldn't find that." },
  throttled: {
    message: "You've filed several reports recently. Please wait a while before trying again.",
    action: "retry",
  },
  server_error: { message: "Something went wrong on our end. Please try again." },
  error: { message: "Something went wrong. Please try again." },
};

// --- Public plane -----------------------------------------------------------

export function createTicket(formData: FormData): Promise<ApiResult<TicketCreateResponse>> {
  return apiFetch<TicketCreateResponse>("/api/tickets/", { method: "POST", body: formData });
}

export function resendLink(email: string): Promise<ApiResult<{ message: string }>> {
  return apiFetch<{ message: string }>("/api/tickets/resend-link/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

// --- Customer plane -----------------------------------------------------------

export function getTicketByToken(token: string, origin?: string): Promise<ApiResult<TicketCustomerDetail>> {
  return apiFetch<TicketCustomerDetail>(`/api/track/${encodeURIComponent(token)}/`, { origin });
}

export function attachmentDownloadUrl(token: string, attachmentId: number): string {
  return `/api/track/${encodeURIComponent(token)}/attachments/${attachmentId}/`;
}

// --- Admin plane -----------------------------------------------------------

export function adminLogin(username: string, password: string): Promise<ApiResult<AdminUser>> {
  return apiFetch<AdminUser>("/api/admin/auth/login/", {
    method: "POST",
    headers: adminHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ username, password }),
  });
}

export function adminLogout(): Promise<ApiResult<void>> {
  return apiFetch<void>("/api/admin/auth/logout/", { method: "POST", headers: adminHeaders() });
}

export function adminMe(): Promise<ApiResult<AdminUser>> {
  return apiFetch<AdminUser>("/api/admin/auth/me/");
}

export interface AdminListParams {
  status?: string;
  priority?: string;
  category?: string;
  search?: string;
  ordering?: string;
  page?: number;
}

export function adminListTickets(
  params: AdminListParams = {}
): Promise<ApiResult<PaginatedList<TicketAdminListItem>>> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.priority) qs.set("priority", params.priority);
  if (params.category) qs.set("category", params.category);
  if (params.search) qs.set("search", params.search);
  if (params.ordering) qs.set("ordering", params.ordering);
  if (params.page) qs.set("page", String(params.page));
  const query = qs.toString();
  return apiFetch<PaginatedList<TicketAdminListItem>>(`/api/admin/tickets/${query ? `?${query}` : ""}`);
}

export function adminGetTicket(reference: string): Promise<ApiResult<TicketAdminDetail>> {
  return apiFetch<TicketAdminDetail>(`/api/admin/tickets/${encodeURIComponent(reference)}/`);
}

export interface TicketPatch {
  status?: Status;
  priority?: Priority;
  category?: Category;
}

export function adminPatchTicket(reference: string, patch: TicketPatch): Promise<ApiResult<TicketAdminDetail>> {
  return apiFetch<TicketAdminDetail>(`/api/admin/tickets/${encodeURIComponent(reference)}/`, {
    method: "PATCH",
    headers: adminHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(patch),
  });
}

export function adminAddResponse(
  reference: string,
  message: string,
  isInternal: boolean
): Promise<ApiResult<AdminResponse>> {
  return apiFetch<AdminResponse>(`/api/admin/tickets/${encodeURIComponent(reference)}/responses/`, {
    method: "POST",
    headers: adminHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ message, is_internal: isInternal }),
  });
}

export function adminResendLink(reference: string): Promise<ApiResult<{ message: string }>> {
  return apiFetch<{ message: string }>(`/api/admin/tickets/${encodeURIComponent(reference)}/resend-link/`, {
    method: "POST",
    headers: adminHeaders(),
  });
}

export function adminRevokeLinks(reference: string): Promise<ApiResult<{ revoked: number }>> {
  return apiFetch<{ revoked: number }>(`/api/admin/tickets/${encodeURIComponent(reference)}/revoke-links/`, {
    method: "POST",
    headers: adminHeaders(),
  });
}

export function adminAttachmentDownloadUrl(reference: string, attachmentId: number): string {
  return `/api/admin/tickets/${encodeURIComponent(reference)}/attachments/${attachmentId}/`;
}
