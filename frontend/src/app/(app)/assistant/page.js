import { Suspense } from "react";
import AssistantPageClient from "./client";

export const metadata = {
  title: "AI Assistant",
  description: "Natural-language crypto portfolio intelligence and market analysis.",
};

export default function AssistantPage() {
  return (
    <Suspense>
      <AssistantPageClient />
    </Suspense>
  );
}
