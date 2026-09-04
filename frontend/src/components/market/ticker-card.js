"use client";

/**
 * Ticker card — current price and 24h statistics.
 */

export default function TickerCard({ ticker }) {
  if (!ticker) return null;

  const price = parseFloat(ticker.price);
  const change = parseFloat(ticker.change_24h_pct);
  const isPositive = change >= 0;

  return (
    <div className="prism-surface space-y-5 p-5 sm:p-6">
      <div className="flex items-baseline justify-between">
        <div>
          <span className="text-2xl font-bold font-mono">
            {price.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 8,
            })}
          </span>
          <span className="ml-2 text-sm text-muted-foreground">
            {ticker.quote_asset}
          </span>
        </div>
        <span
          className={`text-sm font-medium px-2 py-0.5 rounded-full ${
            isPositive
              ? "bg-green-500/15 text-green-400"
              : "bg-red-500/15 text-red-400"
          }`}
        >
          {isPositive ? "+" : ""}
          {change.toFixed(2)}%
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground sm:gap-4">
        <div>
          <p className="uppercase tracking-wide mb-0.5">24h High</p>
          <p className="font-mono text-foreground">
            {parseFloat(ticker.high_24h).toLocaleString("en-US", {
              minimumFractionDigits: 2,
            })}
          </p>
        </div>
        <div>
          <p className="uppercase tracking-wide mb-0.5">24h Low</p>
          <p className="font-mono text-foreground">
            {parseFloat(ticker.low_24h).toLocaleString("en-US", {
              minimumFractionDigits: 2,
            })}
          </p>
        </div>
        <div>
          <p className="uppercase tracking-wide mb-0.5">24h Volume</p>
          <p className="font-mono text-foreground">
            {parseFloat(ticker.volume_24h).toLocaleString("en-US", {
              maximumFractionDigits: 2,
            })}
          </p>
        </div>
      </div>
    </div>
  );
}
