import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import HomePage from "./page";
import { useAuthStore } from "@/store/useAuthStore";

describe("HomePage", () => {
  it("renders main heading correctly", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { level: 1 })).toBeDefined();
    expect(screen.getByText("Чистый документ")).toBeDefined();
  });

  it("calls /api/v1/auth/dev-session with GET method", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: "mock_jwt_token" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await useAuthStore.getState().initDevAuth();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/dev-session"),
      expect.objectContaining({ method: "GET" })
    );
    vi.unstubAllGlobals();
  });
});
