import { describe, expect, it } from "vitest";
import { KEY_RE, suggestKey } from "./catalog";

describe("suggestKey", () => {
  it("makes firmware-safe keys from Uzbek/Russian names", () => {
    expect(suggestKey("Bog' chiroqlari")).toBe("bog_chiroqlari");
    expect(suggestKey("Oʻg'il xonasi chirogʻi")).toBe("ogil_xonasi_chirogi");
    expect(suggestKey("Свет в кухне")).toBe("svet_v_kuxne");
    expect(suggestKey("1-qavat")).toBe("device_1_qavat");
    expect(suggestKey("!!")).toBe("device");
    expect(suggestKey("Chiroq", ["chiroq", "chiroq_2"])).toBe("chiroq_3");
    for (const n of ["Bog' chiroqlari", "1-qavat", "!!", "Свет"]) expect(KEY_RE.test(suggestKey(n))).toBe(true);
  });
});
