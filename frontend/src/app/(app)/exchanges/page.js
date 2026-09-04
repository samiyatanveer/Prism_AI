import { Suspense } from "react";
import ExchangesPageClient from "./client";

export const metadata = {
  title: "Exchanges",
  description: "Connect and manage your exchange accounts.",
};

export default function ExchangesPage() {
  return (
    <Suspense>
      <ExchangesPageClient />
    </Suspense>
  );
}
