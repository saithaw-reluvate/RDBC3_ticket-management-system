// Reads Django's csrftoken cookie for the X-CSRFToken header on unsafe admin
// requests. Browser-only — call sites in Server Components never need this.
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}
