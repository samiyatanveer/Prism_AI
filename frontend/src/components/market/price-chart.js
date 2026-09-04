"use client";

/**
 * TradingView Lightweight Charts candlestick chart wrapper.
 * Renders only on the client — no SSR.
 */

import { useEffect, useRef } from "react";

export default function PriceChart({ candles, height = 380 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let chart;
    let observer;
    let cancelled = false;

    (async () => {
      const { createChart, CandlestickSeries, ColorType, CrosshairMode } = await import(
        "lightweight-charts"
      );

      if (cancelled || !containerRef.current) return;

      chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height,
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "#94a3b8",
        },
        grid: {
          vertLines: { color: "rgba(148, 163, 184, 0.12)" },
          horzLines: { color: "rgba(148, 163, 184, 0.12)" },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: "rgba(148, 163, 184, 0.18)" },
        timeScale: {
          borderColor: "rgba(148, 163, 184, 0.18)",
          timeVisible: true,
          secondsVisible: false,
        },
      });

      chartRef.current = chart;

      const series = chart.addSeries(CandlestickSeries, {
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderUpColor: "#22c55e",
        borderDownColor: "#ef4444",
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });

      seriesRef.current = series;

      if (candles && candles.length > 0) {
        const formatted = candles.map((c) => ({
          time: Math.floor(new Date(c.open_time).getTime() / 1000),
          open: parseFloat(c.open),
          high: parseFloat(c.high),
          low: parseFloat(c.low),
          close: parseFloat(c.close),
        }));
        series.setData(formatted);
        chart.timeScale().fitContent();
      }

      // Resize observer
      observer = new ResizeObserver(() => {
        if (containerRef.current) {
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      observer.observe(containerRef.current);

    })();

    return () => {
      cancelled = true;
      observer?.disconnect();
      chart?.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update data without recreating the chart
  useEffect(() => {
    if (!seriesRef.current || !candles || candles.length === 0) return;
    const formatted = candles.map((c) => ({
      time: Math.floor(new Date(c.open_time).getTime() / 1000),
      open: parseFloat(c.open),
      high: parseFloat(c.high),
      low: parseFloat(c.low),
      close: parseFloat(c.close),
    }));
    seriesRef.current.setData(formatted);
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="w-full rounded-xl overflow-hidden border bg-card"
    />
  );
}
