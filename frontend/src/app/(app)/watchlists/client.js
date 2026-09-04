"use client";

import { useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Plus,
  Trash2,
  ExternalLink,
  Edit2,
  Check,
  X,
  Layers,
  Sparkles,
  Info,
  LineChart,
} from "lucide-react";
import {
  useWatchlists,
  useWatchlist,
  useCreateWatchlist,
  useUpdateWatchlist,
  useDeleteWatchlist,
  useAddWatchlistItem,
  useRemoveWatchlistItem,
} from "@/hooks/use-watchlist";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const POPULAR_SUGGESTIONS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"];

export default function WatchlistsPageClient() {
  const { data: watchlists, isLoading: isWatchlistsLoading } = useWatchlists();
  const [selectedWatchlistId, setSelectedWatchlistId] = useState(null);

  // Fallback to first watchlist if none explicitly selected
  const activeId =
    selectedWatchlistId || (watchlists && watchlists.length > 0 ? watchlists[0].id : null);

  const { data: activeWatchlist, isLoading: isDetailLoading } = useWatchlist(activeId);

  // Mutations
  const { mutate: createWatchlist, isPending: isCreating } = useCreateWatchlist();
  const { mutate: updateWatchlist, isPending: isUpdating } = useUpdateWatchlist();
  const { mutate: deleteWatchlist, isPending: isDeleting } = useDeleteWatchlist();
  const { mutate: addItem, isPending: isAddingItem } = useAddWatchlistItem(activeId);
  const { mutate: removeItem, isPending: isRemovingItem } = useRemoveWatchlistItem(activeId);

  // Form states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWlName, setNewWlName] = useState("");
  const [newWlDesc, setNewWlDesc] = useState("");
  const [newWlSymbols, setNewWlSymbols] = useState("");

  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitleName, setEditTitleName] = useState("");
  const [editTitleDesc, setEditTitleDesc] = useState("");

  const [newSymbolInput, setNewSymbolInput] = useState("");
  const [newNotesInput, setNewNotesInput] = useState("");

  const handleCreateSubmit = (e) => {
    e.preventDefault();
    if (!newWlName.trim()) return;

    const initialSymbols = newWlSymbols
      .split(",")
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);

    createWatchlist(
      {
        name: newWlName.trim(),
        description: newWlDesc.trim() || undefined,
        symbols: initialSymbols,
      },
      {
        onSuccess: (created) => {
          setSelectedWatchlistId(created.id);
          setShowCreateModal(false);
          setNewWlName("");
          setNewWlDesc("");
          setNewWlSymbols("");
        },
      }
    );
  };

  const handleQuickCreateDefault = () => {
    createWatchlist(
      {
        name: "Primary Watchlist",
        description: "Core tracked assets",
        symbols: ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
      },
      {
        onSuccess: (created) => {
          setSelectedWatchlistId(created.id);
        },
      }
    );
  };

  const handleStartEdit = () => {
    if (!activeWatchlist) return;
    setEditTitleName(activeWatchlist.name);
    setEditTitleDesc(activeWatchlist.description || "");
    setIsEditingTitle(true);
  };

  const handleSaveEdit = () => {
    if (!editTitleName.trim()) return;
    updateWatchlist(
      {
        watchlistId: activeId,
        name: editTitleName.trim(),
        description: editTitleDesc.trim() || undefined,
      },
      {
        onSuccess: () => {
          setIsEditingTitle(false);
        },
      }
    );
  };

  const handleDeleteActiveWatchlist = () => {
    if (!activeId) return;
    if (confirm(`Are you sure you want to delete "${activeWatchlist?.name}"?`)) {
      deleteWatchlist(activeId, {
        onSuccess: () => {
          setSelectedWatchlistId(null);
        },
      });
    }
  };

  const handleAddItemSubmit = (e) => {
    e.preventDefault();
    const sym = newSymbolInput.trim().toUpperCase();
    if (!sym || isAddingItem) return;

    addItem(
      { symbol: sym, notes: newNotesInput.trim() || undefined },
      {
        onSuccess: () => {
          setNewSymbolInput("");
          setNewNotesInput("");
        },
      }
    );
  };

  const handleAddPreset = (sym) => {
    if (isAddingItem) return;
    addItem({ symbol: sym });
  };

  return (
    <main className="max-w-6xl mx-auto space-y-8 p-4 md:p-8">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">Watchlists</h1>
            {watchlists && watchlists.length > 0 && (
              <Badge variant="secondary" className="font-mono">
                {watchlists.length}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Monitor selected crypto assets with live exchange prices, 24h change, and instant chart access.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5"
            id="create-watchlist-btn"
          >
            <Plus className="w-4 h-4" />
            <span>New Watchlist</span>
          </Button>
        </div>
      </header>

      {/* Loading Skeleton */}
      {isWatchlistsLoading && (
        <div className="space-y-4">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      )}

      {/* Zero Watchlists Initial State */}
      {!isWatchlistsLoading && (!watchlists || watchlists.length === 0) && (
        <Card className="border-dashed bg-card/50">
          <CardContent className="p-12 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Layers className="w-6 h-6" />
            </div>
            <div className="space-y-1 max-w-md mx-auto">
              <h3 className="text-lg font-semibold">No watchlists yet</h3>
              <p className="text-sm text-muted-foreground">
                Create your first watchlist to monitor crypto pairs and get real-time price intelligence from your connected exchange.
              </p>
            </div>
            <div className="flex justify-center gap-3 pt-2">
              <Button onClick={handleQuickCreateDefault} disabled={isCreating} className="gap-2">
                <Sparkles className="w-4 h-4" />
                <span>Create default watchlist (BTC, ETH, SOL)</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Watchlists View */}
      {!isWatchlistsLoading && watchlists && watchlists.length > 0 && (
        <div className="space-y-6">
          {/* Watchlists Tab Selector */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b">
            {watchlists.map((wl) => {
              const isSelected = wl.id === activeId;
              return (
                <button
                  key={wl.id}
                  onClick={() => {
                    setSelectedWatchlistId(wl.id);
                    setIsEditingTitle(false);
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap flex items-center gap-2 ${
                    isSelected
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-card hover:bg-accent text-muted-foreground border"
                  }`}
                  id={`tab-watchlist-${wl.id}`}
                >
                  <span>{wl.name}</span>
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded-full ${
                      isSelected
                        ? "bg-primary-foreground/20 text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {wl.item_count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Active Watchlist Card */}
          {activeWatchlist && (
            <div className="space-y-6">
              {/* Watchlist Header / Metadata */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card/40 border p-5 rounded-xl">
                {isEditingTitle ? (
                  <div className="flex-1 space-y-2">
                    <Input
                      value={editTitleName}
                      onChange={(e) => setEditTitleName(e.target.value)}
                      placeholder="Watchlist name"
                      className="max-w-xs font-semibold"
                    />
                    <Input
                      value={editTitleDesc}
                      onChange={(e) => setEditTitleDesc(e.target.value)}
                      placeholder="Optional description"
                      className="max-w-md text-xs"
                    />
                    <div className="flex gap-2 pt-1">
                      <Button size="xs" onClick={handleSaveEdit} disabled={isUpdating} className="h-7 text-xs gap-1">
                        <Check className="w-3.5 h-3.5" /> Save
                      </Button>
                      <Button size="xs" variant="ghost" onClick={() => setIsEditingTitle(false)} className="h-7 text-xs">
                        <X className="w-3.5 h-3.5" /> Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold">{activeWatchlist.name}</h2>
                      <button
                        onClick={handleStartEdit}
                        className="text-muted-foreground hover:text-foreground p-1 rounded transition-colors"
                        title="Edit name/description"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    {activeWatchlist.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">{activeWatchlist.description}</p>
                    )}
                  </div>
                )}

                <div className="flex items-center gap-2 self-start md:self-auto">
                  <Button
                    variant="destructive"
                    size="xs"
                    onClick={handleDeleteActiveWatchlist}
                    disabled={isDeleting}
                    className="h-8 text-xs gap-1 opacity-80 hover:opacity-100"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Watchlist</span>
                  </Button>
                </div>
              </div>

              {/* Add Asset Form & Preset Chips */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold">Add Asset</CardTitle>
                  <CardDescription className="text-xs">
                    Add a symbol (e.g. BTCUSDT, ETH, SOL) to track its live price and candlestick trends.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <form onSubmit={handleAddItemSubmit} className="flex flex-col sm:flex-row gap-2">
                    <Input
                      placeholder="Symbol (e.g. BTCUSDT)"
                      value={newSymbolInput}
                      onChange={(e) => setNewSymbolInput(e.target.value)}
                      className="font-mono uppercase sm:max-w-xs text-sm"
                      id="input-add-symbol"
                    />
                    <Input
                      placeholder="Optional notes"
                      value={newNotesInput}
                      onChange={(e) => setNewNotesInput(e.target.value)}
                      className="sm:max-w-sm text-sm"
                    />
                    <Button type="submit" size="sm" disabled={isAddingItem || !newSymbolInput.trim()} className="gap-1">
                      <Plus className="w-4 h-4" />
                      <span>Add</span>
                    </Button>
                  </form>

                  {/* Preset chips */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-xs text-muted-foreground mr-1">Popular:</span>
                    {POPULAR_SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => handleAddPreset(s)}
                        disabled={isAddingItem}
                        className="text-xs px-2.5 py-1 rounded-md bg-secondary hover:bg-secondary/80 text-secondary-foreground font-mono transition-colors"
                      >
                        +{s}
                      </button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Items Table / Cards */}
              {isDetailLoading ? (
                <Skeleton className="h-48 w-full rounded-xl" />
              ) : activeWatchlist.items.length === 0 ? (
                <div className="rounded-xl border border-dashed p-10 text-center space-y-2 bg-card/30">
                  <p className="text-sm text-muted-foreground">
                    This watchlist is empty. Add a symbol above to start tracking.
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border bg-card overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-muted/40 text-xs text-muted-foreground border-b uppercase tracking-wider">
                        <tr>
                          <th className="py-3 px-4 font-semibold">Asset</th>
                          <th className="py-3 px-4 font-semibold">Price</th>
                          <th className="py-3 px-4 font-semibold">24h Change</th>
                          <th className="py-3 px-4 font-semibold hidden sm:table-cell">24h High / Low</th>
                          <th className="py-3 px-4 font-semibold hidden md:table-cell">24h Volume</th>
                          <th className="py-3 px-4 font-semibold hidden lg:table-cell">Notes</th>
                          <th className="py-3 px-4 font-semibold text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        {activeWatchlist.items.map((item) => {
                          const hasPrice = item.price !== null && item.price !== undefined;
                          const isPositive = item.change_24h_pct >= 0;

                          return (
                            <tr key={item.id} className="hover:bg-accent/40 transition-colors">
                              {/* Asset Symbol */}
                              <td className="py-3.5 px-4">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono font-bold text-foreground text-sm">
                                    {item.symbol}
                                  </span>
                                </div>
                              </td>

                              {/* Price */}
                              <td className="py-3.5 px-4 font-mono">
                                {hasPrice ? (
                                  <span className="font-semibold text-foreground">
                                    ${Number(item.price).toLocaleString(undefined, {
                                      minimumFractionDigits: 2,
                                      maximumFractionDigits: 4,
                                    })}
                                  </span>
                                ) : (
                                  <span className="text-xs text-muted-foreground italic">—</span>
                                )}
                              </td>

                              {/* 24h Change */}
                              <td className="py-3.5 px-4 font-mono">
                                {item.change_24h_pct !== null && item.change_24h_pct !== undefined ? (
                                  <div
                                    className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded ${
                                      isPositive
                                        ? "text-emerald-500 bg-emerald-500/10"
                                        : "text-rose-500 bg-rose-500/10"
                                    }`}
                                  >
                                    {isPositive ? (
                                      <TrendingUp className="w-3.5 h-3.5" />
                                    ) : (
                                      <TrendingDown className="w-3.5 h-3.5" />
                                    )}
                                    <span>
                                      {isPositive ? "+" : ""}
                                      {Number(item.change_24h_pct).toFixed(2)}%
                                    </span>
                                  </div>
                                ) : (
                                  <span className="text-xs text-muted-foreground italic">—</span>
                                )}
                              </td>

                              {/* 24h High / Low */}
                              <td className="py-3.5 px-4 hidden sm:table-cell text-xs font-mono text-muted-foreground">
                                {item.high_24h && item.low_24h ? (
                                  <span>
                                    ${Number(item.high_24h).toLocaleString()} / ${Number(item.low_24h).toLocaleString()}
                                  </span>
                                ) : (
                                  <span>—</span>
                                )}
                              </td>

                              {/* Volume */}
                              <td className="py-3.5 px-4 hidden md:table-cell text-xs font-mono text-muted-foreground">
                                {item.volume_24h ? (
                                  <span>{Number(item.volume_24h).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                                ) : (
                                  <span>—</span>
                                )}
                              </td>

                              {/* Notes */}
                              <td className="py-3.5 px-4 hidden lg:table-cell text-xs text-muted-foreground max-w-xs truncate">
                                {item.notes || "—"}
                              </td>

                              {/* Actions */}
                              <td className="py-3.5 px-4 text-right">
                                <div className="flex items-center justify-end gap-2">
                                  <Button asChild variant="ghost" size="xs" className="h-8 px-2 text-xs gap-1">
                                    <Link href={`/market/${item.symbol}`}>
                                      <LineChart className="w-3.5 h-3.5 text-primary" />
                                      <span className="hidden sm:inline">Chart</span>
                                    </Link>
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="xs"
                                    onClick={() => removeItem(item.id)}
                                    disabled={isRemovingItem}
                                    className="h-8 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                                    title="Remove from watchlist"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Create Watchlist Modal / Overlay */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md shadow-2xl border bg-card">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg font-bold">Create Watchlist</CardTitle>
                <CardDescription className="text-xs">Group and monitor your custom asset selections.</CardDescription>
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
                  <label className="text-xs font-semibold">Name *</label>
                  <Input
                    required
                    placeholder="e.g. DeFi Core, Metaverse, High Beta"
                    value={newWlName}
                    onChange={(e) => setNewWlName(e.target.value)}
                    id="new-watchlist-name-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Description (optional)</label>
                  <Input
                    placeholder="e.g. Top Layer 1 protocols to watch this quarter"
                    value={newWlDesc}
                    onChange={(e) => setNewWlDesc(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Initial Symbols (comma separated)</label>
                  <Input
                    placeholder="e.g. BTCUSDT, ETHUSDT, SOLUSDT"
                    value={newWlSymbols}
                    onChange={(e) => setNewWlSymbols(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setShowCreateModal(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={isCreating || !newWlName.trim()}>
                    {isCreating ? "Creating…" : "Create Watchlist"}
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
