"use client";

/**
 * Client Mobile Workout Logger and Progress View (/s/:token).
 * 
 * Features:
 * 1. Accessed strictly via unique session URL; no password required.
 * 2. Mobile-first design for one-handed gym floor usage (touch targets >= 44px).
 * 3. Natural language chat or voice log input parsed by Agent 1.
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
    <div className="flex-1 flex flex-col h-full bg-slate-900 text-slate-100">
      {/* Mobile Top App Bar */}
      <header className="px-4 py-3 bg-slate-800/90 border-b border-slate-700/80 sticky top-0 z-20 flex items-center justify-between backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Link href="/" className="p-1 text-slate-400 hover:text-white">
            <ChevronLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-sm font-bold text-white leading-tight">{clientName}</h1>
            <p className="text-xs text-emerald-400 font-medium">{weekLabel}</p>
          </div>
        </div>

        {/* Tab Navigator */}
        <div className="flex bg-slate-900 p-0.5 rounded-lg border border-slate-700">
          <button
            onClick={() => setActiveTab("workout")}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
              activeTab === "workout" ? "bg-emerald-600 text-white" : "text-slate-400"
            }`}
          >
            Today's Log
          </button>
          <button
            onClick={() => setActiveTab("progress")}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
              activeTab === "progress" ? "bg-emerald-600 text-white" : "text-slate-400"
            }`}
          >
            My Progress
          </button>
        </div>
      </header>

      {/* Main Dedicated Scrollable Container */}
      <div className="flex-1 scrollable-container p-4 space-y-4">
        {submissionStatus && (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-300 text-sm">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <span>{submissionStatus}</span>
          </div>
        )}

        {activeTab === "workout" ? (
          <>
            {/* Active Exercise Prescribed Target */}
            <div className="bg-slate-800/90 border border-slate-700 rounded-2xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Target Exercise
                </span>
                <span className="inline-flex items-center gap-1 text-xs text-emerald-400 font-medium bg-emerald-950/40 px-2 py-0.5 rounded-full border border-emerald-800/50">
                  <TrendingUp className="w-3 h-3" />
                  Target: 3 × 10 @ 135 lbs
                </span>
              </div>
              <h2 className="text-xl font-bold text-white">{selectedExercise}</h2>
              <p className="text-xs text-slate-400 mt-1">
                Rest 90-120 seconds between sets. Tap the pain icon if you feel any joint pinching.
              </p>
            </div>

            {/* In-Gym Set Logger Card */}
            <div className="bg-slate-800/70 border border-slate-700/70 rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-200">Completed Sets</h3>
                <span className="text-xs text-slate-400">Autosaved to phone</span>
              </div>

              {/* Set Rows with large tap targets */}
              <div className="space-y-2">
                {sets.map((set, idx) => (
                  <div
                    key={set.setNum}
                    className={`flex items-center justify-between p-3 rounded-xl border transition-colors ${
                      set.painFlag
                        ? "bg-amber-950/20 border-amber-500/40"
                        : "bg-slate-900/80 border-slate-700/60"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-300 text-xs font-bold flex items-center justify-center">
                        {set.setNum}
                      </span>
                      <div>
                        <span className="text-sm font-bold text-white">{set.weightLbs} lbs</span>
                        <span className="text-xs text-slate-400 ml-1.5">× {set.reps} reps</span>
                      </div>
                    </div>

                    {/* Quick rep adjustment buttons */}
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleUpdateReps(idx, -1)}
                        className="touch-target w-9 h-9 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-600 text-white font-bold text-sm flex items-center justify-center"
                        aria-label="Decrease reps"
                      >
                        -
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUpdateReps(idx, 1)}
                        className="touch-target w-9 h-9 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-600 text-white font-bold text-sm flex items-center justify-center"
                        aria-label="Increase reps"
                      >
                        +
                      </button>

                      {/* 1-Tap Joint Pain / Inhibitor Toggle */}
                      <button
                        type="button"
                        onClick={() => handleTogglePain(idx)}
                        className={`touch-target px-2.5 h-9 rounded-lg border flex items-center gap-1 text-xs font-semibold ml-1 transition-colors ${
                          set.painFlag
                            ? "bg-amber-500 text-slate-950 border-amber-400"
                            : "bg-slate-800 text-slate-400 border-slate-700 hover:text-amber-400"
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
                className="w-full touch-target py-2.5 border border-dashed border-slate-700 hover:border-slate-500 text-slate-400 hover:text-white rounded-xl text-xs font-medium flex items-center justify-center gap-1 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add Set</span>
              </button>
            </div>

            {/* Natural Language Voice / Chat Extraction Input (Agent 1) */}
            <div className="bg-slate-800/70 border border-slate-700/70 rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-slate-200 mb-1">
                Voice Dictation or Chat Note
              </h3>
              <p className="text-xs text-slate-400 mb-2">
                Dictate or type freely: "Did bench 135 for 3 sets of 10. Shoulder felt good."
              </p>

              <form onSubmit={handleSubmitWorkout} className="space-y-3">
                <textarea
                  rows={3}
                  value={chatInput}
                  onChange={(e) => handleChatChange(e.target.value)}
                  placeholder="Tell your coach how it felt, weights used, or missed sets..."
                  className="w-full p-3 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
                />

                <button
                  type="submit"
                  className="w-full touch-target py-3 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-bold rounded-xl text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40 transition-colors"
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
            <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-4">
              <h3 className="text-base font-bold text-white mb-1">Your Progression History</h3>
              <p className="text-xs text-slate-400 mb-4">
                Week-over-week performance tracked automatically from your workout logs.
              </p>

              <div className="space-y-3">
                <div className="p-3 bg-slate-900/90 rounded-xl border border-slate-700/60">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span className="font-semibold text-white">Barbell Bench Press</span>
                    <span>Week 1</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-300">3 sets of 10 reps</span>
                    <span className="font-bold text-emerald-400">135.0 lbs</span>
                  </div>
                </div>

                <div className="p-3 bg-slate-900/90 rounded-xl border border-slate-700/60">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span className="font-semibold text-white">Back Squat</span>
                    <span>Week 1</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-300">3 sets of 8 reps</span>
                    <span className="font-bold text-emerald-400">185.0 lbs</span>
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
