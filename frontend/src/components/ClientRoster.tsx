"use client";

/**
 * Client Roster: every client this trainer has, in its own scrollable table.
 * Search by name, filter by goal or urgency, sort by last active, and copy a client's link.
 */

import React, { useState } from "react";
import { Check, Copy, Search } from "lucide-react";
import { URGENCY_STYLES } from "@/components/TriageFeed";
import type { RosterClient, Urgency } from "@/types";

interface ClientRosterProps {
  clients: RosterClient[];
  /** Returns the client's private link, creating one if they don't have one yet. */
  getClientLink: (client: RosterClient) => Promise<string>;
}

const lastActiveLabel = (client: RosterClient) =>
  client.last_active_at
    ? new Date(client.last_active_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })
    : "Never logged";

export default function ClientRoster({ clients, getClientLink }: ClientRosterProps) {
  const [search, setSearch] = useState("");
  const [goalFilter, setGoalFilter] = useState("all");
  const [urgencyFilter, setUrgencyFilter] = useState<"all" | Urgency>("all");
  const [newestFirst, setNewestFirst] = useState(true);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);

  const goals = Array.from(new Set(clients.map((client) => client.primary_goal).filter(Boolean))) as string[];

  const visible = clients
    .filter((client) => client.full_name.toLowerCase().includes(search.toLowerCase()))
    .filter((client) => goalFilter === "all" || client.primary_goal === goalFilter)
    .filter((client) => urgencyFilter === "all" || client.urgency === urgencyFilter)
    .sort((a, b) => {
      const aTime = a.last_active_at ? Date.parse(a.last_active_at) : 0;
      const bTime = b.last_active_at ? Date.parse(b.last_active_at) : 0;
      return newestFirst ? bTime - aTime : aTime - bTime;
    });

  const copyLink = async (client: RosterClient) => {
    setLinkError(null);
    try {
      await navigator.clipboard.writeText(await getClientLink(client));
      setCopiedId(client.client_id);
    } catch {
      setLinkError("We couldn't copy that link. Try again.");
    }
  };

  const control =
    "h-10 px-3 bg-ground border border-hairline rounded-xl text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink";

  return (
    <section className="space-y-3" aria-label="Client roster">
      <h2 className="font-display text-lg font-medium text-ink">Clients ({clients.length})</h2>

      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-48">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name..."
            aria-label="Search roster by name"
            className={`${control} w-full pl-9 placeholder-muted`}
          />
        </div>
        <select value={goalFilter} onChange={(e) => setGoalFilter(e.target.value)} aria-label="Filter by goal" className={control}>
          <option value="all">All goals</option>
          {goals.map((goal) => (
            <option key={goal} value={goal}>
              {goal}
            </option>
          ))}
        </select>
        <select
          value={urgencyFilter}
          onChange={(e) => setUrgencyFilter(e.target.value as "all" | Urgency)}
          aria-label="Filter by urgency"
          className={control}
        >
          <option value="all">All urgency</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="routine">Routine</option>
        </select>
        <button
          type="button"
          onClick={() => setNewestFirst((current) => !current)}
          className={`${control} font-semibold text-ink-2 hover:bg-hairline`}
        >
          Last active: {newestFirst ? "newest" : "oldest"}
        </button>
      </div>

      {linkError && <p className="text-sm text-warn" role="alert">{linkError}</p>}

      <div className="scrollable-container max-h-96 overflow-x-auto border border-hairline rounded-2xl">
        <table className="w-full min-w-[34rem] text-sm text-left">
          <thead className="sticky top-0 bg-surface text-xs font-semibold text-muted">
            <tr>
              <th className="px-3 py-2.5">Client</th>
              <th className="px-3 py-2.5">Goal</th>
              <th className="px-3 py-2.5">Last active</th>
              <th className="px-3 py-2.5">Urgency</th>
              <th className="px-3 py-2.5">Link</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((client) => {
              const style = URGENCY_STYLES[client.urgency];
              return (
                <tr key={client.client_id} className="border-t border-hairline">
                  <td className="px-3 py-2 font-semibold text-ink">{client.full_name}</td>
                  <td className="px-3 py-2 text-ink-2">{client.primary_goal ?? "Not set"}</td>
                  <td className="px-3 py-2 text-ink-2">{lastActiveLabel(client)}</td>
                  <td className="px-3 py-2">
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${style.badge}`}>{style.label}</span>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => copyLink(client)}
                      aria-label={`Copy link for ${client.full_name}`}
                      className="touch-target px-3 border border-hairline hover:bg-hairline text-ink-2 rounded-full text-xs font-semibold flex items-center gap-1"
                    >
                      {copiedId === client.client_id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedId === client.client_id ? "Copied" : "Copy"}</span>
                    </button>
                  </td>
                </tr>
              );
            })}
            {visible.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-ink-2">
                  No clients match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
