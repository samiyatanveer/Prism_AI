"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useTicker } from "@/hooks/use-market";
import { useCandles } from "@/hooks/use-market";
import TickerCard from "@/components/market/ticker-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import Link from "next/link";

// PriceChart must be client-only (uses DOM APIs)
const PriceChart = dynamic(() => import("@/components/market/price-chart"), {
  ssr: false,
  loading: () => <Skeleton className="w-full rounded-xl" style={{ height: 380 }} />,
});

const INTERVALS = [
  { label: "15m", value: "15m" },
  { label: "1h",  value: "1h" },
  { label: "4h",  value: "4h" },
  { label: "1D",  value: "1d" },
  { label: "1W",  value: "1w" },
];

export default function MarketPageClient({ symbol }) {
  const [interval, setInterval] = useState("1d");

  const sym = (symbol || "BTCUSDT").toUpperCase();
  const { data: ticker, isLoading: tickerLoading, error: tickerError } = useTicker(sym);
  const {
    data: candlesData,
    isLoading: candlesLoading,
    error: candlesError,
  } = useCandles(sym, interval, 120);

  const noExchange =
    tickerError?.response?.status === 424 || candlesError?.response?.status === 424;

  return (
    <div className="prism-page max-w-6xl">
      {/* Header */}
      <div className="prism-hero">
        <p className="prism-kicker">Live market observatory</p>
        <h1 className="text-2xl font-bold tracking-tight font-mono">{sym}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Live market data from your connected exchange.
        </p>
      </div>

      {/* No exchange connected */}
      {noExchange && (
        <div className="prism-empty space-y-3">
          <p className="text-muted-foreground text-sm">
            No exchange connected. Connect one to see live market data.
          </p>
          <Button asChild size="sm">
            <Link href="/exchanges">Connect exchange</Link>
          </Button>
        </div>
      )}

      {!noExchange && (
        <>
          {/* Ticker */}
          {tickerLoading && <Skeleton className="h-28 w-full rounded-xl" />}
          {!tickerLoading && tickerError && (
            <p className="text-sm text-destructive" role="alert">
              Could not load ticker data.
            </p>
          )}
          {!tickerLoading && ticker && <TickerCard ticker={ticker} />}

          {/* Interval selector */}
          <div className="prism-tabs">
            {INTERVALS.map((iv) => (
              <button
                key={iv.value}
                onClick={() => setInterval(iv.value)}
                className={`prism-tab ${
                  interval === iv.value
                    ? "prism-tab-active"
                    : ""
                }`}
                id={`interval-${iv.value}`}
              >
                {iv.label}
              </button>
            ))}
          </div>

          {/* Candlestick chart */}
          {candlesLoading && <Skeleton className="w-full rounded-xl" style={{ height: 380 }} />}
          {!candlesLoading && candlesError && (
            <p className="text-sm text-destructive" role="alert">
              Could not load chart data.
            </p>
          )}
          {!candlesLoading && candlesData && (
            <div className="prism-surface p-2 sm:p-3"><PriceChart candles={candlesData.candles} height={420} /></div>
          )}
        </>
      )}
    </div>
  );
}
