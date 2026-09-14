import EmptyState from "@/components/EmptyState";

export default function AdminQueuePage() {
  return (
    <div className="flex h-full items-center justify-center px-6 py-16">
      <EmptyState title="Select a ticket" description="Choose a ticket from the queue to see its details." />
    </div>
  );
}
