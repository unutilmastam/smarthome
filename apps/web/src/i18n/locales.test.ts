import { describe, expect, it } from "vitest";
import uz from "./locales/uz.json";
import ru from "./locales/ru.json";
import en from "./locales/en.json";
import capabilities from "../../../../packages/contracts/capabilities.json";

function keys(o: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(o).flatMap(([k, v]) =>
    v && typeof v === "object" ? keys(v as Record<string, unknown>, `${prefix}${k}.`) : [`${prefix}${k}`]);
}

describe("i18n", () => {
  it("ru and en have exactly the uz keys", () => {
    const base = keys(uz).sort();
    expect(keys(ru).sort()).toEqual(base);
    expect(keys(en).sort()).toEqual(base);
  });
  it("every capability, attribute and action from contracts has an uz label", () => {
    const caps = (capabilities as { capabilities: Record<string, { attributes: object; actions: object }> }).capabilities;
    for (const [name, c] of Object.entries(caps)) {
      expect((uz.cap as Record<string, string>)[name], name).toBeTruthy();
      for (const a of Object.keys(c.attributes)) expect((uz.attr as Record<string, string>)[a], a).toBeTruthy();
      for (const a of Object.keys(c.actions)) expect((uz.action as Record<string, string>)[a], a).toBeTruthy();
    }
  });
});
