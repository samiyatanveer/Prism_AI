"use client";

/**
 * Exchange status card — shows connection info and disconnect button.
 * No credential fields are displayed — only exchange name, label, status, last sync.
 */

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useDisconnectExchange, useValidateExchange } from "@/hooks/use-exchanges";

function formatDate(iso) {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString();
}

export default function ExchangeStatusCard({ exchange }) {
  const [confirming, setConfirming] = useState(false);
  const { mutate: disconnect, isPending: isDisconnecting } = useDisconnectExchange();
  const { mutate: validate, isPending: isValidating } = useValidateExchange();

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base capitalize">
            {exchange.display_label || exchange.exchange_name}
          </CardTitle>
          <Badge variant={exchange.is_active ? "default" : "secondary"}>
            {exchange.is_active ? "Active" : "Inactive"}
          </Badge>
        </div>
        <CardDescription className="text-xs capitalize">
          {exchange.exchange_name} · {exchange.permissions || "read-only"}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="text-xs text-muted-foreground space-y-1">
          <p>Last synced: {formatDate(exchange.last_synced_at)}</p>
          <p>Connected: {formatDate(exchange.created_at)}</p>
        </div>

        <Separator />

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={isValidating}
            onClick={() => validate(exchange.id)}
            id={`validate-exchange-${exchange.id}`}
          >
            {isValidating ? "Checking…" : "Validate credentials"}
          </Button>

          {!confirming ? (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              onClick={() => setConfirming(true)}
              id={`disconnect-exchange-${exchange.id}`}
            >
              Disconnect
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Sure?</span>
              <Button
                variant="destructive"
                size="sm"
                disabled={isDisconnecting}
                onClick={() => {
                  disconnect(exchange.id);
                  setConfirming(false);
                }}
                id={`confirm-disconnect-${exchange.id}`}
              >
                {isDisconnecting ? "…" : "Yes, disconnect"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirming(false)}
              >
                Cancel
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
