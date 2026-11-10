"use client";

/**
 * Triage Feed: clients who need the trainer's attention today.
 *
 * Each card holds a check-in drafted by the Trainer Assistant. The app never sends it.
 * The trainer edits it if they like, copies it, and sends it from their own phone.
 */

import React, { useState } from "react";
import { Check, ChevronDown, Copy } from "lucide-react";
import type { TriageCard, Urgency } from "@/types";

const URGENCY_STYLES: Record<Urgency, { border: string; tint: string; badge: string; label: string }> = {
  high: { border: "border-l-danger", tint: "bg-surface", badge: "bg-danger text-on-action", label: "High" },
  medium: { border: "border-l-warn", tint: "bg-surface", badge: "bg-warn text-on-action", label: "Medium" },
  routine: { border: "border-l-success", tint: "bg-surface", badge: "bg-success-bg text-success border border-success-line", label: "Routine" },
};

interface TriageFeedProps {
  cards: TriageCard[];
  onDismiss: (cardId: number) => Promise<void>;
}

export default function TriageFeed({ cards, onDismiss }: TriageFeedProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [dismissingId, setDismissingId] = useState<number | null>(null);

  if (cards.length === 0) return null;

  const messageFor = (card: TriageCard) => drafts[card.id] ?? card.draft_message;

  const copyMessage = async (card: TriageCard) => {
    try {
      await navigator.clipboard.writeText(messageFor(card));
      setCopiedId(card.id);
    } catch {
      setCopiedId(null);
    }
  };

  const dismiss = async (cardId: number) => {
    setDismissingId(cardId);
    try {
      await onDismiss(cardId);
    } finally {
      setDismissingId(null);
    }
  };

  return (
    <section className="space-y-3" aria-label="Triage feed">
      <div>
        <h2 className="section-title font-display text-lg font-medium text-ink">Check in with ({cards.length})</h2>
        <p className="text-sm text-ink-2">Drafts are for you to review and send yourself.</p>
      </div>
      <div className="grid gap-3 lg:grid-cols-2 items-start">
        {cards.map((card) => {
          const style = URGENCY_STYLES[card.urgency];
          const expanded = expandedId === card.id;
          return (
            <article key={card.id} className={`p-4 rounded-2xl border border-hairline border-l-4 space-y-3 ${style.border} ${style.tint}`}>
              <button
                type="button"
                onClick={() => setExpandedId(expanded ? null : card.id)}
                aria-expanded={expanded}
                className="w-full text-left flex items-start justify-between gap-3"
              >
                <span>
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-display text-base font-bold tracking-tight text-ink">{card.client_name}</span>
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${style.badge}`}>{style.label}</span>
                  </span>
                  <span className="block text-sm text-ink-2 mt-1">{card.reason}</span>
                </span>
                <ChevronDown className={`w-5 h-5 flex-shrink-0 text-muted transition-transform ${expanded ? "rotate-180" : ""}`} />
              </button>

              {expanded && (
                <div className="space-y-3">
                  {editingId === card.id ? (
                    <textarea
                      rows={4}
                      value={messageFor(card)}
                      onChange={(e) => {
                        setDrafts((current) => ({ ...current, [card.id]: e.target.value }));
                        setCopiedId(null);
                      }}
                      aria-label={`Check-in message for ${card.client_name}`}
                      className="w-full p-3 rounded-xl bg-ground border border-hairline text-sm text-ink focus:outline-none focus:ring-2 focus:ring-ink resize-none"
                    />
                  ) : (
                    <p className="p-3 rounded-xl bg-ground border border-hairline text-sm text-ink">{messageFor(card)}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => copyMessage(card)}
                      className="touch-target px-4 bg-action hover:bg-action-hover text-on-action rounded-full text-sm font-semibold flex items-center gap-1.5"
                    >
                      {copiedId === card.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      <span>{copiedId === card.id ? "Copied" : "Copy Message"}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(editingId === card.id ? null : card.id)}
                      className="touch-target px-4 border border-hairline hover:bg-hairline text-ink-2 rounded-full text-sm font-semibold"
                    >
                      {editingId === card.id ? "Done" : "Edit Message"}
                    </button>
                    <button
                      type="button"
                      onClick={() => dismiss(card.id)}
                      disabled={dismissingId === card.id}
                      className="touch-target px-4 border border-hairline hover:bg-hairline disabled:opacity-50 text-ink-2 rounded-full text-sm font-semibold"
                    >
                      Dismiss Alert
                    </button>
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

export { URGENCY_STYLES };
