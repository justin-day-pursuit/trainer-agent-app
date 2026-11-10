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
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  Loader2,
  Mic,
  RotateCcw,
  Send,
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
    message: string | null;
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

/** "3 × 10 @ 155 lbs" when every set matches, otherwise each set's reps. */
function summarizeSets(rows: { reps: string; weight: string }[]): string {
  const reps = rows.map((row) => row.reps);
  const weights = Array.from(new Set(rows.map((row) => row.weight).filter(Boolean)));
  const repsText = new Set(reps).size === 1 ? `${rows.length} × ${reps[0]}` : `${reps.join(", ")} reps`;
  return weights.length ? `${repsText} @ ${weights.join(" / ")} lbs` : `${repsText} (bodyweight)`;
}

/** The server stores UTC without a zone marker, so treat a bare timestamp as UTC. */
const timeLabel = (iso: string) =>
  new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });

/** Three steps so the client always knows where they are and whether anything was sent. */
function StepBar({ step }: { step: 1 | 2 | 3 }) {
  const labels = ["Tell us", "Check", "Sent"];
  return (
    <ol className="flex items-center gap-2" aria-label={`Step ${step} of 3: ${labels[step - 1]}`}>
      {labels.map((label, index) => {
        const n = index + 1;
        const done = n < step || step === 3;
        const current = n === step;
        return (
          <li key={label} className="flex flex-1 items-center gap-2 min-w-0">
            <span
              className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-extrabold ${
                done || current ? "bg-action text-on-action" : "border border-hairline text-muted"
              }`}
              aria-current={current ? "step" : undefined}
            >
              {done && !current ? <Check className="h-3.5 w-3.5" /> : n}
            </span>
            <span className={`truncate text-xs font-bold uppercase tracking-tight ${current ? "text-ink" : "text-muted"}`}>
              {label}
            </span>
            {n < 3 && <span className={`h-px flex-1 ${n < step ? "bg-action" : "bg-hairline"}`} />}
          </li>
        );
      })}
    </ol>
  );
}

/** The client's own message as a sent chat bubble. */
function SentBubble({ message, sentAt }: { message: string; sentAt: string | null }) {
  return (
    <div className="flex flex-col items-end gap-1">
      <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-action px-4 py-3 text-base text-on-action">{message}</p>
      <p className="flex items-center gap-1 text-xs font-semibold text-success">
        <Check className="h-3.5 w-3.5" />
        Sent to your trainer{sentAt ? ` · ${timeLabel(sentAt)}` : ""}
      </p>
    </div>
  );
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
  const [emptyHint, setEmptyHint] = useState(false);
  const [openIds, setOpenIds] = useState<string[]>([]);
  const stepTopRef = useRef<HTMLElement | null>(null);

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

  // Bring each new step into view so the change is impossible to miss
  const step: 1 | 2 | 3 = isPending || phase === "saved" ? 3 : phase === "review" ? 2 : 1;
  useEffect(() => {
    if (step > 1) stepTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [step]);

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
    if (phase === "analyzing") return;
    if (draft.rawInput.trim().length < 2) {
      setEmptyHint(true);
      return;
    }
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
      setOpenIds(Array.from(new Set(result.extracted_sets.filter((set) => set.pain_flag).map((set) => set.exercise_id))));
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
      <header className="relative px-4 py-3 bg-ground border-b border-hairline sticky top-0 z-20 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex items-center gap-2 min-w-0">
          <Link href="/" className="touch-target -ml-2 flex items-center justify-center text-muted hover:text-ink" aria-label="Back to home">
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
        <div className="flex w-full sm:w-auto flex-shrink-0 bg-surface p-0.5 rounded-full border border-hairline">
          <button
            onClick={() => setActiveTab("workout")}
            className={`touch-target flex-1 sm:flex-none px-4 text-sm font-semibold rounded-full whitespace-nowrap transition-colors ${
              activeTab === "workout" ? "bg-action text-on-action" : "text-muted"
            }`}
          >
            Today's Log
          </button>
          <button
            onClick={() => setActiveTab("progress")}
            className={`touch-target flex-1 sm:flex-none px-4 text-sm font-semibold rounded-full whitespace-nowrap transition-colors ${
              activeTab === "progress" ? "bg-action text-on-action" : "text-muted"
            }`}
          >
            My Progress
          </button>
        </div>
        {activeTab === "workout" && !loadError && session && (
          <div className="w-full pt-1">
            <StepBar step={step} />
          </div>
        )}
      </header>

      <div className="flex-1 scrollable-container p-4 space-y-4">
        {loadError && (
          <div className="p-4 bg-warn-bg border border-warn-line rounded-xl text-warn text-base">{loadError}</div>
        )}

        {activeTab === "workout" && !loadError && isPending ? (
          /* Waiting on the trainer: this stays in place through reloads until they approve */
          <section ref={stepTopRef} className="space-y-4 scroll-mt-48">
            <div className="p-4 bg-success-bg border border-success-line rounded-2xl" role="status">
              <p className="flex items-center gap-2 font-display text-xl font-extrabold tracking-tight text-success">
                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                Sent to your trainer. Great work.
              </p>
              <p className="text-base text-ink-2 mt-1">
                They&apos;ll review it and unlock next week&apos;s targets. This page updates on its own.
              </p>
            </div>

            {session?.last_session?.message && (
              <SentBubble message={session.last_session.message} sentAt={session.last_session.logged_at} />
            )}

            <div className="bg-surface border border-hairline rounded-2xl p-4 space-y-3">
              <h2 className="section-title font-display text-lg text-ink">What you logged</h2>
              {Array.from(new Set((session?.last_session?.sets ?? []).map((set) => set.exercise_id))).map((id) => {
                const rows = (session?.last_session?.sets ?? []).filter((set) => set.exercise_id === id);
                const effort = rows.find((set) => set.effort)?.effort;
                const hadPain = rows.some((set) => set.pain_flag);
                return (
                  <div key={id} className="p-3 bg-ground rounded-xl border border-hairline">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-base font-semibold text-ink">{exerciseName(id)}</span>
                      {effort && (
                        <span className={`text-sm font-semibold capitalize ${effort === "challenging" ? "text-warn" : "text-success"}`}>{effort}</span>
                      )}
                    </div>
                    <p className="text-sm text-ink-2">
                      {rows.map((set) => set.reps).join(", ")} reps
                      {rows.some((set) => set.weight_lbs)
                        ? ` @ ${Array.from(new Set(rows.map((set) => set.weight_lbs))).join(" / ")} lbs`
                        : ""}
                    </p>
                    {hadPain && <p className="text-sm font-semibold text-danger mt-1">Pain noted</p>}
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
                  <span>Sent to your trainer. They&apos;re reviewing next week.</span>
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
              <h2 className="section-title font-display text-lg text-ink mb-3">Today's session</h2>
              {session ? (
                <ul className="space-y-2">
                  {exercises.map((exercise) => (
                    <li key={exercise.exercise_id} className="flex items-baseline justify-between gap-3">
                      <span className="text-base text-ink">{exercise.name}</span>
                      <span className="text-sm font-semibold text-action whitespace-nowrap">
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
              <section ref={stepTopRef} className="bg-surface border border-hairline rounded-2xl p-4 space-y-4 scroll-mt-48">
                <div>
                  <h2 className="section-title font-display text-lg text-ink">Check your sets</h2>
                  <p className="text-sm text-ink-2 mt-0.5">
                    Not sent yet. Tap an exercise to fix a number, then send it to your trainer.
                  </p>
                </div>

                <div className="flex flex-col items-end gap-1">
                  <p className="max-w-[85%] rounded-2xl rounded-br-sm border border-hairline bg-ground px-4 py-3 text-sm text-ink-2">
                    {draft.rawInput}
                  </p>
                  <p className="text-xs font-semibold text-muted">Draft · not sent</p>
                </div>

                {groupedSets.map((group) => (
                  <div key={group.id} className="space-y-2 rounded-xl border border-hairline bg-ground p-3">
                    <button
                      type="button"
                      onClick={() =>
                        setOpenIds((ids) => (ids.includes(group.id) ? ids.filter((id) => id !== group.id) : [...ids, group.id]))
                      }
                      aria-expanded={openIds.includes(group.id)}
                      className="touch-target flex w-full items-center justify-between gap-3 text-left"
                    >
                      <span className="min-w-0">
                        <span className="block text-base font-bold tracking-tight text-ink">{exerciseName(group.id)}</span>
                        <span className="flex flex-wrap items-center gap-2 text-sm font-semibold text-action">
                          {summarizeSets(group.rows)}
                          {group.rows.some((set) => set.painFlag) && (
                            <span className="rounded-full bg-danger px-2 py-0.5 text-xs font-bold text-on-action">Pain flagged</span>
                          )}
                        </span>
                      </span>
                      <span className="flex flex-shrink-0 items-center gap-1 text-xs font-semibold text-muted">
                        {openIds.includes(group.id) ? "Done" : "Edit"}
                        <ChevronDown className={`h-4 w-4 transition-transform ${openIds.includes(group.id) ? "rotate-180" : ""}`} />
                      </span>
                    </button>
                    {openIds.includes(group.id) && group.rows.map((set, index) => (
                      <div
                        key={set.key}
                        className={`p-3 rounded-xl border space-y-2 ${
                          set.painFlag ? "bg-danger-bg border-danger" : "bg-surface border-hairline"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-6 text-sm font-semibold text-action text-center">{index + 1}</span>
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
                              ? "bg-danger text-on-action border-danger"
                              : "bg-ground text-muted border-hairline"
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
                                ? option === "easy"
                                  ? "bg-action text-on-action border-action"
                                  : "bg-warn text-on-action border-warn"
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
                    <span className="text-sm font-semibold text-danger">What should your trainer know about the pain?</span>
                    <textarea
                      rows={2}
                      value={draft.painSummary}
                      onChange={(e) => updateDraft({ painSummary: e.target.value })}
                      className="mt-1 w-full p-3 rounded-xl bg-ground border border-danger text-ink text-base focus:outline-none focus:ring-2 focus:ring-ink resize-none"
                    />
                  </label>
                )}

                {draft.badge && <p className="text-xs text-muted">{draft.badge}</p>}

                <button
                  type="button"
                  onClick={backToEditing}
                  className="w-full touch-target py-2 text-ink-2 text-sm font-semibold rounded-full"
                >
                  Back to my message
                </button>
                {/* Room for the pinned send bar */}
                <div className="h-28" aria-hidden="true" />

                <div
                  className="fixed bottom-0 left-1/2 z-30 w-full max-w-md -translate-x-1/2 space-y-2 border-t border-hairline bg-ground/95 px-4 pt-3 backdrop-blur"
                  style={{ paddingBottom: "calc(1rem + var(--safe-bottom))" }}
                >
                  {errorMessage && <p className="text-sm text-warn" role="alert">{errorMessage}</p>}
                  {!effortsAnswered && (
                    <p className="text-sm text-ink-2">Pick Easy or Challenging for each exercise to send.</p>
                  )}
                  <button
                    type="button"
                    onClick={handleConfirm}
                    disabled={!setsAreValid || saving}
                    className="w-full touch-target py-3 bg-action hover:bg-action-hover disabled:opacity-50 text-on-action font-bold rounded-full text-base flex items-center justify-center gap-2"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    <span>{saving ? "Sending..." : "Send to Trainer"}</span>
                  </button>
                </div>
              </section>
            ) : phase !== "saved" ? (
              /* Message box: typing is always available, voice just fills it in */
              <form onSubmit={handlePreview} className="bg-surface border border-hairline rounded-2xl p-4 space-y-3">
                <div>
                  <h2 className="section-title font-display text-lg text-ink">How did it go?</h2>
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
                    onChange={(e) => {
                      updateDraft({ rawInput: e.target.value });
                      setEmptyHint(false);
                    }}
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
                        listening ? "bg-action text-on-action mic-listening" : "bg-surface text-action border border-hairline"
                      }`}
                    >
                      <Mic className="w-5 h-5" />
                    </button>
                  )}
                </div>

                {phase === "analyzing" && (
                  <div className="space-y-3 rounded-xl border border-action bg-ground p-4" role="status">
                    <p className="flex items-center gap-2 text-base font-bold text-ink">
                      <Loader2 className="w-5 h-5 animate-spin text-action" />
                      Reading your workout...
                    </p>
                    <p className="text-sm text-ink-2">Turning your message into sets. This takes a few seconds.</p>
                    <div className="space-y-2" aria-hidden="true">
                      {[0, 1, 2].map((i) => (
                        <div key={i} className="h-3 animate-pulse rounded-full bg-hairline" style={{ width: `${90 - i * 20}%` }} />
                      ))}
                    </div>
                    <p className="text-xs text-muted">Read by {LOGGER_MODEL}</p>
                  </div>
                )}

                {emptyHint && (
                  <p className="text-sm font-semibold text-warn" role="alert">
                    Tell us what you lifted first. Type it, or tap the mic and say it.
                  </p>
                )}

                {phase === "error" && errorMessage && (
                  <p className="text-sm text-warn" role="alert">
                    {errorMessage}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={phase === "analyzing"}
                  className="w-full touch-target py-3 bg-action hover:bg-action-hover disabled:opacity-50 text-on-action font-semibold rounded-full text-base flex items-center justify-center gap-2"
                >
                  {phase === "error" && <RotateCcw className="w-4 h-4" />}
                  <span>
                    {phase === "analyzing" ? "Reading..." : phase === "error" ? "Try Again" : "Next: Check My Sets"}
                  </span>
                </button>
                <p className="text-center text-xs text-muted">Not sent yet. You&apos;ll check your sets, then send them to your trainer.</p>
              </form>
            ) : null}
          </>
        ) : null}

        {activeTab === "progress" && !loadError && (
          <section className="bg-surface border border-hairline rounded-2xl p-4">
            <h2 className="section-title font-display text-lg text-ink mb-1">Your workouts</h2>
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
                        <span className="text-xs font-semibold text-danger bg-danger-bg px-2 py-0.5 rounded-full">
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
