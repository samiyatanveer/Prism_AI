"use client";

import { useState } from "react";
import { useExchanges } from "@/hooks/use-exchanges";
import ConnectForm from "@/components/exchange/connect-form";
import ExchangeStatusCard from "@/components/exchange/exchange-status-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

function ExchangeSkeleton() {
  return (
    <div className="rounded-xl border bg-card p-5 space-y-3">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-full" />
    </div>
  );
}

export default function ExchangesPageClient() {
  const [showForm, setShowForm] = useState(false);
  const { data: exchanges, isLoading, error } = useExchanges();

  const hasExchanges = exchanges && exchanges.length > 0;

  return (
    <div className="prism-page max-w-3xl">
      {/* Header */}
      <div className="prism-hero flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="prism-kicker">Secure data bridge</p>
          <h1 className="text-2xl font-bold tracking-tight">Exchanges</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Connect your exchange accounts to enable portfolio tracking and market data.
          </p>
        </div>
        {hasExchanges && !showForm && (
          <Button
            size="sm"
            onClick={() => setShowForm(true)}
            id="add-exchange-btn"
          >
            Add exchange
          </Button>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-3">
          <ExchangeSkeleton />
          <ExchangeSkeleton />
        </div>
      )}

      {/* Error state */}
      {error && (
        <p className="text-sm text-destructive text-center py-6" role="alert">
          Could not load exchanges. Please refresh and try again.
        </p>
      )}

      {/* Connected exchanges list */}
      {!isLoading && !error && (
        <>
          {hasExchanges ? (
            <div className="space-y-3">
              {exchanges.map((ex) => (
                <ExchangeStatusCard key={ex.id} exchange={ex} />
              ))}
            </div>
          ) : (
            !showForm && (
              <div className="prism-empty space-y-3">
                <p className="text-muted-foreground text-sm">
                  No exchanges connected yet.
                </p>
                <Button
                  onClick={() => setShowForm(true)}
                  id="connect-first-exchange-btn"
                >
                  Connect Binance
                </Button>
              </div>
            )
          )}

          {/* Connect form */}
          {showForm && (
            <ConnectForm
              onSuccess={() => setShowForm(false)}
            />
          )}

          {showForm && hasExchanges && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          )}
        </>
      )}
    </div>
  );
}
