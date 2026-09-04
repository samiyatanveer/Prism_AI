import { Suspense } from "react";
import AlertsPageClient from "./client";

export const metadata = {
  title: "Price Alerts",
  description: "Set and track custom price and condition threshold alerts evaluated on-demand against live market data.",
};

export default function AlertsPage() {
  return (
    <Suspense>
      <AlertsPageClient />
    </Suspense>
  );
}
