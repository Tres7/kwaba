import { describe, expect, it } from "vitest";
import { formatPourcent } from "./taux";

describe("formatPourcent", () => {
  it("writes a rate in each language, with its decimals when there are some", () => {
    expect(formatPourcent(0.06, "fr")).toBe("6 %");
    expect(formatPourcent(0.065, "fr")).toBe("6,5 %");
    expect(formatPourcent(0.065, "en")).toBe("6.5%");
    expect(formatPourcent(0.12, "en")).toBe("12%");
  });
});
