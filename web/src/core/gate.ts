import type { Leg } from "./kelly";

export function passesEdgeGate(
  modelP: number,
  marketPrice: number,
  threshold = 0.03,
): boolean {
  return modelP - marketPrice > threshold;
}

export function filterLegs(legs: Leg[], threshold: number): Leg[] {
  return legs.filter((leg) => passesEdgeGate(leg.p, leg.price, threshold));
}
