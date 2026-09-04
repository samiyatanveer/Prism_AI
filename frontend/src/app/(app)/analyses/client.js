"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Brain,
  Sparkles,
  TrendingUp,
  TrendingDown,
  MinusCircle,
  AlertCircle,
  LineChart,
  Trash2,
  Plus,
  X,
  Clock,
  Shield,
  Target,
  ArrowDownRight,
  ArrowUpRight,
  Layers,
  ChevronRight,
} from "lucide-react";
import {
  useAnalyses,
  useAnalysisSummary,
  useGenerateAnalysis,
  useDeleteAnalysis,
} from "@/hooks/use-analyses";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const PRESET_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"];
const TIMEFRAMES = ["1D", "4H", "1H", "15M"];

export default function AnalysesPageClient() {
  const [selectedAssessment, setSelectedAssessment] = useState("ALL");
  const { data: reports, isLoading } = useAnalyses({
    assessment: selectedAssessment === "ALL" ? undefined : selectedAssessment,
  });
  const { data: summary } = useAnalysisSummary();

  const { mutate: generateAnalysis, isPending: isGenerating } = useGenerateAnalysis();
  const { mutate: deleteAnalysis, isPending: isDeleting } = useDeleteAnalysis();

  // Create/generate modal state
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [symbolInput, setSymbolInput] = useState("");
  const [timeframeInput, setTimeframeInput] = useState("1D");
  const [notesInput, setNotesInput] = useState("");

  // Detailed view modal state
  const [activeDetailReport, setActiveDetailReport] = useState(null);

  const handleGenerateSubmit = (e) => {
    e.preventDefault();
    const sym = symbolInput.trim().toUpperCase();
    if (!sym) return;

    generateAnalysis(
      {
        symbol: sym,
        timeframe: timeframeInput,
        user_notes: notesInput.trim() || undefined,
      },
      {
        onSuccess: (data) => {
          setShowGenerateModal(false);
          setSymbolInput("");
          setNotesInput("");
          setActiveDetailReport(data);
        },
      }
    );
  };

  const handleDelete = (reportId, symbol) => {
    if (confirm(`Delete analysis report for ${symbol}?`)) {
      deleteAnalysis(reportId, {
        onSuccess: () => {
          if (activeDetailReport?.id === reportId) {
            setActiveDetailReport(null);
          }
        },
      });
    }
  };

  const getAssessmentStyle = (assessment) => {
    switch (assessment) {
      case "Buy Gradually":
        return {
          badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
          icon: <TrendingUp className="w-3.5 h-3.5" />,
          cardBorder: "border-emerald-500/30",
        };
      case "Hold":
        return {
          badge: "bg-sky-500/15 text-sky-400 border-sky-500/30",
          icon: <MinusCircle className="w-3.5 h-3.5" />,
          cardBorder: "border-sky-500/30",
        };
      case "Consider Selling":
        return {
          badge: "bg-rose-500/15 text-rose-400 border-rose-500/30",
          icon: <TrendingDown className="w-3.5 h-3.5" />,
          cardBorder: "border-rose-500/30",
        };
      default:
        return {
          badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
          icon: <AlertCircle className="w-3.5 h-3.5" />,
          cardBorder: "border-amber-500/30",
        };
    }
  };

  const getRiskBadge = (risk) => {
    switch (risk) {
      case "Low":
        return <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-400 border-emerald-500/30">Risk: Low</Badge>;
      case "High":
        return <Badge variant="outline" className="text-xs bg-rose-500/10 text-rose-400 border-rose-500/30">Risk: High</Badge>;
      default:
        return <Badge variant="outline" className="text-xs bg-amber-500/10 text-amber-400 border-amber-500/30">Risk: Moderate</Badge>;
    }
  };

  return (
    <main className="max-w-6xl mx-auto space-y-8 p-4 md:p-8">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">AI Analysis Reports</h1>
            {summary && summary.total > 0 && (
              <Badge variant="secondary" className="font-mono">
                {summary.total}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Structured decision-support intelligence, standardized assessments, and technical indicator evaluations.
          </p>
        </div>

        <div>
          <Button
            size="sm"
            onClick={() => setShowGenerateModal(true)}
            className="flex items-center gap-1.5"
            id="generate-analysis-btn"
          >
            <Sparkles className="w-4 h-4" />
            <span>New AI Analysis</span>
          </Button>
        </div>
      </header>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-4 bg-card/60">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Total Reports</span>
            <Brain className="w-4 h-4 text-muted-foreground" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1">{summary?.total ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60 border-emerald-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-400">Buy Gradually</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-emerald-400">{summary?.buy_gradually ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60 border-sky-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs text-sky-400">Hold</span>
            <MinusCircle className="w-4 h-4 text-sky-400" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-sky-400">{summary?.hold ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60 border-rose-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs text-rose-400">Consider Selling</span>
            <TrendingDown className="w-4 h-4 text-rose-400" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-rose-400">{summary?.consider_selling ?? 0}</p>
        </Card>
      </div>

      {/* Assessment Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b pb-2">
        {["ALL", "Buy Gradually", "Hold", "Consider Selling", "Insufficient Context"].map((tab) => (
          <button
            key={tab}
            onClick={() => setSelectedAssessment(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
              selectedAssessment === tab
                ? "bg-primary text-primary-foreground"
                : "bg-card hover:bg-accent text-muted-foreground border"
            }`}
            id={`filter-${tab.toLowerCase().replace(/\s+/g, "-")}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-44 w-full rounded-xl" />
          <Skeleton className="h-44 w-full rounded-xl" />
          <Skeleton className="h-44 w-full rounded-xl" />
          <Skeleton className="h-44 w-full rounded-xl" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && reports && reports.length === 0 && (
        <Card className="border-dashed bg-card/40">
          <CardContent className="p-12 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Brain className="w-6 h-6" />
            </div>
            <div className="space-y-1 max-w-sm mx-auto">
              <h3 className="text-lg font-semibold">No analysis reports found</h3>
              <p className="text-xs text-muted-foreground">
                {selectedAssessment === "ALL"
                  ? "Generate a comprehensive AI technical analysis report for any crypto asset."
                  : `No '${selectedAssessment}' reports saved yet.`}
              </p>
            </div>
            <Button size="sm" onClick={() => setShowGenerateModal(true)} className="gap-1.5">
              <Sparkles className="w-4 h-4" />
              <span>Generate AI Analysis</span>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Reports Grid */}
      {!isLoading && reports && reports.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reports.map((report) => {
            const style = getAssessmentStyle(report.assessment);

            return (
              <Card
                key={report.id}
                className={`transition-all hover:border-primary/50 bg-card/70 flex flex-col justify-between cursor-pointer ${style.cardBorder}`}
                onClick={() => setActiveDetailReport(report)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-lg text-foreground">{report.symbol}</span>
                        <Badge variant="secondary" className="font-mono text-xs">
                          {report.timeframe}
                        </Badge>
                        {getRiskBadge(report.risk_level)}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(report.created_at).toLocaleDateString()} {new Date(report.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </p>
                    </div>

                    <div className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-md border ${style.badge}`}>
                      {style.icon}
                      <span>{report.assessment}</span>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-3 pb-4">
                  {/* Market Price & Summary */}
                  <div>
                    <div className="text-xs text-muted-foreground font-mono">
                      Price at analysis: <span className="font-semibold text-foreground">${Number(report.market_price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}</span>
                    </div>
                    <p className="text-xs text-foreground/90 mt-1.5 line-clamp-2 leading-relaxed">
                      {report.summary}
                    </p>
                  </div>

                  {/* Key Price Levels Preview */}
                  {report.key_price_levels && (
                    <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-xs bg-muted/30 p-2 rounded-lg">
                      {report.key_price_levels.support && (
                        <div>
                          <span className="text-muted-foreground text-[10px] uppercase">Support:</span>{" "}
                          <span className="font-medium">${Number(report.key_price_levels.support).toLocaleString()}</span>
                        </div>
                      )}
                      {report.key_price_levels.resistance && (
                        <div>
                          <span className="text-muted-foreground text-[10px] uppercase">Resistance:</span>{" "}
                          <span className="font-medium">${Number(report.key_price_levels.resistance).toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Action Bar */}
                  <div className="flex items-center justify-between pt-2 border-t text-xs">
                    <Button
                      asChild
                      variant="ghost"
                      size="xs"
                      className="h-7 px-2 text-xs gap-1 text-primary"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Link href={`/market/${report.symbol}`}>
                        <LineChart className="w-3.5 h-3.5" />
                        <span>Chart</span>
                      </Link>
                    </Button>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(report.id, report.symbol);
                        }}
                        disabled={isDeleting}
                        className="h-7 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                      <span className="text-muted-foreground flex items-center text-xs">
                        View Report <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Generate AI Analysis Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md shadow-2xl border bg-card">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg font-bold flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <span>Run AI Technical Analysis</span>
                </CardTitle>
                <CardDescription className="text-xs">
                  Retrieves live quotes and candlestick indicators for a comprehensive assessment report.
                </CardDescription>
              </div>
              <button
                onClick={() => setShowGenerateModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleGenerateSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Asset Symbol *</label>
                  <Input
                    required
                    placeholder="e.g. BTCUSDT, ETHUSDT, SOLUSDT"
                    value={symbolInput}
                    onChange={(e) => setSymbolInput(e.target.value)}
                    className="font-mono uppercase text-sm"
                    id="input-analysis-symbol"
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
                  <label className="text-xs font-semibold">Chart Timeframe</label>
                  <div className="grid grid-cols-4 gap-2">
                    {TIMEFRAMES.map((tf) => (
                      <button
                        key={tf}
                        type="button"
                        onClick={() => setTimeframeInput(tf)}
                        className={`p-2 rounded-lg border text-xs font-semibold transition-colors ${
                          timeframeInput === tf
                            ? "bg-primary text-primary-foreground border-primary"
                            : "bg-muted/40 text-muted-foreground"
                        }`}
                      >
                        {tf}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Trade Notes / Context (optional)</label>
                  <Input
                    placeholder="e.g. Evaluating entry zone for swing position"
                    value={notesInput}
                    onChange={(e) => setNotesInput(e.target.value)}
                    className="text-sm"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowGenerateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={isGenerating || !symbolInput.trim()}>
                    {isGenerating ? (
                      <span className="flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 animate-spin" />
                        <span>Analyzing…</span>
                      </span>
                    ) : (
                      "Generate Report"
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Detailed Analysis Report Modal */}
      {activeDetailReport && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <Card className="w-full max-w-2xl shadow-2xl border bg-card my-8">
            <CardHeader className="flex flex-row items-start justify-between pb-3 border-b">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold font-mono">{activeDetailReport.symbol}</span>
                  <Badge variant="secondary" className="font-mono text-xs">
                    {activeDetailReport.timeframe}
                  </Badge>
                  {getRiskBadge(activeDetailReport.risk_level)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Report generated on {new Date(activeDetailReport.created_at).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <div
                  className={`inline-flex items-center gap-1 text-sm font-semibold px-3 py-1 rounded-md border ${
                    getAssessmentStyle(activeDetailReport.assessment).badge
                  }`}
                >
                  {getAssessmentStyle(activeDetailReport.assessment).icon}
                  <span>{activeDetailReport.assessment}</span>
                </div>
                <button
                  onClick={() => setActiveDetailReport(null)}
                  className="text-muted-foreground hover:text-foreground p-1 rounded-md"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </CardHeader>

            <CardContent className="space-y-6 pt-4">
              {/* Market Reference */}
              <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg font-mono text-sm">
                <span className="text-muted-foreground">Market Price at Analysis:</span>
                <span className="font-bold text-foreground">
                  ${Number(activeDetailReport.market_price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                </span>
              </div>

              {/* Executive Summary */}
              <div className="space-y-1.5">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Executive Summary
                </h4>
                <p className="text-sm font-medium leading-relaxed bg-primary/5 p-3 rounded-lg border border-primary/20">
                  {activeDetailReport.summary}
                </p>
              </div>

              {/* Key Price Levels */}
              {activeDetailReport.key_price_levels && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Target className="w-3.5 h-3.5 text-primary" />
                    <span>Key Price Levels</span>
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono">
                    <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center">
                      <span className="text-[10px] uppercase text-emerald-400 block">Support</span>
                      <span className="text-sm font-bold text-emerald-400">
                        {activeDetailReport.key_price_levels.support
                          ? `$${Number(activeDetailReport.key_price_levels.support).toLocaleString()}`
                          : "—"}
                      </span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-center">
                      <span className="text-[10px] uppercase text-rose-400 block">Resistance</span>
                      <span className="text-sm font-bold text-rose-400">
                        {activeDetailReport.key_price_levels.resistance
                          ? `$${Number(activeDetailReport.key_price_levels.resistance).toLocaleString()}`
                          : "—"}
                      </span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-center">
                      <span className="text-[10px] uppercase text-sky-400 block">Target</span>
                      <span className="text-sm font-bold text-sky-400">
                        {activeDetailReport.key_price_levels.target
                          ? `$${Number(activeDetailReport.key_price_levels.target).toLocaleString()}`
                          : "—"}
                      </span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-center">
                      <span className="text-[10px] uppercase text-amber-400 block">Stop Loss</span>
                      <span className="text-sm font-bold text-amber-400">
                        {activeDetailReport.key_price_levels.stop_loss
                          ? `$${Number(activeDetailReport.key_price_levels.stop_loss).toLocaleString()}`
                          : "—"}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Technical Reasoning */}
              <div className="space-y-1.5">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Technical Reasoning & Structure
                </h4>
                <div className="text-xs text-foreground/90 leading-relaxed bg-muted/20 p-3.5 rounded-lg border whitespace-pre-wrap">
                  {activeDetailReport.reasoning}
                </div>
              </div>

              {/* Technical Indicators Snapshot */}
              {activeDetailReport.technical_indicators && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-primary" />
                    <span>Indicator Snapshot</span>
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono bg-card p-3 rounded-lg border">
                    {activeDetailReport.technical_indicators.trend && (
                      <div>
                        <span className="text-muted-foreground text-[10px] uppercase block">Trend:</span>
                        <span className="font-semibold">{activeDetailReport.technical_indicators.trend}</span>
                      </div>
                    )}
                    {activeDetailReport.technical_indicators.rsi_14 !== undefined && (
                      <div>
                        <span className="text-muted-foreground text-[10px] uppercase block">RSI (14):</span>
                        <span className="font-semibold">{activeDetailReport.technical_indicators.rsi_14}</span>
                      </div>
                    )}
                    {activeDetailReport.technical_indicators.change_24h_pct !== undefined && (
                      <div>
                        <span className="text-muted-foreground text-[10px] uppercase block">24h Change:</span>
                        <span className={activeDetailReport.technical_indicators.change_24h_pct >= 0 ? "text-emerald-400 font-semibold" : "text-rose-400 font-semibold"}>
                          {activeDetailReport.technical_indicators.change_24h_pct >= 0 ? "+" : ""}
                          {Number(activeDetailReport.technical_indicators.change_24h_pct).toFixed(2)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* User Notes */}
              {activeDetailReport.user_notes && (
                <div className="text-xs text-muted-foreground italic border-t pt-2">
                  Note: {activeDetailReport.user_notes}
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center justify-between pt-4 border-t">
                <Button asChild variant="outline" size="sm" className="gap-1.5">
                  <Link href={`/market/${activeDetailReport.symbol}`}>
                    <LineChart className="w-4 h-4 text-primary" />
                    <span>Open Live Chart</span>
                  </Link>
                </Button>

                <div className="flex items-center gap-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDelete(activeDetailReport.id, activeDetailReport.symbol)}
                  >
                    Delete Report
                  </Button>
                  <Button variant="default" size="sm" onClick={() => setActiveDetailReport(null)}>
                    Close
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </main>
  );
}
