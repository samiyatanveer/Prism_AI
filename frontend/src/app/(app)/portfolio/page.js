import { Suspense } from "react";
import PortfolioPageClient from "./client";

export const metadata = {
  title: "Portfolio",
  description: "Live portfolio holdings from your connected exchange.",
};

export default function PortfolioPage() {
  return (
    <Suspense>
      <PortfolioPageClient />
    </Suspense>
  );
}
