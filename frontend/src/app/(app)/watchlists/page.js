import { Suspense } from "react";
import WatchlistsPageClient from "./client";

export const metadata = {
  title: "Watchlists",
  description: "Monitor crypto assets with real-time exchange prices, 24h performance, and technical chart access.",
};

export default function WatchlistsPage() {
  return (
    <Suspense>
      <WatchlistsPageClient />
    </Suspense>
  );
}
