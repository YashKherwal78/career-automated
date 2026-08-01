import { createFileRoute } from "@tanstack/react-router";
import { EmptyState } from "../../components/dashboard/CommonComponents";
import { Send } from "lucide-react";

export const Route = createFileRoute("/dashboard/applications")({
  component: ApplicationsPage,
});

function ApplicationsPage() {
  return (
    <div className="p-8 flex items-center justify-center min-h-[450px]">
      <EmptyState
        title="Coming Soon: Auto Apply Engine"
        description="We are currently benchmarking the eligibility filter and forms auto-filler models. This tab will soon track drafts, ready queues, and active application statuses."
        icon={Send}
      />
    </div>
  );
}
