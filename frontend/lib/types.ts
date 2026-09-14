// Shapes match the shipped Step 2 API exactly — docs/BACKEND.md / FRONTEND.md §10.

export const CATEGORIES = [
  { value: "ACCOUNT_ACCESS", label: "Login & account access" },
  { value: "BILLING", label: "Billing & payments" },
  { value: "BUG", label: "Something is broken" },
  { value: "PERFORMANCE", label: "Slow or unavailable" },
  { value: "DATA", label: "Incorrect or missing data" },
  { value: "SECURITY", label: "Security concern" },
  { value: "OTHER", label: "Something else" },
] as const;

export type Category = (typeof CATEGORIES)[number]["value"];

export const STATUSES = ["OPEN", "IN_PROGRESS", "RESOLVED"] as const;
export type Status = (typeof STATUSES)[number];

export const PRIORITIES = ["LOW", "MEDIUM", "HIGH"] as const;
export type Priority = (typeof PRIORITIES)[number];

export interface TicketCreateResponse {
  reference: string;
  subject: string;
  category: Category;
  status: Status;
  priority: Priority;
  created_at: string;
}

export interface CustomerResponse {
  message: string;
  created_at: string;
}

export type CustomerEventType = "CREATED" | "STATUS_CHANGED" | "RESPONSE_ADDED";

export interface CustomerEvent {
  event_type: CustomerEventType;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export interface AttachmentSummary {
  id: number;
  original_filename: string;
  size_bytes: number;
  content_type: string;
}

export interface TicketCustomerDetail {
  reference: string;
  subject: string;
  description: string;
  reporter_name: string;
  category: Category;
  category_display: string;
  status: Status;
  priority: Priority;
  created_at: string;
  resolved_at: string | null;
  responses: CustomerResponse[];
  events: CustomerEvent[];
  attachments: AttachmentSummary[];
}

export interface AdminUser {
  username: string;
  is_staff: boolean;
}

export interface TicketAdminListItem {
  reference: string;
  subject: string;
  category: Category;
  status: Status;
  priority: Priority;
  client_email: string;
  reporter_name: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedList<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AdminResponse {
  id: number;
  author: string | null;
  message: string;
  is_internal: boolean;
  created_at: string;
}

export type AdminEventType =
  | CustomerEventType
  | "PRIORITY_CHANGED"
  | "CATEGORY_CHANGED"
  | "ATTACHMENT_ADDED"
  | "TOKEN_ISSUED"
  | "TOKEN_REVOKED"
  | "EMAIL_SENT"
  | "EMAIL_FAILED";

export interface AdminEvent {
  id: number;
  event_type: AdminEventType;
  actor: string | null;
  actor_type: "system" | "customer" | "admin";
  old_value: string | null;
  new_value: string | null;
  note: string | null;
  created_at: string;
}

export interface TicketAdminDetail {
  reference: string;
  subject: string;
  description: string;
  reporter_name: string;
  client_email: string;
  category: Category;
  category_display: string;
  status: Status;
  priority: Priority;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  responses: AdminResponse[];
  events: AdminEvent[];
  attachments: AttachmentSummary[];
}

export type ErrorCode =
  | "validation_error"
  | "invalid_token"
  | "expired_token"
  | "revoked_token"
  | "permission_denied"
  | "not_found"
  | "throttled"
  | "server_error"
  | "error";

export interface ApiErrorEnvelope {
  error: {
    code: ErrorCode;
    message: string;
    details: Record<string, unknown>;
  };
}
