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
      safetyFlag: "Agent 2 Warning: Client intake lists shoulder impingement. Weight increase blocked.",
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
    <div className="flex-1 flex flex-col h-full bg-slate-900 text-slate-100">
      {/* Top Trainer Navigation Bar */}
      <header className="px-4 py-3 bg-slate-800/90 border-b border-slate-700/80 sticky top-0 z-20 flex items-center justify-between backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="p-1.5 bg-purple-500/10 rounded-lg text-purple-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white">Trainer Dashboard</h1>
              <p className="text-xs text-slate-400">Sunday Planning & Safety Review</p>
            </div>
          </Link>
        </div>

        {/* Action: Generate Client Link */}
        <button
          onClick={() => handleCreateSessionLink("New Athlete")}
          className="touch-target px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New Client Link</span>
        </button>
      </header>

      {/* Generated Session Link Banner */}
      {generatedLink && (
        <div className="mx-4 mt-3 p-3 bg-slate-800 border border-emerald-500/40 rounded-xl flex items-center justify-between text-xs">
          <div className="truncate mr-2">
            <span className="text-slate-400">Client Session Link: </span>
            <span className="text-emerald-400 font-mono select-all">{generatedLink}</span>
          </div>
          <button
            onClick={() => {
              navigator.clipboard.writeText(generatedLink);
              alert("Copied link to clipboard!");
            }}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-white rounded font-medium"
          >
            Copy
          </button>
        </div>
      )}

      {/* Search, Filter, and Sort Controls */}
      <div className="px-4 pt-4 pb-2 grid grid-cols-1 sm:grid-cols-3 gap-2">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search clients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        {/* Filter Urgency */}
        <div className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={filterUrgency}
            onChange={(e) => setFilterUrgency(e.target.value)}
            aria-label="Filter by urgency"
            className="bg-transparent text-white focus:outline-none w-full"
          >
            <option value="all">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>
        </div>

        {/* Sort */}
        <div className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs">
          <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as "urgency" | "name")}
            aria-label="Sort clients"
            className="bg-transparent text-white focus:outline-none w-full"
          >
            <option value="urgency">Sort by Urgency</option>
            <option value="name">Sort by Name</option>
          </select>
        </div>
      </div>

      {/* Dedicated Scrollable Container for Review Items */}
      <div className="flex-1 scrollable-container p-4 space-y-4">
        {filteredItems.map((item) => (
          <div
            key={item.id}
            className={`p-4 rounded-2xl border transition-all ${
              item.approved
                ? "bg-slate-800/40 border-slate-700/40 opacity-75"
                : item.urgency === "high"
                ? "bg-slate-800/90 border-amber-500/50 shadow-md shadow-amber-950/20"
                : "bg-slate-800/90 border-slate-700 shadow-sm"
            }`}
          >
            {/* Client Header & Urgency Badge */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">{item.clientName}</h2>
                <span
                  className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                    item.urgency === "high"
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                  }`}
                >
                  {item.urgency} priority
                </span>
              </div>

              {item.approved && (
                <span className="flex items-center gap-1 text-xs text-emerald-400 font-semibold bg-emerald-950/40 px-2 py-0.5 rounded-md border border-emerald-800/50">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Approved
                </span>
              )}
            </div>

            {/* Adherence / Event Reason */}
            <p className="text-xs text-slate-300 mb-3">{item.reason}</p>

            {/* Proposed Progression Box */}
            <div className="p-3 bg-slate-900/90 rounded-xl border border-slate-700/70 mb-3">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span className="font-semibold text-slate-300 flex items-center gap-1">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                  Proposed Next Week Progression:
                </span>
                <span className="text-[11px] text-slate-400 font-mono">Engine: LinearProgression</span>
              </div>
              <p className="text-xs font-medium text-white">{item.proposedProgression}</p>

              {/* Agent 2 Safety Warning Banner */}
              {item.safetyFlag && (
                <div className="mt-2 p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-start gap-2 text-xs text-amber-200">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <span>{item.safetyFlag}</span>
                </div>
              )}
            </div>

            {/* Pre-Drafted Check-In Message from Agent 3 */}
            {item.draftMessage && (
              <div className="p-3 bg-purple-950/20 border border-purple-800/40 rounded-xl mb-3">
                <span className="text-[11px] font-semibold text-purple-300 flex items-center gap-1 mb-1">
                  <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                  Agent 3 Suggested Follow-Up:
                </span>
                <p className="text-xs text-slate-300 italic">"{item.draftMessage}"</p>
              </div>
            )}

            {/* Human-in-the-Loop Action Controls */}
            <div className="flex items-center gap-2 pt-1">
              {!item.approved ? (
                <>
                  <button
                    onClick={() => handleApprove(item.id)}
                    className="touch-target flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Approve Progression</span>
                  </button>
                  <button className="touch-target px-4 py-2 border border-slate-700 hover:bg-slate-700 active:bg-slate-800 text-slate-300 rounded-xl text-xs font-semibold">
                    Edit Plan
                  </button>
                </>
              ) : (
                <button
                  disabled
                  className="w-full py-2 bg-slate-800 text-slate-500 rounded-xl text-xs font-semibold cursor-not-allowed"
                >
                  Plan Sent to Client's Session Link
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Model & Agent Observability Footer */}
      <footer className="px-4 py-2 bg-slate-950 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Active Agents: 3 (Intake, Progression, Monitor)</span>
        </div>
        <div>Model: Claude 3.7 Sonnet</div>
      </footer>
    </div>
  );
}
