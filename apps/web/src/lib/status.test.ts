import { describe, expect, it } from "vitest";
import { commandBadge, formatValue, valueBadge } from "./status";
import type { Value } from "../api/types";

const t = (k: string, o?: Record<string, unknown>) => (o?.defaultValue as string) ?? k;
const v = (over: Partial<Value>): Value => ({ value: 1, source: "reported", quality: "good", ts: "x", ...over });

describe("valueBadge", () => {
  it("maps trust metadata to the five symbols", () => {
    expect(valueBadge(v({}))).toBe("ok");
    expect(valueBadge(v({ source: "assumed" }))).toBe("assumed");
    expect(valueBadge(v({ quality: "stale" }))).toBe("stale");
    expect(valueBadge(v({ quality: "unknown", value: null }))).toBe("unknown");
    expect(valueBadge(v({ quality: "not_supported", value: null }))).toBe("unsupported");
    expect(valueBadge(undefined)).toBe("unknown");
    expect(valueBadge(v({}), true)).toBe("pending");
  });
  it("stale assumed is still stale", () => {
    expect(valueBadge(v({ source: "assumed", quality: "stale" }))).toBe("stale");
  });
});

describe("formatValue never invents a value", () => {
  it("unknown shows a dash, not 0 or Off", () => {
    expect(formatValue(v({ quality: "unknown", value: null }), t)).toBe("—");
    expect(formatValue(undefined, t)).toBe("—");
  });
  it("not_supported is labelled", () => {
    expect(formatValue(v({ quality: "not_supported", value: null }), t)).toBe("status.unsupported");
  });
  it("formats numbers with units and booleans", () => {
    expect(formatValue(v({ value: 231.4, unit: "V" }), t)).toBe("231.4 V");
    expect(formatValue(v({ value: 230, unit: "V" }), t)).toBe("230 V");
    expect(formatValue(v({ value: true }), t)).toBe("value.on");
    expect(formatValue(v({ value: false }), t)).toBe("value.off");
  });
});

describe("commandBadge", () => {
  it("only confirmed is ✓", () => {
    expect(commandBadge("confirmed")).toBe("ok");
    expect(commandBadge("acked")).toBe("pending");
    expect(commandBadge("sent")).toBe("pending");
    for (const s of ["rejected", "failed", "expired", "timeout"] as const) expect(commandBadge(s)).toBe("failed");
  });
});
