"use client";

/**
 * Portfolio holdings table.
 * USD valuation is nullable — displays "—" when null, never fabricates a value.
 */

function formatDecimal(value, decimals = 6) {
  if (value === null || value === undefined) return "—";
  const n = parseFloat(value);
  if (isNaN(n)) return "—";
  // Strip trailing zeros
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: decimals,
  });
}

function formatUSD(value) {
  if (value === null || value === undefined) return null;
  const n = parseFloat(value);
  if (isNaN(n)) return null;
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function HoldingsTable({ assets, totalUsd }) {
  if (!assets || assets.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-6 text-center">
        No holdings found. Your exchange account may have no non-zero balances.
      </p>
    );
  }

  const formattedTotal = formatUSD(totalUsd);

  return (
    <div className="space-y-3 overflow-x-auto">
      {/* Header */}
      <div className="grid min-w-[520px] grid-cols-4 gap-4 px-3 text-xs font-medium text-muted-foreground uppercase tracking-[.14em]">
        <span>Asset</span>
        <span className="text-right">Free</span>
        <span className="text-right">Locked</span>
        <span className="text-right">Est. USD</span>
      </div>

      {/* Rows */}
      <div className="min-w-[520px] space-y-1">
        {assets.map((holding) => (
          <div
            key={holding.asset}
            className="grid grid-cols-4 gap-4 rounded-xl border border-transparent px-3 py-3 bg-card/45 hover:border-primary/20 hover:bg-accent/30 transition-all text-sm"
          >
            <span className="font-mono font-semibold">{holding.asset}</span>
            <span className="text-right font-mono text-muted-foreground">
              {formatDecimal(holding.free)}
            </span>
            <span className="text-right font-mono text-muted-foreground">
              {formatDecimal(holding.locked)}
            </span>
            <span className="text-right font-mono">
              {formatUSD(holding.estimated_usd_value) ?? (
                <span className="text-muted-foreground">—</span>
              )}
            </span>
          </div>
        ))}
      </div>

      {/* Total row */}
      <div className="border-t pt-3 flex justify-between items-center px-3">
        <span className="text-sm font-medium text-muted-foreground">
          Total estimated value
        </span>
        <span className="font-mono font-semibold text-sm">
          {formattedTotal ?? (
            <span className="text-muted-foreground text-xs">
              Partial — some assets have no USD price
            </span>
          )}
        </span>
      </div>
    </div>
  );
}
