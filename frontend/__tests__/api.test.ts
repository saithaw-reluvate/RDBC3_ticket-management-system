import { adminLogout, createTicket, ERROR_PRESENTATION, resendLink } from "@/lib/api";
import type { ErrorCode } from "@/lib/types";

const ALL_CODES: ErrorCode[] = [
  "validation_error",
  "invalid_token",
  "expired_token",
  "revoked_token",
  "permission_denied",
  "not_found",
  "throttled",
  "server_error",
  "error",
];

function mockJsonResponse(status: number, body: unknown): Response {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  } as Response;
}

describe("ERROR_PRESENTATION", () => {
  it("has an entry for every error code", () => {
    for (const code of ALL_CODES) {
      expect(ERROR_PRESENTATION[code]).toBeDefined();
      expect(ERROR_PRESENTATION[code].message.length).toBeGreaterThan(0);
    }
  });

  it("never leaks the raw error code into the customer-facing message", () => {
    for (const code of ALL_CODES) {
      expect(ERROR_PRESENTATION[code].message.toLowerCase()).not.toContain(code);
    }
  });

  it("never mentions an HTTP status code in the message", () => {
    const httpStatuses = ["400", "403", "404", "410", "429", "500"];
    for (const code of ALL_CODES) {
      for (const status of httpStatuses) {
        expect(ERROR_PRESENTATION[code].message).not.toContain(status);
      }
    }
  });

  it("maps token failures to the request-new-link action", () => {
    expect(ERROR_PRESENTATION.invalid_token.action).toBe("request-new-link");
    expect(ERROR_PRESENTATION.expired_token.action).toBe("request-new-link");
    expect(ERROR_PRESENTATION.revoked_token.action).toBe("request-new-link");
  });

  it("maps permission_denied to redirect-login", () => {
    expect(ERROR_PRESENTATION.permission_denied.action).toBe("redirect-login");
  });
});

describe("apiFetch error envelope parsing (via createTicket)", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("returns ok:true with the parsed body on success", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      mockJsonResponse(201, {
        reference: "TKT-ABCD1234",
        subject: "s",
        category: "BUG",
        status: "OPEN",
        priority: "MEDIUM",
        created_at: "2026-01-01T00:00:00Z",
      })
    );
    const result = await createTicket(new FormData());
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.reference).toBe("TKT-ABCD1234");
    }
  });

  it("returns the parsed code/message/details on a validation_error", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      mockJsonResponse(400, {
        error: { code: "validation_error", message: "Validation failed.", details: { email: ["Required."] } },
      })
    );
    const result = await createTicket(new FormData());
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.code).toBe("validation_error");
      expect(result.details).toEqual({ email: ["Required."] });
    }
  });

  it("falls back to server_error when the response has no envelope", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 502,
      ok: false,
      json: async () => {
        throw new Error("not json");
      },
    } as unknown as Response);
    const result = await resendLink("a@example.com");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("server_error");
  });

  it("falls back to server_error when fetch itself throws (network failure)", async () => {
    global.fetch = jest.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const result = await resendLink("a@example.com");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.code).toBe("server_error");
  });

  it("treats a 204 No Content as success", async () => {
    global.fetch = jest.fn().mockResolvedValue({ status: 204, ok: true } as Response);
    const result = await adminLogout();
    expect(result.ok).toBe(true);
  });
});
