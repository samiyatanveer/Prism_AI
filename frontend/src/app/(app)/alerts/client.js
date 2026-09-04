"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Bell,
  BellRing,
  BellOff,
  Plus,
  Trash2,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  LineChart,
  X,
  Power,
  TrendingUp,
  TrendingDown,
  Sparkles,
} from "lucide-react";
import {
  useAlerts,
  useAlertSummary,
  useCreateAlert,
  useUpdateAlert,
  useToggleAlert,
  useDeleteAlert,
} from "@/hooks/use-alerts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const PRESET_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"];

export default function AlertsPageClient() {
  const [activeFilter, setActiveFilter] = useState("all");
  const { data: alerts, isLoading, error } = useAlerts(activeFilter);
  const { data: summary } = useAlertSummary();

  const { mutate: createAlert, isPending: isCreating } = useCreateAlert();
  const { mutate: updateAlert, isPending: isUpdating } = useUpdateAlert();
  const { mutate: toggleAlert, isPending: isToggling } = useToggleAlert();
  const { mutate: deleteAlert, isPending: isDeleting } = useDeleteAlert();

  // Create modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [symbolInput, setSymbolInput] = useState("");
  const [targetPriceInput, setTargetPriceInput] = useState("");
  const [conditionInput, setConditionInput] = useState("above");
  const [notesInput, setNotesInput] = useState("");

  // Edit modal state
  const [editingAlert, setEditingAlert] = useState(null);
  const [editPriceInput, setEditPriceInput] = useState("");
  const [editConditionInput, setEditConditionInput] = useState("above");
  const [editNotesInput, setEditNotesInput] = useState("");

  const handleCreateSubmit = (e) => {
    e.preventDefault();
    const sym = symbolInput.trim().toUpperCase();
    const price = parseFloat(targetPriceInput);
    if (!sym || isNaN(price) || price <= 0) return;

    createAlert(
      {
        symbol: sym,
        target_price: price,
        condition: conditionInput,
        notes: notesInput.trim() || undefined,
      },
      {
        onSuccess: () => {
          setShowCreateModal(false);
          setSymbolInput("");
          setTargetPriceInput("");
          setNotesInput("");
          setConditionInput("above");
        },
      }
    );
  };

  const handleStartEdit = (alert) => {
    setEditingAlert(alert);
    setEditPriceInput(alert.target_price);
    setEditConditionInput(alert.condition);
    setEditNotesInput(alert.notes || "");
  };

  const handleSaveEdit = (e) => {
    e.preventDefault();
    if (!editingAlert) return;
    const price = parseFloat(editPriceInput);
    if (isNaN(price) || price <= 0) return;

    updateAlert(
      {
        alertId: editingAlert.id,
        target_price: price,
        condition: editConditionInput,
        notes: editNotesInput.trim() || undefined,
      },
      {
        onSuccess: () => {
          setEditingAlert(null);
        },
      }
    );
  };

  const handleDelete = (alertId, symbol) => {
    if (confirm(`Delete alert for ${symbol}?`)) {
      deleteAlert(alertId);
    }
  };

  return (
    <main className="max-w-6xl mx-auto space-y-8 p-4 md:p-8">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">Price Alerts</h1>
            {summary && summary.total > 0 && (
              <Badge variant="secondary" className="font-mono">
                {summary.total}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Set custom price threshold alerts evaluated on-demand against live exchange data.
          </p>
        </div>

        <div>
          <Button
            size="sm"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5"
            id="create-alert-btn"
          >
            <Plus className="w-4 h-4" />
            <span>New Alert</span>
          </Button>
        </div>
      </header>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-4 bg-card/60">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Total Alerts</span>
            <Bell className="w-4 h-4 text-muted-foreground" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1">{summary?.total ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60 border-emerald-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-400">Active</span>
            <BellRing className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-emerald-400">{summary?.active ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60 border-amber-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-400">Triggered</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-amber-400">{summary?.triggered ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Disabled</span>
            <BellOff className="w-4 h-4 text-muted-foreground" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-muted-foreground">{summary?.disabled ?? 0}</p>
        </Card>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex items-center gap-2 border-b pb-2">
        {["all", "active", "triggered", "disabled"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveFilter(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
              activeFilter === tab
                ? "bg-primary text-primary-foreground"
                : "bg-card hover:bg-accent text-muted-foreground border"
            }`}
            id={`filter-${tab}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full rounded-xl" />
          <Skeleton className="h-20 w-full rounded-xl" />
          <Skeleton className="h-20 w-full rounded-xl" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && alerts && alerts.length === 0 && (
        <Card className="border-dashed bg-card/40">
          <CardContent className="p-12 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Bell className="w-6 h-6" />
            </div>
            <div className="space-y-1 max-w-sm mx-auto">
              <h3 className="text-lg font-semibold">No alerts found</h3>
              <p className="text-xs text-muted-foreground">
                {activeFilter === "all"
                  ? "Set up price threshold alerts for your favorite crypto assets."
                  : `No ${activeFilter} alerts found.`}
              </p>
            </div>
            <Button size="sm" onClick={() => setShowCreateModal(true)} className="gap-1">
              <Plus className="w-4 h-4" />
              <span>Create Alert</span>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Alerts List */}
      {!isLoading && alerts && alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const isTriggered = alert.status === "triggered";
            const isActive = alert.status === "active";
            const isDisabled = alert.status === "disabled";
            const isAbove = alert.condition === "above";

            return (
              <Card
                key={alert.id}
                className={`transition-all ${
                  isTriggered
                    ? "border-amber-500/40 bg-amber-500/5"
                    : isActive
                    ? "border-border bg-card/70"
                    : "border-border/40 bg-card/30 opacity-70"
                }`}
              >
                <CardContent className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  {/* Left: Asset, Condition, Target */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-mono font-bold text-base text-foreground">{alert.symbol}</span>
                      <div
                        className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded ${
                          isAbove
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {isAbove ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                        <span>
                          {isAbove ? "≥ Above" : "≤ Below"} ${Number(alert.target_price).toLocaleString()}
                        </span>
                      </div>

                      {/* Status Badge */}
                      {isTriggered && (
                        <Badge variant="outline" className="text-xs bg-amber-500/20 text-amber-300 border-amber-500/40 gap-1 font-medium">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Triggered</span>
                        </Badge>
                      )}
                      {isActive && (
                        <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-medium">
                          Active
                        </Badge>
                      )}
                      {isDisabled && (
                        <Badge variant="secondary" className="text-xs font-medium">
                          Disabled
                        </Badge>
                      )}
                    </div>

                    {/* Notes */}
                    {alert.notes && <p className="text-xs text-muted-foreground">{alert.notes}</p>}

                    {/* Trigger Details */}
                    {isTriggered && alert.triggered_price && (
                      <p className="text-xs text-amber-300/90 font-mono">
                        Triggered at ${Number(alert.triggered_price).toLocaleString()}{" "}
                        {alert.triggered_at ? `on ${new Date(alert.triggered_at).toLocaleDateString()} ${new Date(alert.triggered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ""}
                      </p>
                    )}
                  </div>

                  {/* Middle: Live Market Price & Distance */}
                  <div className="text-left md:text-right font-mono space-y-0.5">
                    {alert.current_price !== null && alert.current_price !== undefined ? (
                      <>
                        <div className="text-xs text-muted-foreground">Current Price</div>
                        <div className="font-semibold text-sm">
                          ${Number(alert.current_price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                        </div>
                        {isActive && alert.distance_pct !== null && (
                          <div className="text-xs text-muted-foreground">
                            {alert.distance_pct >= 0 ? "+" : ""}
                            {Number(alert.distance_pct).toFixed(2)}% to trigger
                          </div>
                        )}
                      </>
                    ) : (
                      <span className="text-xs text-muted-foreground italic">Live price unavailable</span>
                    )}
                  </div>

                  {/* Right: Actions */}
                  <div className="flex items-center gap-2 self-end md:self-center pt-2 md:pt-0">
                    {/* View Chart */}
                    <Button asChild variant="ghost" size="xs" className="h-8 px-2 text-xs gap-1">
                      <Link href={`/market/${alert.symbol}`}>
                        <LineChart className="w-3.5 h-3.5 text-primary" />
                        <span className="hidden sm:inline">Chart</span>
                      </Link>
                    </Button>

                    {/* Toggle */}
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => toggleAlert(alert.id)}
                      disabled={isToggling}
                      className={`h-8 px-2 text-xs gap-1 ${
                        isActive ? "text-amber-400 hover:text-amber-300" : "text-emerald-400 hover:text-emerald-300"
                      }`}
                      title={isActive ? "Disable alert" : "Enable / Reset alert"}
                    >
                      <Power className="w-3.5 h-3.5" />
                      <span>{isActive ? "Disable" : isTriggered ? "Re-arm" : "Enable"}</span>
                    </Button>

                    {/* Edit */}
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleStartEdit(alert)}
                      className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </Button>

                    {/* Delete */}
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleDelete(alert.id, alert.symbol)}
                      disabled={isDeleting}
                      className="h-8 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Alert Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md shadow-2xl border bg-card">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg font-bold">Create Price Alert</CardTitle>
                <CardDescription className="text-xs">Set a price threshold and trigger condition.</CardDescription>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Symbol *</label>
                  <Input
                    required
                    placeholder="e.g. BTCUSDT, ETHUSDT"
                    value={symbolInput}
                    onChange={(e) => setSymbolInput(e.target.value)}
                    className="font-mono uppercase text-sm"
                    id="input-alert-symbol"
                  />
                  <div className="flex flex-wrap gap-1 pt-1">
                    {PRESET_SYMBOLS.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setSymbolInput(s)}
                        className="text-xs px-2 py-0.5 rounded bg-muted hover:bg-muted/80 text-muted-foreground font-mono"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Trigger Condition *</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setConditionInput("above")}
                      className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
                        conditionInput === "above"
                          ? "bg-emerald-500/15 border-emerald-500 text-emerald-400"
                          : "bg-muted/40 text-muted-foreground"
                      }`}
                    >
                      <TrendingUp className="w-4 h-4" />
                      <span>Price Moves Above (≥)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setConditionInput("below")}
                      className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
                        conditionInput === "below"
                          ? "bg-rose-500/15 border-rose-500 text-rose-400"
                          : "bg-muted/40 text-muted-foreground"
                      }`}
                    >
                      <TrendingDown className="w-4 h-4" />
                      <span>Price Moves Below (≤)</span>
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Target Price ($ USD) *</label>
                  <Input
                    required
                    type="number"
                    step="any"
                    min="0.00000001"
                    placeholder="e.g. 70000"
                    value={targetPriceInput}
                    onChange={(e) => setTargetPriceInput(e.target.value)}
                    className="font-mono text-sm"
                    id="input-alert-target-price"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Notes (optional)</label>
                  <Input
                    placeholder="e.g. Breakout target or take profit level"
                    value={notesInput}
                    onChange={(e) => setNotesInput(e.target.value)}
                    className="text-sm"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={isCreating || !symbolInput.trim() || !targetPriceInput}>
                    {isCreating ? "Creating…" : "Set Alert"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Edit Alert Modal */}
      {editingAlert && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md shadow-2xl border bg-card">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg font-bold">Edit Alert: {editingAlert.symbol}</CardTitle>
                <CardDescription className="text-xs">Update threshold, condition, or notes.</CardDescription>
              </div>
              <button
                onClick={() => setEditingAlert(null)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSaveEdit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Condition</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setEditConditionInput("above")}
                      className={`p-2 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1 ${
                        editConditionInput === "above"
                          ? "bg-emerald-500/15 border-emerald-500 text-emerald-400"
                          : "bg-muted/40 text-muted-foreground"
                      }`}
                    >
                      <TrendingUp className="w-3.5 h-3.5" /> Above (≥)
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditConditionInput("below")}
                      className={`p-2 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1 ${
                        editConditionInput === "below"
                          ? "bg-rose-500/15 border-rose-500 text-rose-400"
                          : "bg-muted/40 text-muted-foreground"
                      }`}
                    >
                      <TrendingDown className="w-3.5 h-3.5" /> Below (≤)
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Target Price ($ USD)</label>
                  <Input
                    required
                    type="number"
                    step="any"
                    min="0.00000001"
                    value={editPriceInput}
                    onChange={(e) => setEditPriceInput(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Notes</label>
                  <Input
                    value={editNotesInput}
                    onChange={(e) => setEditNotesInput(e.target.value)}
                    className="text-sm"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => setEditingAlert(null)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={isUpdating}>
                    {isUpdating ? "Saving…" : "Save Changes"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </main>
  );
}
