"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import FilterRail, { type QueueFilters } from "@/components/FilterRail";
import StatusBadge from "@/components/StatusBadge";
import PriorityMark from "@/components/PriorityMark";
import CategoryTag from "@/components/CategoryTag";
import SkeletonRow from "@/components/SkeletonRow";
import EmptyState from "@/components/EmptyState";
import { adminListTickets } from "@/lib/api";
import type { TicketAdminListItem } from "@/lib/types";
import { formatAge } from "@/lib/format";

const PAGE_SIZE = 20;

export default function QueueLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const match = pathname.match(/^\/admin\/tickets\/(.+)$/);
  const selectedReference = match ? decodeURIComponent(match[1]) : null;

  const [filters, setFilters] = useState<QueueFilters>({ status: "", priority: "", category: "" });
  const [search, setSearch] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [page, setPage] = useState(1);
  const [tickets, setTickets] = useState<TicketAdminListItem[] | null>(null);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const result = await adminListTickets({
      status: filters.status || undefined,
      priority: filters.priority || undefined,
      category: filters.category || undefined,
      search: search || undefined,
      ordering,
      page,
    });
    if (result.ok) {
      setTickets(result.data.results);
      setCount(result.data.count);
    } else {
      setTickets([]);
      setCount(0);
    }
    setLoading(false);
  }, [filters, search, ordering, page]);

  useEffect(() => {
    load();
  }, [load, pathname]);

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const hasActiveFilters = Boolean(filters.status || filters.priority || filters.category || search);

  function clearAll() {
    setFilters({ status: "", priority: "", category: "" });
    setSearch("");
    setPage(1);
  }

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col sm:flex-row">
      <aside className="rule w-full shrink-0 px-4 py-6 sm:w-[244px] sm:border-b-0 sm:border-r xs:px-6">
        <FilterRail
          filters={filters}
          onChange={(next) => {
            setFilters(next);
            setPage(1);
          }}
          onClear={clearAll}
        />
      </aside>

      <section
        className={`w-full shrink-0 flex-col border-rule sm:w-[320px] sm:border-r ${
          selectedReference ? "hidden lg:flex" : "flex"
        }`}
      >
        <div className="rule flex flex-col gap-3 p-4">
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="Search tickets"
            aria-label="Search tickets"
            className="w-full border-0 border-b border-rule bg-transparent py-1.5 text-sm focus:border-oxide focus:outline-none"
          />
          <select
            aria-label="Sort by"
            value={ordering}
            onChange={(event) => setOrdering(event.target.value)}
            className="w-full border-0 border-b border-rule bg-transparent py-1.5 text-sm focus:border-oxide focus:outline-none"
          >
            <option value="-created_at">Newest</option>
            <option value="created_at">Oldest</option>
            <option value="-priority">Priority (high first)</option>
            <option value="status">Status</option>
          </select>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex flex-col gap-3 p-4">
              {Array.from({ length: 6 }).map((_, index) => (
                <SkeletonRow key={index} />
              ))}
            </div>
          ) : tickets && tickets.length === 0 ? (
            <EmptyState
              title={hasActiveFilters ? "No tickets match these filters." : "No tickets yet."}
              action={
                hasActiveFilters ? (
                  <button type="button" onClick={clearAll} className="eyebrow underline decoration-rule">
                    Clear all filters
                  </button>
                ) : undefined
              }
            />
          ) : (
            <ul>
              {tickets?.map((ticket) => {
                const selected = ticket.reference === selectedReference;
                return (
                  <li key={ticket.reference}>
                    <Link
                      href={`/admin/tickets/${ticket.reference}`}
                      className={`rule block px-4 py-3 border-l-[3px] ${
                        selected ? "border-l-oxide bg-sel-bg" : "border-l-transparent"
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <PriorityMark priority={ticket.priority} />
                        <span className="text-xs text-faint">{formatAge(ticket.created_at)}</span>
                      </div>
                      <div className={`reference-code text-sm ${selected ? "text-oxide" : ""}`}>
                        {ticket.reference}
                      </div>
                      <div className={`truncate text-sm ${selected ? "font-medium" : ""}`}>{ticket.subject}</div>
                      <div className="mt-1 flex items-center justify-between gap-2 xs:flex hidden">
                        <CategoryTag category={ticket.category} />
                        <StatusBadge status={ticket.status} />
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {totalPages > 1 && (
          <div className="rule flex items-center justify-between border-t p-3 text-sm">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="eyebrow disabled:opacity-40"
            >
              Prev
            </button>
            <span className="text-faint">
              {page} / {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="eyebrow disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </section>

      <section className={`min-w-0 flex-1 ${selectedReference ? "block" : "hidden lg:block"}`}>{children}</section>
    </div>
  );
}
