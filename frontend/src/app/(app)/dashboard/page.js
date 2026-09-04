"use client";

/**
 * Dashboard — protected placeholder page.
 *
 * Demonstrates the auth guard pattern: if the user is not authenticated
 * after hydration completes, redirect to /login.
 *
 * Future: Replace the placeholder content with the real dashboard
 * (portfolio summary, market overview, AI quick-access).
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth-store";
import apiClient from "@/lib/api-client";
import { usePortfolio } from "@/hooks/use-portfolio";
import { useAlerts } from "@/hooks/use-alerts";
import { useAnalyses } from "@/hooks/use-analyses";
import { useExchanges } from "@/hooks/use-exchanges";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isHydrating, clearAuth } = useAuthStore();
  const portfolio = usePortfolio();
  const alerts = useAlerts();
  const analyses = useAnalyses({ limit: 3 });
  const exchanges = useExchanges();

  // Auth guard — redirect to login if unauthenticated after hydration
  useEffect(() => {
    if (!isHydrating && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isHydrating, isAuthenticated, router]);

  const handleLogout = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // Proceed with local logout even if the server call fails
    } finally {
      clearAuth();
      router.push("/login");
    }
  };

  // Show nothing while hydrating (prevents flicker)
  if (isHydrating) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground text-sm animate-pulse">Loading…</p>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <main className="prism-shell relative overflow-hidden">
      <div className="prism-orb size-72 bg-primary/20 -top-28 -left-24" />
      <div className="prism-orb size-64 bg-cyan-400/10 top-36 -right-24" style={{ animationDelay: "-5s" }} />
      <div className="relative max-w-6xl mx-auto space-y-7" style={{ animation: "prism-in .45s ease-out both" }}>
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="prism-kicker">Private crypto intelligence</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Good to see you, {user?.full_name?.split(" ")[0] || "there"}.</h1>
          <p className="text-sm text-muted-foreground mt-1">Read-only portfolio intelligence, grounded in live data.</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="secondary">{user?.role}</Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            id="logout-btn"
          >
            Sign out
          </Button>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Portfolio value" value={portfolio.isLoading ? "Loading…" : portfolio.data?.total_estimated_usd_value ? `$${Number(portfolio.data.total_estimated_usd_value).toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "Connect exchange"} note={portfolio.data ? `${portfolio.data.assets.length} assets · ${portfolio.data.exchange_name}` : "Live balances when connected"} href="/portfolio" />
        <MetricCard label="Active signals" value={alerts.isLoading ? "—" : String(alerts.data?.filter((item) => item.status === "active").length || 0)} note="Price conditions waiting to trigger" href="/alerts" />
        <MetricCard label="Saved analyses" value={analyses.isLoading ? "—" : String(analyses.data?.length || 0)} note="Your most recent decision-support reports" href="/analyses" />
      </section>
      <section className="grid gap-5 lg:grid-cols-[1.25fr_.75fr]">
        <Card className="prism-panel border-primary/20"><CardHeader><p className="prism-kicker">Ask PrismAI</p><CardTitle className="text-2xl">Turn market noise into a clearer next step.</CardTitle><CardDescription>Ask in English, Roman Urdu, or mixed language. PrismAI stays read-only and identifies uncertainty when data is missing.</CardDescription></CardHeader><CardContent className="flex flex-wrap gap-3"><Button asChild><Link href="/assistant">Start an analysis</Link></Button><Button asChild variant="outline"><Link href="/market/BTCUSDT">Explore BTC market</Link></Button></CardContent></Card>
        <Card className="prism-panel"><CardHeader><CardTitle>Connection status</CardTitle><CardDescription>Only read-only Binance access is supported.</CardDescription></CardHeader><CardContent><div className="flex items-center justify-between rounded-lg bg-muted/60 p-3"><span className="text-sm">Exchange</span><Badge variant={exchanges.data?.length ? "default" : "secondary"}>{exchanges.isLoading ? "Checking…" : exchanges.data?.length ? "Connected" : "Not connected"}</Badge></div><Button className="mt-4 w-full" variant="outline" asChild><Link href="/exchanges">Manage exchange</Link></Button></CardContent></Card>
      </section>
      <section><div className="mb-3 flex items-end justify-between"><div><p className="prism-kicker">Workspace</p><h2 className="text-xl font-semibold">Everything in one secure view</h2></div><Link className="text-sm text-primary hover:underline" href="/profile">Security settings →</Link></div><nav className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" aria-label="Main navigation"><NavLink href="/assistant" label="AI Assistant" description="Ask naturally" /><NavLink href="/watchlists" label="Watchlists" description="Track assets" /><NavLink href="/portfolio" label="Portfolio" description="Live balances" /><NavLink href="/complaints" label="Support" description="Get help" /><NavLink href="/profile" label="Profile" description="Sessions & risk" />{user?.role === "admin" && <NavLink href="/admin" label="Admin" description="Operations" />}</nav></section>
      </div>
    </main>
  );
}

function NavLink({ href, label, description }) {
  return (
    <Link
      href={href}
      className="prism-link flex flex-col rounded-xl border border-white/10 bg-card/70 px-4 py-4 backdrop-blur-sm min-w-[140px]"
    >
      <span className="text-sm font-medium">{label}</span>
      <span className="text-xs text-muted-foreground">{description}</span>
    </Link>
  );
}

function MetricCard({ label, value, note, href }) {
  return (
    <Link href={href} className="prism-link rounded-xl"><Card className="prism-panel h-full"><CardHeader><CardDescription>{label}</CardDescription><CardTitle className="text-2xl font-semibold tracking-tight">{value}</CardTitle></CardHeader><CardContent><p className="text-xs text-muted-foreground">{note}</p></CardContent></Card></Link>
  );
}
