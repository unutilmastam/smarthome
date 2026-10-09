import { describe, expect, it } from "vitest";
import { api, setAccessToken } from "./client";
import { mockFetch, ok } from "../test/utils";

describe("api client", () => {
  it("refreshes via cookie on 401 and retries once", async () => {
    setAccessToken("expired");
    let meCalls = 0;
    const calls = mockFetch((url, init) => {
      if (url.endsWith("/auth/refresh")) return ok({ access_token: "fresh" });
      if (url.endsWith("/auth/me")) {
        meCalls += 1;
        const auth = (init.headers as Record<string, string>).Authorization;
        return auth === "Bearer fresh" ? ok({ id: "u" }) : { status: 401, body: { data: null, error: { code: "AUTH_REQUIRED", message: "x" } } };
      }
      return undefined;
    });
    await expect(api.get("/auth/me")).resolves.toEqual({ id: "u" });
    expect(meCalls).toBe(2);
    expect(calls.map((c) => c.url)).toEqual(["/api/v1/auth/me", "/api/v1/auth/refresh", "/api/v1/auth/me"]);
  });

  it("never stores tokens in web storage", async () => {
    mockFetch((url) => (url.endsWith("/auth/login") ? ok({ access_token: "a", user: { id: "u" } }) : undefined));
    await api.post("/auth/login", { email: "x", password: "y" });
    expect(JSON.stringify({ ...localStorage })).not.toContain("a\"");
    expect(sessionStorage.length).toBe(0);
  });
});
