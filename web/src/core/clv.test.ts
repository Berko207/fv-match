import { describe, expect, it } from "vitest";

import { computeClv } from "./clv";

describe("computeClv", () => {
  it("is positive when the line rises after entry (beat the close)", () => {
    const clv = computeClv(0.455, 0.478);
    expect(clv).toBeCloseTo((0.478 - 0.455) / 0.455, 10);
    expect(clv).toBeGreaterThan(0);
  });

  it("is negative when the line drops after entry", () => {
    expect(computeClv(0.5, 0.45)).toBeLessThan(0);
  });

  it("is zero at entry", () => {
    expect(computeClv(0.5, 0.5)).toBe(0);
  });

  it("throws on a non-positive entry price", () => {
    expect(() => computeClv(0, 0.5)).toThrow();
  });
});
