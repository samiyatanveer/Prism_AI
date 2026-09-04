import { Suspense } from "react";
import AnalysesPageClient from "./client";

export const metadata = {
  title: "AI Analysis Reports",
  description: "Review saved AI trading intelligence, structured assessments, and technical indicator breakdowns.",
};

export default function AnalysesPage() {
  return (
    <Suspense>
      <AnalysesPageClient />
    </Suspense>
  );
}
