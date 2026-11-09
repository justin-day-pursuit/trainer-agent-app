"use client";

/**
 * Trainer Progression Dashboard & Administrative Portal.
 * 
 * Features:
 * 1. Dedicated scrollable triage container with search, filter, and sort controls.
 * 2. Progression approval cards with deterministic weight change indicators (+5 lbs).
 * 3. AI Safety Alert badges cross-referencing intake injuries against recent pain logs.
 * 4. Human-in-the-Loop Checkpoint: 1-click "Approve" button activating the weekly program.
 * 5. Unique client session link generation modal.
 * 6. Model & Agent observability indicators.
 */

import React, { useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Search,
  Filter,
  ArrowUpDown,
  CheckCircle2,
  AlertTriangle,
  Send,
  Link as LinkIcon,
  Plus,
  TrendingUp,
  Clock,
  Sparkles,
} from "lucide-react";

interface TriageItem {
  id: number;
  clientName: string;
  urgency: "high" | "medium" | "low";
  reason: string;
  actionRequired: string;
  proposedProgression: string;
  safetyFlag?: string;
  draftMessage?: string;
  approved: boolean;
}

export default function TrainerDashboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterUrgency, setFilterUrgency] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"urgency" | "name">("urgency");
  const [generatedLink, setGeneratedLink] = useState<string | null>(null);

  // Sample progression triage queue
  const [items, setItems] = useState<TriageItem[]>([
    {
      id: 1,
      clientName: "Sarah Miller",
      urgency: "high",
      reason: "Shoulder pinching reported on set 3 of Bench Press. Reps hit: 10, 10, 8.",
      actionRequired: "Review shoulder injury history and approve or adjust load.",
      proposedProgression: "Bench Press: Hold at 135 lbs (No load jump due to pain flag)",
      safetyFlag: "Progression Planner Warning: Client intake lists shoulder impingement. Weight increase blocked.",
      draftMessage: "Hey Sarah, I saw your note about shoulder pinching on the last bench set. How is it feeling today?",
      approved: false,
    },
    {
      id: 2,
      clientName: "Marcus Vance",
      urgency: "medium",
      reason: "Completed all 3 sets of Back Squat at 185 lbs with clean rep cadence.",
      actionRequired: "Approve Week 2 progression.",
      proposedProgression: "Back Squat: +5 lbs (185 lbs -> 190 lbs, 3 x 8 reps)",
      safetyFlag: undefined,
      approved: false,
    },
    {
      id: 3,
      clientName: "Elena Rostova",
      urgency: "medium",
      reason: "No workout logged in the past 5 days.",
      actionRequired: "Send check-in message.",
      proposedProgression: "Deadlift: Hold at 155 lbs pending return session",
      draftMessage: "Hi Elena, hope you're having a good week! Let me know if you need any adjustments before your next workout.",
      approved: false,
    },
  ]);

  // Handle plan approval (Human-in-the-Loop)
  const handleApprove = (id: number) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, approved: true } : item))
    );
  };

  // Generate unique client session link
  const handleCreateSessionLink = (clientName: string) => {
    const mockToken = `s_${Math.random().toString(36).substring(2, 10)}`;
    const fullUrl = `${window.location.origin}/s/${mockToken}`;
    setGeneratedLink(fullUrl);
  };

  // Filter and search
  const filteredItems = items
    .filter((item) => {
      const matchesSearch = item.clientName.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesFilter = filterUrgency === "all" || item.urgency === filterUrgency;
      return matchesSearch && matchesFilter;
    })
    .sort((a, b) => {
      if (sortBy === "urgency") {
        const order = { high: 0, medium: 1, low: 2 };
        return order[a.urgency] - order[b.urgency];
      }
      return a.clientName.localeCompare(b.clientName);
    });

  return (
    <div className="flex-1 flex flex-col h-full bg-ground text-ink">
      {/* Top Trainer Navigation Bar */}
      <header className="px-4 py-3 bg-surface border-b border-hairline sticky top-0 z-20 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="p-1.5 bg-surface rounded-lg text-ink-2">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-display text-base font-medium text-ink">Trainer Dashboard</h1>
              <p className="text-sm text-muted">Sunday Planning & Safety Review</p>
            </div>
          </Link>
        </div>

        {/* Action: Generate Client Link */}
        <button
          onClick={() => handleCreateSessionLink("New Athlete")}
          className="touch-target px-3 py-1.5 bg-action hover:bg-action-hover text-on-action rounded-full text-sm font-semibold flex items-center gap-1.5 flex-shrink-0 whitespace-nowrap transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>New Client Link</span>
        </button>
      </header>

      {/* Generated Session Link Banner */}
      {generatedLink && (
        <div className="mx-4 mt-3 p-3 bg-surface border border-hairline rounded-xl flex items-center justify-between text-sm">
          <div className="truncate mr-2">
            <span className="text-muted">Client Session Link: </span>
            <span className="text-ink-2 font-mono select-all">{generatedLink}</span>
          </div>
          <button
            onClick={() => {
              navigator.clipboard.writeText(generatedLink);
              alert("Copied link to clipboard!");
            }}
            className="px-2 py-1 bg-surface hover:bg-hairline text-ink rounded font-medium"
          >
            Copy
          </button>
        </div>
      )}

      {/* Search, Filter, and Sort Controls */}
      <div className="px-4 pt-4 pb-2 grid grid-cols-1 sm:grid-cols-3 gap-2">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted" />
          <input
            type="text"
            placeholder="Search clients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-surface border border-hairline rounded-xl text-sm text-ink placeholder-muted focus:outline-none focus:ring-1 focus:ring-ink"
          />
        </div>

        {/* Filter Urgency */}
        <div className="flex items-center gap-1.5 bg-surface border border-hairline rounded-xl px-3 py-2 text-sm">
          <Filter className="w-3.5 h-3.5 text-muted" />
          <select
            value={filterUrgency}
            onChange={(e) => setFilterUrgency(e.target.value)}
            aria-label="Filter by urgency"
            className="bg-transparent text-ink focus:outline-none w-full"
          >
            <option value="all">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>
        </div>

        {/* Sort */}
        <div className="flex items-center gap-1.5 bg-surface border border-hairline rounded-xl px-3 py-2 text-sm">
          <ArrowUpDown className="w-3.5 h-3.5 text-muted" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as "urgency" | "name")}
            aria-label="Sort clients"
            className="bg-transparent text-ink focus:outline-none w-full"
          >
            <option value="urgency">Sort by Urgency</option>
            <option value="name">Sort by Name</option>
          </select>
        </div>
      </div>

      {/* Dedicated Scrollable Container for Review Items */}
      <div className="flex-1 scrollable-container p-4 grid gap-4 lg:grid-cols-2 items-start content-start">
        {filteredItems.map((item) => (
          <div
            key={item.id}
            className={`p-4 rounded-2xl border transition-all ${
              item.approved
                ? "bg-surface border-hairline"
                : item.urgency === "high"
                ? "bg-surface border-warn-line"
                : "bg-surface border-hairline"
            }`}
          >
            {/* Client Header & Urgency Badge */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <h2 className="font-display text-base font-medium text-ink">{item.clientName}</h2>
                <span
                  className={`text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                    item.urgency === "high"
                      ? "bg-warn-bg text-warn border border-warn-line"
                      : "bg-ground text-ink-2 border border-hairline"
                  }`}
                >
                  {item.urgency} priority
                </span>
              </div>

              {item.approved && (
                <span className="flex items-center gap-1 text-sm text-success font-semibold bg-success-bg px-2 py-0.5 rounded-full border border-success-line">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Approved
                </span>
              )}
            </div>

            {/* Adherence / Event Reason */}
            <p className="text-sm text-ink-2 mb-3">{item.reason}</p>

            {/* Proposed Progression Box */}
            <div className="p-3 bg-ground rounded-xl border border-hairline mb-3">
              <div className="flex items-center justify-between text-sm text-muted mb-1">
                <span className="font-semibold text-ink-2 flex items-center gap-1">
                  <TrendingUp className="w-3.5 h-3.5 text-ink-2" />
                  Proposed Next Week Progression:
                </span>
                <span className="text-xs text-muted font-mono">Engine: LinearProgression</span>
              </div>
              <p className="text-sm font-medium text-ink">{item.proposedProgression}</p>

              {/* Progression Planner Safety Warning Banner */}
              {item.safetyFlag && (
                <div className="mt-2 p-2 bg-warn-bg border border-warn-line rounded-lg flex items-start gap-2 text-sm text-warn">
                  <AlertTriangle className="w-4 h-4 text-warn flex-shrink-0 mt-0.5" />
                  <span>{item.safetyFlag}</span>
                </div>
              )}
            </div>

            {/* Pre-Drafted Check-In Message from Trainer Assistant */}
            {item.draftMessage && (
              <div className="p-3 bg-ground border border-hairline rounded-xl mb-3">
                <span className="text-xs font-semibold text-ink-2 flex items-center gap-1 mb-1">
                  <Sparkles className="w-3.5 h-3.5 text-ink-2" />
                  Trainer Assistant Suggested Follow-Up:
                </span>
                <p className="text-sm text-ink-2 italic">"{item.draftMessage}"</p>
              </div>
            )}

            {/* Human-in-the-Loop Action Controls */}
            <div className="flex items-center gap-2 pt-1">
              {!item.approved ? (
                <>
                  <button
                    onClick={() => handleApprove(item.id)}
                    className="touch-target flex-1 py-2 bg-action hover:bg-action-hover text-on-action font-semibold rounded-full text-sm flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Approve Progression</span>
                  </button>
                  <button className="touch-target px-4 py-2 border border-hairline hover:bg-hairline active:bg-hairline text-ink-2 rounded-full text-sm font-semibold">
                    Edit Plan
                  </button>
                </>
              ) : (
                <button
                  disabled
                  className="w-full py-2 bg-surface text-muted rounded-xl text-sm font-semibold cursor-not-allowed"
                >
                  Plan Sent to Client's Session Link
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Model & Agent Observability Footer */}
      <footer className="px-4 py-2 bg-surface border-t border-hairline text-xs text-muted flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-success animate-pulse"></span>
          <span>Active: Workout Logger, Progression Planner, Trainer Assistant</span>
        </div>
        <div>Model: Claude Sonnet 5.5</div>
      </footer>
    </div>
  );
}
