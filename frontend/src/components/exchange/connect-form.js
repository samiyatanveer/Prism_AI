"use client";

/**
 * Exchange connect form.
 * - Inline validation errors (form field level)
 * - Sonner toast on success (handled by useConnectExchange hook)
 * - API key / secret fields are never stored in state beyond the submit call
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useConnectExchange } from "@/hooks/use-exchanges";

export default function ConnectForm({ onSuccess }) {
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [label, setLabel] = useState("");
  const [formError, setFormError] = useState(null);

  const { mutate: connect, isPending } = useConnectExchange();

  const handleSubmit = (e) => {
    e.preventDefault();
    setFormError(null);

    if (apiKey.length < 8) {
      setFormError("API key must be at least 8 characters.");
      return;
    }
    if (apiSecret.length < 8) {
      setFormError("API secret must be at least 8 characters.");
      return;
    }

    connect(
      {
        exchange_name: "binance",
        api_key: apiKey,
        api_secret: apiSecret,
        display_label: label || undefined,
      },
      {
        onSuccess: () => {
          // Clear sensitive fields immediately on success
          setApiKey("");
          setApiSecret("");
          setLabel("");
          if (onSuccess) onSuccess();
        },
        onError: (err) => {
          const detail = err.response?.data?.detail;
          setFormError(
            detail ||
              "Could not connect exchange. Check your credentials and try again."
          );
        },
      }
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Connect Binance</CardTitle>
        <CardDescription>
          Use a read-only API key. Your credentials are encrypted before storage
          and never returned in any response.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" id="connect-exchange-form">
          <div className="space-y-1.5">
            <Label htmlFor="exchange-label">Label (optional)</Label>
            <Input
              id="exchange-label"
              placeholder="e.g. Main account"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              maxLength={100}
              autoComplete="off"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="text"
              placeholder="Binance API key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
              autoComplete="off"
              spellCheck={false}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="api-secret">API Secret</Label>
            <Input
              id="api-secret"
              type="password"
              placeholder="Binance API secret"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              required
              autoComplete="off"
            />
          </div>

          {formError && (
            <p className="text-sm text-destructive" role="alert">
              {formError}
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={isPending}
            id="connect-exchange-btn"
          >
            {isPending ? "Connecting…" : "Connect exchange"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
