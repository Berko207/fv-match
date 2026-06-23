import type { DevigMethod } from "./constants";

export function multiplicative(prices: number[]): number[] {
  if (!prices.length) return [];
  const implied = prices.map((p) => 1 / p);
  const total = implied.reduce((a, b) => a + b, 0);
  if (total === 0) return prices.map(() => 0);
  return implied.map((imp) => imp / total);
}

export function power(prices: number[], tol = 1e-10, maxIter = 100): number[] {
  if (!prices.length) return [];
  const r = prices.map((p) => 1 / p);
  const s = r.reduce((a, b) => a + b, 0);
  if (Math.abs(s - 1) < 1e-12) return [...r];

  let lo = 0.1;
  let hi = 10;
  for (let i = 0; i < maxIter; i += 1) {
    const mid = (lo + hi) / 2;
    const val = r.reduce((acc, ri) => acc + ri ** mid, 0);
    if (Math.abs(val - 1) < tol) break;
    if (val > 1) lo = mid;
    else hi = mid;
  }
  const k = (lo + hi) / 2;
  const probs = r.map((ri) => ri ** k);
  const total = probs.reduce((a, b) => a + b, 0);
  if (total === 0) return prices.map(() => 0);
  return probs.map((p) => p / total);
}

export function shin(prices: number[]): number[] {
  if (!prices.length) return [];
  const n = prices.length;
  if (n < 2) return [1];
  const r = prices.map((p) => 1 / p);
  const s = r.reduce((a, b) => a + b, 0);
  let z = (s - 1) / (n - 1);
  z = Math.max(0, Math.min(z, Math.min(...r) - 1e-12));
  const denom = 1 - z;
  if (denom <= 0) return multiplicative(prices);
  const probs = r.map((ri) => (ri - z) / denom);
  const total = probs.reduce((a, b) => a + b, 0);
  if (total <= 0) return multiplicative(prices);
  return probs.map((p) => Math.max(0, p / total));
}

export function devig(prices: number[], method: DevigMethod = "shin"): number[] {
  if (method === "multiplicative") return multiplicative(prices);
  if (method === "power") return power(prices);
  return shin(prices);
}
