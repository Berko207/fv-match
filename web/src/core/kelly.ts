export interface Leg {
  outcome: string;
  p: number;
  price: number;
}

export function kellyFraction(p: number, price: number): number {
  if (p <= price || price >= 1 || price <= 0) return 0;
  return (p - price) / (1 - price);
}

export function fractionalKelly(
  p: number,
  price: number,
  fraction = 0.25,
  cap = 0.05,
): number {
  const full = kellyFraction(p, price);
  const scaled = full * Math.max(0, Math.min(fraction, 1));
  return Math.min(scaled, Math.max(0, cap));
}

export function jointMatchStakes(
  legs: Leg[],
  fraction = 0.25,
  cap = 0.05,
): number[] {
  if (!legs.length) return [];
  const raw = legs.map((leg) => fractionalKelly(leg.p, leg.price, fraction, cap));
  const totalRaw = raw.reduce((a, b) => a + b, 0);
  if (totalRaw <= cap + 1e-12) return raw;
  const scale = totalRaw > 0 ? cap / totalRaw : 0;
  return raw.map((s) => Math.min(s * scale, cap));
}
