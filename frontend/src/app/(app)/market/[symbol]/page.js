import { Suspense } from "react";
import MarketPageClient from "./client";

export const metadata = {
  title: "Market",
  description: "Live price and OHLCV candlestick chart.",
};

// In Next.js 15+, dynamic route params are a Promise and must be awaited.
export default async function MarketPage({ params }) {
  const { symbol } = await params;
  return (
    <Suspense>
      <MarketPageClient symbol={symbol} />
    </Suspense>
  );
}
