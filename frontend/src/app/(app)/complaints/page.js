import { Suspense } from "react";
import ComplaintsPageClient from "./client";

export const metadata = {
  title: "Support & Complaint Portal",
  description: "Submit support tickets, report exchange or market issues, and track resolutions with staff responses.",
};

export default function ComplaintsPage() {
  return (
    <Suspense>
      <ComplaintsPageClient />
    </Suspense>
  );
}
