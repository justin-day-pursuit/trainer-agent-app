"use client";

/**
 * Landing Page & Role Navigation Hub.
 * 
 * Provides an immediate starting point for both audiences:
 * 1. Clients: Enter their unique session link provided by their trainer (or try demo).
 * 2. Trainers: Sign in to open the progression dashboard and client triage feed.
 */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Dumbbell, ShieldCheck, ArrowRight, UserCheck, Smartphone } from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const [sessionToken, setSessionToken] = useState("");

  const handleClientSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (sessionToken.trim()) {
      // Extract token if user pasted the full URL
      const cleanToken = sessionToken.trim().split("/s/").pop() || sessionToken.trim();
      router.push(`/s/${cleanToken}`);
    }
  };

  return (
    <main className="flex-1 flex flex-col justify-center px-4 py-8">
      {/* App Header Branding */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center p-3 bg-surface rounded-2xl border border-hairline mb-4">
          <Dumbbell className="w-8 h-8 text-ink-2" />
        </div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
          Trainer Progression
        </h1>
        <p className="mt-2 text-base text-muted max-w-sm mx-auto">
          Automated weekly progression drafting and frictionless gym floor logging.
        </p>
      </div>

      <div className="space-y-4 max-w-md w-full mx-auto">
        {/* Client Access Card */}
        <div className="bg-surface border border-hairline rounded-2xl p-6 shadow-xl backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-surface rounded-lg text-ink-2">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display text-lg font-medium text-ink">Client Workout Access</h2>
              <p className="text-sm text-muted">No password needed. Access via your trainer link.</p>
            </div>
          </div>

          <form onSubmit={handleClientSubmit} className="mt-4 space-y-3">
            <div>
              <label htmlFor="token-input" className="block text-sm font-medium text-ink-2 mb-1">
                Enter your Session Link or Token
              </label>
              <input
                id="token-input"
                type="text"
                placeholder="Paste link or token e.g. demo-client-session"
                value={sessionToken}
                onChange={(e) => setSessionToken(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-ground border border-hairline text-ink placeholder-muted text-base focus:outline-none focus:ring-2 focus:ring-ink"
              />
            </div>
            <button
              type="submit"
              className="w-full touch-target flex items-center justify-center gap-2 bg-action hover:bg-action-hover text-on-action font-medium rounded-full text-base transition-colors py-2.5"
            >
              <span>Open My Workout Log</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Shortcut */}
          <div className="mt-3 text-center">
            <Link
              href="/s/demo-client-session"
              className="text-sm text-ink-2 hover:text-ink-2 underline underline-offset-4"
            >
              Preview Demo Client Session Link
            </Link>
          </div>
        </div>

        {/* Trainer Access Card */}
        <div className="bg-surface border border-hairline rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-surface rounded-lg text-ink-2">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h2 className="font-display text-base font-medium text-ink">Personal Trainer Portal</h2>
                <p className="text-sm text-muted">Review progression drafts & approve weekly plans.</p>
              </div>
            </div>
          </div>

          <div className="mt-4 flex gap-2">
            <Link
              href="/trainer"
              className="flex-1 touch-target flex items-center justify-center gap-2 bg-surface hover:bg-hairline active:bg-hairline text-ink font-medium rounded-full text-base transition-colors py-2.5"
            >
              <UserCheck className="w-4 h-4 text-ink-2" />
              <span>Trainer Dashboard</span>
            </Link>
            <Link
              href="/trainer/login"
              className="touch-target px-4 flex items-center justify-center text-sm font-medium text-muted hover:text-ink border border-hairline rounded-full"
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
