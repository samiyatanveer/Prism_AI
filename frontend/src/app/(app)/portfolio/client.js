"use client";

import { usePortfolio } from "@/hooks/use-portfolio";
import HoldingsTable from "@/components/portfolio/holdings-table";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import Link from "next/link";

function PortfolioSkeleton() {
  return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <Skeleton key={i} className="h-10 w-full rounded-lg" />
      ))}
    </div>
  );
}

export default function PortfolioPageClient() {
  const { data, isLoading, error, refetch, isRefetching } = usePortfolio();

  return (
    <div className="prism-page max-w-5xl">
      {/* Header */}
      <div className="prism-hero flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="prism-kicker">Connected capital</p>
          <h1 className="text-2xl font-bold tracking-tight">Portfolio</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Live holdings from your connected exchange.
            {data && (
              <span className="ml-1 capitalize text-xs text-muted-foreground/70">
                ({data.exchange_name})
              </span>
            )}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={isLoading || isRefetching}
          onClick={() => refetch()}
          id="refresh-portfolio-btn"
        >
          {isRefetching ? "Refreshing…" : "Refresh"}
        </Button>
      </div>

      {!isLoading && !error && data && <section className="grid gap-3 sm:grid-cols-3"><div className="prism-stat"><p className="text-xs text-muted-foreground">Estimated value</p><p className="mt-1 text-xl font-semibold">${Number(data.total_estimated_usd_value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</p></div><div className="prism-stat"><p className="text-xs text-muted-foreground">Assets held</p><p className="mt-1 text-xl font-semibold">{data.assets.length}</p></div><div className="prism-stat"><p className="text-xs text-muted-foreground">Data source</p><p className="mt-1 text-xl font-semibold capitalize">{data.exchange_name}</p></div></section>}

      {/* Loading */}
      {isLoading && <PortfolioSkeleton />}

      {/* No exchange connected */}
      {!isLoading && error?.response?.status === 424 && (
        <div className="prism-empty space-y-3">
          <p className="text-muted-foreground text-sm">
            No exchange connected yet. Connect an exchange to see your portfolio.
          </p>
          <Button asChild size="sm">
            <Link href="/exchanges">Connect exchange</Link>
          </Button>
        </div>
      )}

      {/* Rate limit */}
      {!isLoading && error?.response?.status === 429 && (
        <p className="text-sm text-destructive text-center py-6" role="alert">
          Exchange rate limit reached. Please wait a moment and refresh.
        </p>
      )}

      {/* Other error */}
      {!isLoading && error && error?.response?.status !== 424 && error?.response?.status !== 429 && (
        <p className="text-sm text-destructive text-center py-6" role="alert">
          Could not load portfolio. The exchange may be temporarily unavailable.
        </p>
      )}

      {/* Holdings */}
      {!isLoading && !error && data && (
        <div className="prism-surface p-3 sm:p-5">
          <HoldingsTable assets={data.assets} totalUsd={data.total_estimated_usd_value} />
        </div>
      )}

      {/* USD valuation note */}
      {!isLoading && !error && data && (
        <p className="text-xs text-muted-foreground text-center">
          USD values derived from live USDT ticker prices. Assets without a USDT market show{" "}
          <span className="font-mono">—</span>.
        </p>
      )}
    </div>
  );
}
