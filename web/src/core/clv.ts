/**
 * Closing-line value (CLV) — the project's north-star validation metric.
 * TS port of accounting/clv.py.
 *
 * CLV measures whether we transacted at a better price than the market's
 * closing line. Beating the close is evidence of genuine edge that does not
 * depend on the (high-variance) match result.
 */

/**
 * CLV as a fractional price improvement vs the close. For a $1-payout share, a
 * *lower* entry than the close is favourable: `(close - entry) / entry`.
 * Positive means we bought cheaper than the close (beat the market).
 */
export function computeClv(entryPrice: number, closePrice: number): number {
  if (entryPrice <= 0) throw new Error("entryPrice must be > 0");
  return (closePrice - entryPrice) / entryPrice;
}
