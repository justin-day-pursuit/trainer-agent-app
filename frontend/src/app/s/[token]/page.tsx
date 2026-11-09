"use client";

/**
 * Client Mobile Workout Logger and Progress View (/s/:token).
 *
 * Features:
 * 1. Accessed strictly via unique session URL; no password required.
 * 2. Mobile-first design for one-handed gym floor usage (touch targets >= 44px).
 * 3. The client types or dictates what they did; the Workout Logger turns it into sets.
 * 4. Confirmation card: nothing is saved until the client reviews and confirms the sets.
 * 5. LocalStorage Crash Safeguard: text and the unconfirmed preview are saved on every change,
 *    and offered back after a refresh. The buffer clears only after a successful save.
 * 6. Client Self-Progress History view.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  Loader2,
  Mic,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import type { Effort, ExtractedSet, PrescribedExercise } from "@/types";

const LOGGER_MODEL = "claude-sonnet-5-5";
const PREVIEW_TIMEOUT_MS = 60000;

interface SessionView {
  client_name: string;
  link_status: "active" | "pending_review";
  last_session: {
    logged_at: string;
    sets: ExtractedSet[];
    has_pain_flag: boolean;
    pain_summary: string | null;
  } | null;
  active_plan: { id: number; week_label: string; exercises: PrescribedExercise[] };
}

interface PreviewResponse {
  status: "complete" | "incomplete";
  extracted_sets: ExtractedSet[];
  clarifying_question: string | null;
  has_pain_flag: boolean;
  pain_summary: string | null;
  model_name: string;
  execution_time_ms: number;
}

interface ProgressLog {
  id: number;
  logged_at: string;
  sets: ExtractedSet[];
  has_pain_flag: boolean;
}

/** One editable row on the confirmation card. Numbers stay as text while being typed. */
interface EditableSet {
  key: string;
  exerciseId: string;
  setNum: number;
  weight: string;
  reps: string;
  painFlag: boolean;
  note: string;
  effort: Effort | null;
}

interface Draft {
  rawInput: string;
  requestId: string | null;
  sets: EditableSet[] | null;
  painSummary: string;
  badge: string | null;
}

type Phase = "idle" | "analyzing" | "review" | "clarify" | "error" | "saved";

const EMPTY_DRAFT: Draft = { rawInput: "", requestId: null, sets: null, painSummary: "", badge: null };

/** Minimal shape of the browser's speech recognition, which TypeScript doesn't ship types for. */
interface SpeechResultEvent {
  resultIndex: number;
  results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }>;
}
interface SpeechRecognizer {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechResultEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
}
type SpeechWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognizer;
  webkitSpeechRecognition?: new () => SpeechRecognizer;
};

function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `req-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function toEditable(sets: ExtractedSet[]): EditableSet[] {
  return sets.map((set, index) => ({
    key: `${set.exercise_id}-${set.set_num}-${index}`,
    exerciseId: set.exercise_id,
    setNum: set.set_num,
    weight: set.weight_lbs === null || set.weight_lbs === undefined ? "" : String(set.weight_lbs),
    reps: String(set.reps),
    painFlag: set.pain_flag,
    note: set.note ?? "",
    effort: set.effort ?? null,
  }));
}

export default function ClientSessionPage() {
  const params = useParams();
  const token = (params?.token as string) || "demo-session";
  const storageKey = `workout_draft_${token}`;

  const [session, setSession] = useState<SessionView | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"workout" | "progress">("workout");

  const [phase, setPhase] = useState<Phase>("idle");
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [question, setQuestion] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [restorable, setRestorable] = useState<Draft | null>(null);

  const [progress, setProgress] = useState<ProgressLog[] | null>(null);

  const [speechSupported, setSpeechSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const recognizerRef = useRef<SpeechRecognizer | null>(null);
  const wasPendingRef = useRef(false);

  // Once the trainer approves, the link returns to a fresh workout on the new plan
  const applySession = useCallback((next: SessionView) => {
    if (wasPendingRef.current && next.link_status === "active") setPhase("idle");
    wasPendingRef.current = next.link_status === "pending_review";
    setSession(next);
  }, []);

  // Update the draft and write it to the phone at the same moment, so a crash can't lose it
  const updateDraft = useCallback(
    (patch: Partial<Draft>) => {
      setDraft((current) => {
        const next = { ...current, ...patch };
        try {
          localStorage.setItem(storageKey, JSON.stringify(next));
        } catch {
          // Storage can be blocked in private browsing; logging still works without it
        }
        return next;
      });
    },
    [storageKey]
  );

  const clearDraft = useCallback(() => {
    setDraft(EMPTY_DRAFT);
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // Nothing to clear if storage is blocked
    }
  }, [storageKey]);

  // Load the client's plan and look for an unfinished workout from earlier
  useEffect(() => {
    apiFetch<SessionView>(`/s/${token}`)
      .then(applySession)
      .catch((error) =>
        setLoadError(
          error instanceof ApiError && error.status === 404
            ? "This workout link isn't working. Ask your trainer for a new one."
            : "We can't reach the server right now. Anything you typed is saved, so refresh to try again."
        )
      );

    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved) as Draft;
        if (parsed.rawInput || parsed.sets) setRestorable(parsed);
      }
    } catch {
      // A damaged draft is ignored
    }

    const speechWindow = window as SpeechWindow;
    setSpeechSupported(Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition));
  }, [token, storageKey, applySession]);

  useEffect(() => {
    if (activeTab !== "progress") return;
    apiFetch<{ recent_logs: ProgressLog[] }>(`/s/${token}/progress`)
      .then((data) => setProgress(data.recent_logs))
      .catch(() => setProgress([]));
  }, [activeTab, token, phase]);

  // Pick up a newly approved plan when the client returns, and keep checking while they wait
  const isPending = session?.link_status === "pending_review";
  useEffect(() => {
    const refreshPlan = () => {
      if (document.visibilityState === "visible") {
        apiFetch<SessionView>(`/s/${token}`).then(applySession).catch(() => undefined);
      }
    };
    document.addEventListener("visibilitychange", refreshPlan);
    const timer = isPending ? setInterval(refreshPlan, 30000) : undefined;
    return () => {
      document.removeEventListener("visibilitychange", refreshPlan);
      if (timer) clearInterval(timer);
    };
  }, [token, applySession, isPending]);

  useEffect(() => () => recognizerRef.current?.stop(), []);

  const exercises = session?.active_plan.exercises ?? [];
  const exerciseName = (id: string) => exercises.find((e) => e.exercise_id === id)?.name ?? id;

  const handleRestore = () => {
    if (!restorable) return;
    updateDraft(restorable);
    setPhase(restorable.sets ? "review" : "idle");
    setRestorable(null);
  };

  const handleDiscard = () => {
    clearDraft();
    setRestorable(null);
  };

  const toggleListening = () => {
    if (listening) {
      recognizerRef.current?.stop();
      return;
    }
    const speechWindow = window as SpeechWindow;
    const Recognizer = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!Recognizer) return;

    const recognizer = new Recognizer();
    recognizer.continuous = true;
    recognizer.interimResults = false;
    recognizer.lang = "en-US";
    recognizer.onresult = (event) => {
      let spoken = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) spoken += event.results[i][0].transcript;
      }
      if (!spoken.trim()) return;
      setDraft((current) => {
        const rawInput = `${current.rawInput} ${spoken.trim()}`.trim();
        const next = { ...current, rawInput };
        try {
          localStorage.setItem(storageKey, JSON.stringify(next));
        } catch {
          // Storage can be blocked in private browsing
        }
        return next;
      });
    };
    recognizer.onend = () => setListening(false);
    recognizer.onerror = () => setListening(false);
    recognizerRef.current = recognizer;
    recognizer.start();
    setListening(true);
  };

  const handlePreview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (draft.rawInput.trim().length < 2 || phase === "analyzing") return;
    recognizerRef.current?.stop();

    setPhase("analyzing");
    setErrorMessage(null);
    setQuestion(null);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), PREVIEW_TIMEOUT_MS);
    try {
      const result = await apiFetch<PreviewResponse>(`/s/${token}/log/preview`, {
        method: "POST",
        body: JSON.stringify({
          raw_input: draft.rawInput,
          plan_id: session?.active_plan.id || null,
        }),
        signal: controller.signal,
      });

      if (result.status === "incomplete") {
        setQuestion(result.clarifying_question);
        setPhase("clarify");
        return;
      }

      updateDraft({
        // The same ID is reused on retries so a workout can't be saved twice
        requestId: draft.requestId ?? newRequestId(),
        sets: toEditable(result.extracted_sets),
        painSummary: result.pain_summary ?? "",
        badge: `Extracted by ${result.model_name} in ${Math.round(result.execution_time_ms)}ms`,
      });
      setPhase("review");
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "We couldn't reach the server. Your text is saved, so try again."
      );
      setPhase("error");
    } finally {
      clearTimeout(timer);
    }
  };

  const updateSet = (key: string, patch: Partial<EditableSet>) => {
    updateDraft({ sets: (draft.sets ?? []).map((set) => (set.key === key ? { ...set, ...patch } : set)) });
  };

  // Effort is asked once per exercise, then applied to all of that exercise's sets
  const setEffort = (exerciseId: string, effort: Effort) => {
    updateDraft({
      sets: (draft.sets ?? []).map((set) => (set.exerciseId === exerciseId ? { ...set, effort } : set)),
    });
  };

  const removeSet = (key: string) => {
    updateDraft({ sets: (draft.sets ?? []).filter((set) => set.key !== key) });
  };

  const backToEditing = () => {
    updateDraft({ sets: null, badge: null, painSummary: "" });
    setPhase("idle");
  };

  const sets = draft.sets ?? [];
  const hasPain = sets.some((set) => set.painFlag);
  const effortFor = (exerciseId: string): Effort | null =>
    sets.find((set) => set.exerciseId === exerciseId && set.effort)?.effort ?? null;
  const effortsAnswered = sets.every((set) => effortFor(set.exerciseId) !== null);
  const setsAreValid =
    sets.length > 0 &&
    effortsAnswered &&
    sets.every(
      (set) =>
        /^\d+$/.test(set.reps) && (set.weight === "" || /^\d+(\.\d+)?$/.test(set.weight))
    );

  const handleConfirm = async () => {
    if (!setsAreValid || saving) return;
    setSaving(true);
    setErrorMessage(null);

    // Sets are renumbered per exercise in case a row was removed
    const counters: Record<string, number> = {};
    const confirmedSets: ExtractedSet[] = sets.map((set) => {
      counters[set.exerciseId] = (counters[set.exerciseId] ?? 0) + 1;
      return {
        exercise_id: set.exerciseId,
        set_num: counters[set.exerciseId],
        weight_lbs: set.weight === "" ? null : Number(set.weight),
        reps: Number(set.reps),
        pain_flag: set.painFlag,
        note: set.note || null,
        effort: effortFor(set.exerciseId),
      };
    });

    try {
      await apiFetch(`/s/${token}/log`, {
        method: "POST",
        body: JSON.stringify({
          plan_id: session?.active_plan.id || null,
          client_request_id: draft.requestId ?? newRequestId(),
          raw_input: draft.rawInput,
          confirmed_sets: confirmedSets,
          has_pain_flag: hasPain,
          pain_summary: hasPain ? draft.painSummary || null : null,
        }),
      });
      clearDraft();
      setPhase("saved");
      apiFetch<SessionView>(`/s/${token}`).then(applySession).catch(() => undefined);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        // A 409 means an earlier attempt already saved this workout
        clearDraft();
        setPhase("saved");
        apiFetch<SessionView>(`/s/${token}`).then(applySession).catch(() => undefined);
      } else {
        setErrorMessage(
          error instanceof ApiError
            ? error.message
            : "We couldn't save that. Your sets are still here, so try again."
        );
      }
    } finally {
      setSaving(false);
    }
  };

  // Group confirmation rows by exercise so each lift reads as one block
  const groupedSets = Array.from(new Set(sets.map((set) => set.exerciseId))).map((id) => ({
    id,
    rows: sets.filter((set) => set.exerciseId === id),
  }));

  const numberField =
    "w-16 h-11 text-center rounded-lg bg-ground border border-hairline text-base font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-ink";

  return (
    <div className="flex-1 flex flex-col h-full w-full max-w-md mx-auto bg-ground text-ink">
      {/* Mobile Top App Bar */}
      <header className="px-4 py-3 bg-surface border-b border-hairline sticky top-0 z-20 flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <Link href="/" className="p-1 text-muted hover:text-ink" aria-label="Back to home">
            <ChevronLeft className="w-5 h-5" />
          </Link>
          <div className="min-w-0">
            <h1 className="font-display text-base font-medium text-ink leading-tight truncate">
              {session?.client_name ?? "Your workout"}
            </h1>
            <p className="text-sm text-ink-2 font-medium truncate">{session?.active_plan.week_label ?? ""}</p>
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

      <div className="flex-1 scrollable-container p-4 space-y-4">
        {loadError && (
          <div className="p-4 bg-warn-bg border border-warn-line rounded-xl text-warn text-base">{loadError}</div>
        )}

        {activeTab === "workout" && !loadError && isPending ? (
          /* Waiting on the trainer: this stays in place through reloads until they approve */
          <section className="space-y-4">
            <div className="p-4 bg-success-bg border border-success-line rounded-2xl" role="status">
              <p className="flex items-center gap-2 font-display text-xl font-medium text-success">
                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                Session Logged! Great work.
              </p>
              <p className="text-base text-ink-2 mt-1">
                Your trainer is reviewing your results to unlock next week's targets.
              </p>
            </div>

            <div className="bg-surface border border-hairline rounded-2xl p-4 space-y-3">
              <h2 className="font-display text-xl font-medium text-ink">What you logged</h2>
              {Array.from(new Set((session?.last_session?.sets ?? []).map((set) => set.exercise_id))).map((id) => {
                const rows = (session?.last_session?.sets ?? []).filter((set) => set.exercise_id === id);
                const effort = rows.find((set) => set.effort)?.effort;
                const hadPain = rows.some((set) => set.pain_flag);
                return (
                  <div key={id} className="p-3 bg-ground rounded-xl border border-hairline">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-base font-semibold text-ink">{exerciseName(id)}</span>
                      {effort && <span className="text-sm text-ink-2 capitalize">{effort}</span>}
                    </div>
                    <p className="text-sm text-ink-2">
                      {rows.map((set) => set.reps).join(", ")} reps
                      {rows.some((set) => set.weight_lbs)
                        ? ` @ ${Array.from(new Set(rows.map((set) => set.weight_lbs))).join(" / ")} lbs`
                        : ""}
                    </p>
                    {hadPain && <p className="text-sm font-semibold text-warn mt-1">Pain noted</p>}
                  </div>
                );
              })}
            </div>
          </section>
        ) : activeTab === "workout" && !loadError ? (
          <>
            {restorable && (
              <div className="p-4 bg-surface border border-hairline rounded-2xl space-y-3">
                <p className="text-base font-semibold text-ink">Restore in-progress workout?</p>
                <p className="text-sm text-ink-2 line-clamp-2">{restorable.rawInput}</p>
                <div className="flex gap-2">
                  <button
                    onClick={handleRestore}
                    className="touch-target flex-1 py-2 bg-action hover:bg-action-hover text-on-action rounded-full text-sm font-semibold"
                  >
                    Restore
                  </button>
                  <button
                    onClick={handleDiscard}
                    className="touch-target flex-1 py-2 border border-hairline text-ink rounded-full text-sm font-semibold"
                  >
                    Discard
                  </button>
                </div>
              </div>
            )}

            {phase === "saved" && (
              <div className="p-4 bg-success-bg border border-success-line rounded-xl space-y-3" role="status">
                <div className="flex items-center gap-3 text-success text-base font-semibold">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                  <span>Workout logged! Your trainer is reviewing next week.</span>
                </div>
                <button
                  type="button"
                  onClick={() => setPhase("idle")}
                  className="touch-target w-full border border-success-line bg-ground text-ink rounded-full text-sm font-semibold"
                >
                  Log another workout
                </button>
              </div>
            )}

            {/* Today's plan */}
            <section className="bg-surface border border-hairline rounded-2xl p-4">
              <h2 className="font-display text-xl font-medium text-ink mb-3">Today's plan</h2>
              {session ? (
                <ul className="space-y-2">
                  {exercises.map((exercise) => (
                    <li key={exercise.exercise_id} className="flex items-baseline justify-between gap-3">
                      <span className="text-base text-ink">{exercise.name}</span>
                      <span className="text-sm text-ink-2 whitespace-nowrap">
                        {exercise.sets} × {exercise.target_reps}
                        {exercise.target_weight_lbs ? ` @ ${exercise.target_weight_lbs} lbs` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted">Loading your plan...</p>
              )}
            </section>

            {phase === "review" ? (
              /* Confirmation card: the client checks every number before anything is saved */
              <section className="bg-surface border border-hairline rounded-2xl p-4 space-y-4">
                <div>
                  <h2 className="font-display text-xl font-medium text-ink">Check your sets</h2>
                  <p className="text-sm text-ink-2 mt-0.5">Tap a number to fix it. Nothing is saved yet.</p>
                </div>

                {groupedSets.map((group) => (
                  <div key={group.id} className="space-y-2">
                    <h3 className="text-base font-semibold text-ink">{exerciseName(group.id)}</h3>
                    {group.rows.map((set, index) => (
                      <div
                        key={set.key}
                        className={`p-3 rounded-xl border space-y-2 ${
                          set.painFlag ? "bg-warn-bg border-warn-line" : "bg-ground border-hairline"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-6 text-sm font-semibold text-ink-2 text-center">{index + 1}</span>
                          <label className="flex items-center gap-1 text-sm text-ink-2">
                            <input
                              inputMode="decimal"
                              value={set.weight}
                              onChange={(e) => updateSet(set.key, { weight: e.target.value })}
                              aria-label={`Set ${index + 1} weight in pounds`}
                              placeholder="BW"
                              className={numberField}
                            />
                            lbs
                          </label>
                          <label className="flex items-center gap-1 text-sm text-ink-2">
                            <input
                              inputMode="numeric"
                              value={set.reps}
                              onChange={(e) => updateSet(set.key, { reps: e.target.value })}
                              aria-label={`Set ${index + 1} reps`}
                              className={numberField}
                            />
                            reps
                          </label>
                          <button
                            type="button"
                            onClick={() => removeSet(set.key)}
                            aria-label={`Remove set ${index + 1}`}
                            className="touch-target ml-auto flex items-center justify-center text-muted hover:text-ink"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                        <button
                          type="button"
                          onClick={() => updateSet(set.key, { painFlag: !set.painFlag })}
                          aria-pressed={set.painFlag}
                          className={`touch-target px-3 rounded-full border flex items-center gap-1.5 text-sm font-semibold ${
                            set.painFlag
                              ? "bg-warn text-on-action border-warn-line"
                              : "bg-surface text-muted border-hairline"
                          }`}
                        >
                          <AlertTriangle className="w-4 h-4" />
                          <span>{set.painFlag ? "Pain flagged" : "No pain"}</span>
                        </button>
                      </div>
                    ))}

                    <div className="pt-1">
                      <p className="text-sm font-semibold text-ink mb-1.5">How did the last two reps feel?</p>
                      <div className="flex gap-2">
                        {(["easy", "challenging"] as const).map((option) => (
                          <button
                            key={option}
                            type="button"
                            onClick={() => setEffort(group.id, option)}
                            aria-pressed={effortFor(group.id) === option}
                            className={`touch-target flex-1 rounded-full border text-sm font-semibold capitalize ${
                              effortFor(group.id) === option
                                ? "bg-action text-on-action border-action"
                                : "bg-ground text-ink-2 border-hairline"
                            }`}
                          >
                            {option}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}

                {hasPain && (
                  <label className="block">
                    <span className="text-sm font-semibold text-warn">What should your trainer know?</span>
                    <textarea
                      rows={2}
                      value={draft.painSummary}
                      onChange={(e) => updateDraft({ painSummary: e.target.value })}
                      className="mt-1 w-full p-3 rounded-xl bg-ground border border-warn-line text-ink text-base focus:outline-none focus:ring-2 focus:ring-ink resize-none"
                    />
                  </label>
                )}

                {draft.badge && <p className="text-xs text-muted">{draft.badge}</p>}

                {errorMessage && <p className="text-sm text-warn">{errorMessage}</p>}

                {!effortsAnswered && (
                  <p className="text-sm text-ink-2">Choose how each exercise felt to save.</p>
                )}

                <button
                  type="button"
                  onClick={handleConfirm}
                  disabled={!setsAreValid || saving}
                  className="w-full touch-target py-3 bg-action hover:bg-action-hover disabled:opacity-50 text-on-action font-semibold rounded-full text-base flex items-center justify-center gap-2"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  <span>{saving ? "Saving..." : "Confirm & Save Workout"}</span>
                </button>
                <button
                  type="button"
                  onClick={backToEditing}
                  className="w-full touch-target py-2 text-ink-2 text-sm font-semibold rounded-full"
                >
                  Back to my message
                </button>
              </section>
            ) : phase !== "saved" ? (
              /* Message box: typing is always available, voice just fills it in */
              <form onSubmit={handlePreview} className="bg-surface border border-hairline rounded-2xl p-4 space-y-3">
                <div>
                  <h2 className="font-display text-xl font-medium text-ink">How did it go?</h2>
                  <p className="text-sm text-ink-2 mt-0.5">
                    Say it however you want: "Bench 135, 3 sets of 10, shoulder felt good."
                  </p>
                </div>

                {phase === "clarify" && question && (
                  <div className="p-3 bg-ground border border-hairline rounded-xl rounded-bl-sm text-base text-ink">
                    {question}
                  </div>
                )}

                <div className="relative">
                  <textarea
                    rows={4}
                    value={draft.rawInput}
                    onChange={(e) => updateDraft({ rawInput: e.target.value })}
                    aria-label="Describe your workout"
                    placeholder="What did you lift? Anything feel off?"
                    className="w-full p-3 pr-14 rounded-xl bg-ground border border-hairline text-ink placeholder-muted text-base focus:outline-none focus:ring-2 focus:ring-ink resize-none"
                  />
                  {speechSupported && (
                    <button
                      type="button"
                      onClick={toggleListening}
                      aria-pressed={listening}
                      aria-label={listening ? "Stop dictation" : "Start dictation"}
                      className={`touch-target absolute right-2 top-2 rounded-full flex items-center justify-center ${
                        listening ? "bg-action text-on-action animate-pulse" : "bg-surface text-ink-2"
                      }`}
                    >
                      <Mic className="w-5 h-5" />
                    </button>
                  )}
                </div>

                {phase === "analyzing" && (
                  <p className="flex items-center gap-2 text-sm text-ink-2" role="status">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Workout Logger analyzing workout with {LOGGER_MODEL}...
                  </p>
                )}

                {phase === "error" && errorMessage && (
                  <p className="text-sm text-warn" role="alert">
                    {errorMessage}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={phase === "analyzing" || draft.rawInput.trim().length < 2}
                  className="w-full touch-target py-3 bg-action hover:bg-action-hover disabled:opacity-50 text-on-action font-semibold rounded-full text-base flex items-center justify-center gap-2"
                >
                  {phase === "error" && <RotateCcw className="w-4 h-4" />}
                  <span>
                    {phase === "analyzing" ? "Reading..." : phase === "error" ? "Try Again" : "Preview Workout"}
                  </span>
                </button>
              </form>
            ) : null}
          </>
        ) : null}

        {activeTab === "progress" && !loadError && (
          <section className="bg-surface border border-hairline rounded-2xl p-4">
            <h2 className="font-display text-xl font-medium text-ink mb-1">Your workouts</h2>
            <p className="text-sm text-ink-2 mb-4">Your most recent saved workouts.</p>

            {progress === null ? (
              <p className="text-sm text-muted">Loading...</p>
            ) : progress.length === 0 ? (
              <p className="text-sm text-muted">No workouts saved yet.</p>
            ) : (
              <div className="space-y-3">
                {progress.map((log) => (
                  <div key={log.id} className="p-3 bg-ground rounded-xl border border-hairline">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-semibold text-ink">
                        {new Date(log.logged_at).toLocaleDateString(undefined, {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                      {log.has_pain_flag && (
                        <span className="text-xs font-semibold text-warn bg-warn-bg px-2 py-0.5 rounded-full">
                          Pain noted
                        </span>
                      )}
                    </div>
                    {Array.from(new Set(log.sets.map((set) => set.exercise_id))).map((id) => {
                      const rows = log.sets.filter((set) => set.exercise_id === id);
                      return (
                        <div key={id} className="flex items-baseline justify-between gap-3 text-sm">
                          <span className="text-ink-2">{exerciseName(id)}</span>
                          <span className="text-ink font-semibold whitespace-nowrap">
                            {rows.map((set) => set.reps).join(", ")} reps
                            {rows.some((set) => set.weight_lbs)
                              ? ` @ ${Array.from(new Set(rows.map((set) => set.weight_lbs))).join(" / ")} lbs`
                              : ""}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
