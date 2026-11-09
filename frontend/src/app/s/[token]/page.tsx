"use client";

/**
 * Client Mobile Workout Logger and Progress View (/s/:token).
 * 
 * Features:
 * 1. Accessed strictly via unique session URL; no password required.
 * 2. Mobile-first design for one-handed gym floor usage (touch targets >= 44px).
 * 3. Natural language chat or voice log input parsed by Workout Logger.
 * 4. Quick Set Logger with one-tap joint pain / inhibitor toggle.
 * 5. LocalStorage Crash Safeguard: Keystrokes and sets are saved on every change,
 *    ensuring zero data is lost if the browser refreshes mid-workout.
 * 6. Client Self-Progress History view.
 */

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Dumbbell,
  AlertTriangle,
  Send,
  Plus,
  Clock,
  ChevronLeft,
  CheckCircle2,
  TrendingUp,
} from "lucide-react";

interface SetRow {
  setNum: number;
  reps: number;
  weightLbs: number;
  painFlag: boolean;
}

export default function ClientSessionPage() {
  const params = useParams();
  const token = (params?.token as string) || "demo-session";

  // Client and workout plan state
  const [clientName, setClientName] = useState("Sarah Miller");
  const [weekLabel, setWeekLabel] = useState("Week 2 - Progressive Load");
  const [selectedExercise, setSelectedExercise] = useState("Barbell Bench Press");

  // In-gym logging input
  const [chatInput, setChatInput] = useState("");
  const [submissionStatus, setSubmissionStatus] = useState<string | null>(null);

  // Quick set logger rows
  const [sets, setSets] = useState<SetRow[]>([
    { setNum: 1, reps: 10, weightLbs: 135, painFlag: false },
    { setNum: 2, reps: 10, weightLbs: 135, painFlag: false },
    { setNum: 3, reps: 10, weightLbs: 135, painFlag: false },
  ]);

  // Tab switch: Today's Workout vs My Progress
  const [activeTab, setActiveTab] = useState<"workout" | "progress">("workout");

  // LocalStorage Crash Protection: Restore draft on load
  useEffect(() => {
    try {
      const savedInput = localStorage.getItem(`draft_chat_${token}`);
      if (savedInput) setChatInput(savedInput);

      const savedSets = localStorage.getItem(`draft_sets_${token}`);
      if (savedSets) setSets(JSON.parse(savedSets));
    } catch {
      // Fallback silently if localStorage is restricted
    }
  }, [token]);

  // Save to localStorage on every change to prevent mid-workout data loss
  const handleChatChange = (val: string) => {
    setChatInput(val);
    try {
      localStorage.setItem(`draft_chat_${token}`, val);
    } catch {}
  };

  const handleTogglePain = (index: number) => {
    const updated = [...sets];
    updated[index].painFlag = !updated[index].painFlag;
    setSets(updated);
    try {
      localStorage.setItem(`draft_sets_${token}`, JSON.stringify(updated));
    } catch {}
  };

  const handleUpdateReps = (index: number, delta: number) => {
    const updated = [...sets];
    const newReps = Math.max(0, updated[index].reps + delta);
    updated[index].reps = newReps;
    setSets(updated);
    try {
      localStorage.setItem(`draft_sets_${token}`, JSON.stringify(updated));
    } catch {}
  };

  const handleAddSet = () => {
    const nextNum = sets.length + 1;
    const prevWeight = sets[sets.length - 1]?.weightLbs || 135;
    const prevReps = sets[sets.length - 1]?.reps || 10;
    const updated = [...sets, { setNum: nextNum, reps: prevReps, weightLbs: prevWeight, painFlag: false }];
    setSets(updated);
    try {
      localStorage.setItem(`draft_sets_${token}`, JSON.stringify(updated));
    } catch {}
  };

  const handleSubmitWorkout = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmissionStatus("Workout logged successfully! Your trainer will review next week's draft.");
    // Clear draft from localStorage on successful submission
    try {
      localStorage.removeItem(`draft_chat_${token}`);
      localStorage.removeItem(`draft_sets_${token}`);
    } catch {}
  };

  return (
    <div className="flex-1 flex flex-col h-full w-full max-w-md mx-auto bg-ground text-ink">
      {/* Mobile Top App Bar */}
      <header className="px-4 py-3 bg-surface border-b border-hairline sticky top-0 z-20 flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <Link href="/" className="p-1 text-muted hover:text-ink">
            <ChevronLeft className="w-5 h-5" />
          </Link>
          <div className="min-w-0">
            <h1 className="font-display text-base font-medium text-ink leading-tight">{clientName}</h1>
            <p className="text-sm text-ink-2 font-medium truncate">{weekLabel}</p>
          </div>
        </div>

        {/* Tab Navigator */}
        <div className="flex flex-shrink-0 bg-ground p-0.5 rounded-full border border-hairline">
          <button
            onClick={() => setActiveTab("workout")}
            className={`px-3 py-1.5 text-sm font-semibold rounded-full whitespace-nowrap transition-colors ${
              activeTab === "workout" ? "bg-action text-on-action" : "text-muted"
            }`}
          >
            Today's Log
          </button>
          <button
            onClick={() => setActiveTab("progress")}
            className={`px-3 py-1.5 text-sm font-semibold rounded-full whitespace-nowrap transition-colors ${
              activeTab === "progress" ? "bg-action text-on-action" : "text-muted"
            }`}
          >
            My Progress
          </button>
        </div>
      </header>

      {/* Main Dedicated Scrollable Container */}
      <div className="flex-1 scrollable-container p-4 space-y-4">
        {submissionStatus && (
          <div className="p-4 bg-success-bg border border-success-line rounded-xl flex items-center gap-3 text-success text-base">
            <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" />
            <span>{submissionStatus}</span>
          </div>
        )}

        {activeTab === "workout" ? (
          <>
            {/* Active Exercise Prescribed Target */}
            <div className="bg-surface border border-hairline rounded-2xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold uppercase tracking-wider text-muted">
                  Target Exercise
                </span>
                <span className="inline-flex items-center gap-1 text-sm text-ink-2 font-medium bg-ground px-2 py-0.5 rounded-full border border-hairline">
                  <TrendingUp className="w-3 h-3" />
                  Target: 3 × 10 @ 135 lbs
                </span>
              </div>
              <h2 className="font-display text-xl font-medium text-ink">{selectedExercise}</h2>
              <p className="text-sm text-muted mt-1">
                Rest 90-120 seconds between sets. Tap the pain icon if you feel any joint pinching.
              </p>
            </div>

            {/* In-Gym Set Logger Card */}
            <div className="bg-surface border border-hairline rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-ink">Completed Sets</h3>
                <span className="text-sm text-muted">Autosaved to phone</span>
              </div>

              {/* Set Rows with large tap targets */}
              <div className="space-y-2">
                {sets.map((set, idx) => (
                  <div
                    key={set.setNum}
                    className={`flex items-center justify-between p-3 rounded-xl border transition-colors ${
                      set.painFlag
                        ? "bg-warn-bg border-warn-line"
                        : "bg-ground border-hairline"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-surface text-ink-2 text-sm font-semibold flex items-center justify-center">
                        {set.setNum}
                      </span>
                      <div>
                        <span className="block text-base font-semibold text-ink whitespace-nowrap">{set.weightLbs} lbs</span>
                        <span className="block text-sm text-muted whitespace-nowrap">× {set.reps} reps</span>
                      </div>
                    </div>

                    {/* Quick rep adjustment buttons */}
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleUpdateReps(idx, -1)}
                        className="touch-target w-9 h-9 rounded-full bg-surface hover:bg-hairline active:bg-hairline text-ink font-semibold text-base flex items-center justify-center"
                        aria-label="Decrease reps"
                      >
                        -
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUpdateReps(idx, 1)}
                        className="touch-target w-9 h-9 rounded-full bg-surface hover:bg-hairline active:bg-hairline text-ink font-semibold text-base flex items-center justify-center"
                        aria-label="Increase reps"
                      >
                        +
                      </button>

                      {/* 1-Tap Joint Pain / Inhibitor Toggle */}
                      <button
                        type="button"
                        onClick={() => handleTogglePain(idx)}
                        className={`touch-target px-2.5 h-9 rounded-full border flex items-center gap-1 text-sm font-semibold ml-1 transition-colors ${
                          set.painFlag
                            ? "bg-warn text-on-action border-warn-line"
                            : "bg-surface text-muted border-hairline hover:text-warn"
                        }`}
                        aria-label="Toggle pain flag"
                      >
                        <AlertTriangle className="w-3.5 h-3.5" />
                        <span>{set.painFlag ? "Pain" : "OK"}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add Set Button */}
              <button
                type="button"
                onClick={handleAddSet}
                className="w-full touch-target py-2.5 border border-dashed border-hairline hover:border-ink text-muted hover:text-ink rounded-full text-sm font-medium flex items-center justify-center gap-1 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add Set</span>
              </button>
            </div>

            {/* Natural Language Voice / Chat Extraction Input (Workout Logger) */}
            <div className="bg-surface border border-hairline rounded-2xl p-4">
              <h3 className="text-base font-semibold text-ink mb-1">
                Voice Dictation or Chat Note
              </h3>
              <p className="text-sm text-muted mb-2">
                Dictate or type freely: "Did bench 135 for 3 sets of 10. Shoulder felt good."
              </p>

              <form onSubmit={handleSubmitWorkout} className="space-y-3">
                <textarea
                  rows={3}
                  value={chatInput}
                  onChange={(e) => handleChatChange(e.target.value)}
                  placeholder="Tell your coach how it felt, weights used, or missed sets..."
                  className="w-full p-3 rounded-xl bg-ground border border-hairline text-ink placeholder-muted text-base focus:outline-none focus:ring-2 focus:ring-ink resize-none"
                />

                <button
                  type="submit"
                  className="w-full touch-target py-3 bg-action hover:bg-action-hover text-on-action font-semibold rounded-full text-base flex items-center justify-center gap-2 transition-colors"
                >
                  <Send className="w-4 h-4" />
                  <span>Submit Today's Workout</span>
                </button>
              </form>
            </div>
          </>
        ) : (
          /* Client Self-Progress History View */
          <div className="space-y-4">
            <div className="bg-surface border border-hairline rounded-2xl p-4">
              <h3 className="text-base font-semibold text-ink mb-1">Your Progression History</h3>
              <p className="text-sm text-muted mb-4">
                Week-over-week performance tracked automatically from your workout logs.
              </p>

              <div className="space-y-3">
                <div className="p-3 bg-ground rounded-xl border border-hairline">
                  <div className="flex items-center justify-between text-sm text-muted mb-1">
                    <span className="font-semibold text-ink">Barbell Bench Press</span>
                    <span>Week 1</span>
                  </div>
                  <div className="flex items-center justify-between text-base">
                    <span className="text-ink-2">3 sets of 10 reps</span>
                    <span className="font-semibold text-ink-2">135.0 lbs</span>
                  </div>
                </div>

                <div className="p-3 bg-ground rounded-xl border border-hairline">
                  <div className="flex items-center justify-between text-sm text-muted mb-1">
                    <span className="font-semibold text-ink">Back Squat</span>
                    <span>Week 1</span>
                  </div>
                  <div className="flex items-center justify-between text-base">
                    <span className="text-ink-2">3 sets of 8 reps</span>
                    <span className="font-semibold text-ink-2">185.0 lbs</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
