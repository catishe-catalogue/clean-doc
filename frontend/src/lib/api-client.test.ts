import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient, ApiClientError } from "./api-client";

describe("apiClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches json successfully on 200 OK", async () => {
    const mockData = { status: "ok" };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    });

    const result = await apiClient<{ status: string }>("/api/v1/health");
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/health",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      })
    );
  });

  it("does not set Content-Type application/json when body is FormData", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "job_123" }),
    });

    const formData = new FormData();
    formData.append("file", "fake_pdf_data");

    await apiClient("/api/v1/convert/upload", {
      method: "POST",
      body: formData,
    });

    const lastCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = lastCall[1]?.headers;
    expect(headers?.["Content-Type"]).toBeUndefined();
  });

  it("throws ApiClientError with server error and code on failure", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        error: "Неверный формат документа",
        code: "INVALID_PDF",
      }),
    });

    await expect(apiClient("/api/v1/convert/upload")).rejects.toThrow(ApiClientError);
    await expect(apiClient("/api/v1/convert/upload")).rejects.toMatchObject({
      status: 400,
      code: "INVALID_PDF",
      message: "Неверный формат документа",
    });
  });
});
