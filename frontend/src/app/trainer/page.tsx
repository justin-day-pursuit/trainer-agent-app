"use client";

/**
 * Trainer Dashboard: Weekly Plan Review (/trainer).
 *
 * Shows each client's drafted next week beside what they did last week, with the reason
 * for every change. Human-in-the-Loop: nothing reaches a client until the trainer
 * approves it here, and any target can be edited first.
 */

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Copy, Loader2, Plus, Search, ShieldCheck, Trash2 } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import ClientRoster from "@/components/ClientRoster";
import TriageFeed from "@/components/TriageFeed";
import type { Effort, RosterClient, SafetyFlag, TriageCard } from "@/types";

interface DraftExercise {
  exercise_id: string;
  name: string;
  sets: number;
  target_reps: number;
  target_weight_lbs: number | null;
  previous_reps?: number;
  previous_weight_lbs?: number | null;
  last_reps?: number[];
  last_weight_label?: string | null;
  effort?: Effort | null;
  pain_reported?: boolean;
  pain_note?: string | null;
  reason?: string;
  hold_progression?: boolean;
}

interface PendingPlan {
  id: number;
  review_group: "auto_approve" | "attention_required";
  badges: string[];
  client_id: number;
  client_name: string;
  week_label: string;
  last_workout_at: string | null;
  overall_effort: Effort | null;
  exercises: DraftExercise[];
  safety_flags: SafetyFlag[];
}

interface EditValues {
  reps: string;
  weight: string;
}

interface StartingRow {
  key: number;
  name: string;
  sets: string;
  reps: string;
  weight: string;
}

const blankRow = (key: number): StartingRow => ({ key, name: "", sets: "3", reps: "8", weight: "" });

const effortLabel = (effort?: Effort | null) =>
  effort === "easy" ? "Easy" : effort === "challenging" ? "Challenging" : "Not rated";

const weightLabel = (weight?: number | null) => (weight === null || weight === undefined ? "BW" : `${weight} lbs`);

function lastWeekSummary(exercise: DraftExercise): string {
  if (!exercise.last_reps || exercise.last_reps.length === 0) return "Not logged";
  return `${exercise.last_reps.join(", ")} reps @ ${exercise.last_weight_label ?? "BW"}`;
}

export default function TrainerDashboardPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<PendingPlan[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [busyPlanId, setBusyPlanId] = useState<number | null>(null);
  const [cardError, setCardError] = useState<{ planId: number; message: string } | null>(null);
  const [editingPlanId, setEditingPlanId] = useState<number | null>(null);
  const [edits, setEdits] = useState<Record<string, EditValues>>({});
  const [toast, setToast] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);

  const [triageCards, setTriageCards] = useState<TriageCard[]>([]);
  const [roster, setRoster] = useState<RosterClient[]>([]);

  const [addingClient, setAddingClient] = useState(false);
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [clientGoal, setClientGoal] = useState("");
  const [clientInjuries, setClientInjuries] = useState("");
  const [startingRows, setStartingRows] = useState<StartingRow[]>([blankRow(0)]);
  const [nextRowKey, setNextRowKey] = useState(1);
  const [savingClient, setSavingClient] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [newClientLink, setNewClientLink] = useState<{ name: string; url: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const authToken = useCallback(async () => {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token;
  }, []);

  const handleAuthError = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError && error.status === 401) {
        router.replace("/trainer/login");
        return true;
      }
      return false;
    },
    [router]
  );

  useEffect(() => {
    authToken()
      .then((token) => apiFetch<{ pending_plans: PendingPlan[] }>("/trainer/dashboard", { token }))
      .then((data) => setPlans(data.pending_plans))
      .catch((error) => {
        if (!handleAuthError(error)) setLoadError("We couldn't load your plans. Refresh to try again.");
      });
  }, [authToken, handleAuthError]);

  // Loaded separately so a slow check-in draft never holds up the plan review queue
  const loadTriage = useCallback(async () => {
    try {
      const token = await authToken();
      const data = await apiFetch<{ triage_cards: TriageCard[]; roster: RosterClient[] }>("/trainer/triage", { token });
      setTriageCards(data.triage_cards);
      setRoster(data.roster);
    } catch (error) {
      handleAuthError(error);
    }
  }, [authToken, handleAuthError]);

  useEffect(() => {
    loadTriage();
  }, [loadTriage]);

  const dismissCard = async (cardId: number) => {
    const token = await authToken();
    await apiFetch(`/trainer/triage/${cardId}/dismiss`, { method: "POST", token });
    setTriageCards((cards) => cards.filter((card) => card.id !== cardId));
  };

  const getClientLink = async (client: RosterClient) => {
    let sessionToken = client.session_token;
    if (!sessionToken) {
      const token = await authToken();
      const created = await apiFetch<{ session_token: string }>(`/clients/${client.client_id}/sessions`, { method: "POST", token });
      sessionToken = created.session_token;
      loadTriage();
    }
    return `${window.location.origin}/s/${sessionToken}`;
  };

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(timer);
  }, [toast]);

  const startEditing = (plan: PendingPlan) => {
    const values: Record<string, EditValues> = {};
    plan.exercises.forEach((exercise) => {
      values[exercise.exercise_id] = {
        reps: String(exercise.target_reps),
        weight: exercise.target_weight_lbs === null ? "" : String(exercise.target_weight_lbs),
      };
    });
    setEdits(values);
    setEditingPlanId(plan.id);
    setCardError(null);
  };

  const editsAreValid = Object.values(edits).every(
    (value) => /^\d+$/.test(value.reps) && Number(value.reps) > 0 && (value.weight === "" || /^\d+(\.\d+)?$/.test(value.weight))
  );

  const handleApprove = async (plan: PendingPlan) => {
    setBusyPlanId(plan.id);
    setCardError(null);
    try {
      const token = await authToken();
      if (editingPlanId === plan.id) {
        await apiFetch(`/trainer/plans/${plan.id}`, {
          method: "PUT",
          token,
          body: JSON.stringify({
            exercises: plan.exercises.map((exercise) => ({
              exercise_id: exercise.exercise_id,
              target_reps: Number(edits[exercise.exercise_id].reps),
              target_weight_lbs:
                edits[exercise.exercise_id].weight === "" ? null : Number(edits[exercise.exercise_id].weight),
            })),
          }),
        });
      }
      await apiFetch(`/trainer/plans/${plan.id}/approve`, { method: "POST", token });
      setPlans((current) => (current ?? []).filter((item) => item.id !== plan.id));
      setEditingPlanId(null);
      setToast(`${plan.client_name}'s plan is live on their link.`);
    } catch (error) {
      if (!handleAuthError(error)) {
        setCardError({
          planId: plan.id,
          message: error instanceof ApiError ? error.message : "We couldn't approve that. Try again.",
        });
      }
    } finally {
      setBusyPlanId(null);
    }
  };

  const resetClientForm = () => {
    setClientName("");
    setClientEmail("");
    setClientPhone("");
    setClientGoal("");
    setClientInjuries("");
    setStartingRows([blankRow(0)]);
    setNextRowKey(1);
    setAddError(null);
  };

  const updateRow = (key: number, patch: Partial<StartingRow>) => {
    setStartingRows((rows) => rows.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  };

  const startingPlanIsValid =
    clientName.trim().length > 0 &&
    startingRows.length > 0 &&
    startingRows.every(
      (row) =>
        row.name.trim().length > 0 &&
        /^[1-9]\d*$/.test(row.sets) &&
        /^[1-9]\d*$/.test(row.reps) &&
        (row.weight === "" || /^\d+(\.\d+)?$/.test(row.weight))
    );

  const handleAddClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!startingPlanIsValid || savingClient) return;
    setSavingClient(true);
    setAddError(null);
    try {
      const token = await authToken();
      const created = await apiFetch<{ full_name: string; session_token: string }>("/trainer/clients", {
        method: "POST",
        token,
        body: JSON.stringify({
          full_name: clientName,
          email: clientEmail.trim() || null,
          phone: clientPhone.trim() || null,
          primary_goal: clientGoal.trim() || null,
          injuries: clientInjuries.split(","),
          exercises: startingRows.map((row) => ({
            name: row.name.trim(),
            sets: Number(row.sets),
            target_reps: Number(row.reps),
            target_weight_lbs: row.weight === "" ? null : Number(row.weight),
          })),
        }),
      });
      setNewClientLink({ name: created.full_name, url: `${window.location.origin}/s/${created.session_token}` });
      setCopied(false);
      setAddingClient(false);
      resetClientForm();
      loadTriage();
    } catch (error) {
      if (!handleAuthError(error)) {
        setAddError(error instanceof ApiError ? error.message : "We couldn't add that client. Try again.");
      }
    } finally {
      setSavingClient(false);
    }
  };

  const copyLink = async () => {
    if (!newClientLink) return;
    try {
      await navigator.clipboard.writeText(newClientLink.url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const routinePlans = (plans ?? []).filter((plan) => plan.review_group === "auto_approve");

  const handleApproveAll = async () => {
    setBulkBusy(true);
    setBulkError(null);
    try {
      const token = await authToken();
      const result = await apiFetch<{ approved_plan_ids: number[] }>("/trainer/plans/approve-batch", {
        method: "POST",
        token,
        body: JSON.stringify({ plan_ids: routinePlans.map((plan) => plan.id) }),
      });
      const approved = new Set(result.approved_plan_ids);
      setPlans((current) => (current ?? []).filter((plan) => !approved.has(plan.id)));
      setEditingPlanId(null);
      setToast(`${approved.size} ${approved.size === 1 ? "plan is" : "plans are"} now live.`);
    } catch (error) {
      if (!handleAuthError(error)) {
        setBulkError(error instanceof ApiError ? error.message : "We couldn't approve those. Try again.");
      }
    } finally {
      setBulkBusy(false);
    }
  };

  const visiblePlans = (plans ?? []).filter((plan) =>
    plan.client_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const groups = [
    {
      key: "auto_approve",
      title: "Auto-Approve",
      subtitle: "Felt easy, no pain, standard progression.",
      plans: visiblePlans.filter((plan) => plan.review_group === "auto_approve"),
    },
    {
      key: "attention_required",
      title: "Attention Required",
      subtitle: "Review each of these yourself before the client sees it.",
      plans: visiblePlans.filter((plan) => plan.review_group === "attention_required"),
    },
  ];

  const textField =
    "w-full h-11 px-3 rounded-lg bg-ground border border-hairline text-sm font-normal text-ink placeholder-muted focus:outline-none focus:ring-2 focus:ring-ink";

  const editField =
    "w-16 h-10 text-center rounded-lg bg-ground border border-hairline text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-ink";

  return (
    <div className="flex-1 flex flex-col h-full bg-ground text-ink">
      <header className="px-4 py-3 bg-surface border-b border-hairline sticky top-0 z-20 flex items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-2">
          <div className="p-1.5 bg-ground rounded-lg text-ink-2">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-display text-base font-medium text-ink">Trainer Dashboard</h1>
            <p className="text-sm text-muted">Weekly plan review</p>
          </div>
        </Link>
        <button
          onClick={() => {
            setAddingClient((open) => !open);
            setNewClientLink(null);
          }}
          aria-expanded={addingClient}
          className="touch-target px-4 bg-action hover:bg-action-hover text-on-action rounded-full text-sm font-semibold flex items-center gap-1.5 flex-shrink-0 whitespace-nowrap"
        >
          <Plus className="w-4 h-4" />
          <span>Add client</span>
        </button>
      </header>

      {newClientLink && (
        <section className="mx-4 mt-3 p-4 bg-success-bg border border-success-line rounded-2xl space-y-2">
          <p className="text-base font-semibold text-success">{newClientLink.name} is ready. Send them this private link:</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 min-w-0 truncate p-2.5 bg-ground border border-hairline rounded-lg text-sm text-ink">{newClientLink.url}</code>
            <button
              onClick={copyLink}
              className="touch-target px-4 bg-action hover:bg-action-hover text-on-action rounded-full text-sm font-semibold flex items-center gap-1.5 flex-shrink-0"
            >
              <Copy className="w-4 h-4" />
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
          </div>
        </section>
      )}

      {addingClient && (
        <form onSubmit={handleAddClient} className="mx-4 mt-3 p-4 bg-surface border border-hairline rounded-2xl space-y-4">
          <h2 className="font-display text-lg font-medium text-ink">Add a client</h2>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="block text-sm font-semibold text-ink">
              Name
              <input value={clientName} onChange={(e) => setClientName(e.target.value)} className={`${textField} mt-1`} />
            </label>
            <label className="block text-sm font-semibold text-ink">
              Email
              <input type="email" value={clientEmail} onChange={(e) => setClientEmail(e.target.value)} className={`${textField} mt-1`} />
            </label>
            <label className="block text-sm font-semibold text-ink">
              Phone
              <input type="tel" value={clientPhone} onChange={(e) => setClientPhone(e.target.value)} className={`${textField} mt-1`} />
            </label>
            <label className="block text-sm font-semibold text-ink">
              Goals
              <input value={clientGoal} onChange={(e) => setClientGoal(e.target.value)} placeholder="Build muscle" className={`${textField} mt-1`} />
            </label>
            <label className="block text-sm font-semibold text-ink">
              Injuries, separated by commas
              <input value={clientInjuries} onChange={(e) => setClientInjuries(e.target.value)} placeholder="Left knee, lower back" className={`${textField} mt-1`} />
            </label>
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-ink">Starting plan</h3>
            {startingRows.map((row, index) => (
              <div key={row.key} className="flex flex-wrap items-center gap-2">
                <input
                  value={row.name}
                  onChange={(e) => updateRow(row.key, { name: e.target.value })}
                  aria-label={`Exercise ${index + 1} name`}
                  placeholder="Exercise name"
                  className={`${textField} flex-1 basis-full md:basis-0 min-w-0`}
                />
                <label className="flex items-center gap-1 text-sm text-ink-2">
                  <input inputMode="numeric" value={row.sets} onChange={(e) => updateRow(row.key, { sets: e.target.value })} aria-label={`Exercise ${index + 1} sets`} className={editField} />
                  sets
                </label>
                <label className="flex items-center gap-1 text-sm text-ink-2">
                  <input inputMode="numeric" value={row.reps} onChange={(e) => updateRow(row.key, { reps: e.target.value })} aria-label={`Exercise ${index + 1} reps`} className={editField} />
                  reps
                </label>
                <label className="flex items-center gap-1 text-sm text-ink-2">
                  <input inputMode="decimal" value={row.weight} onChange={(e) => updateRow(row.key, { weight: e.target.value })} aria-label={`Exercise ${index + 1} weight in pounds`} placeholder="BW" className={editField} />
                  lbs
                </label>
                <button
                  type="button"
                  onClick={() => setStartingRows((rows) => rows.filter((item) => item.key !== row.key))}
                  disabled={startingRows.length === 1}
                  aria-label={`Remove exercise ${index + 1}`}
                  className="touch-target flex items-center justify-center text-muted hover:text-ink disabled:opacity-40"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => {
                setStartingRows((rows) => [...rows, blankRow(nextRowKey)]);
                setNextRowKey((key) => key + 1);
              }}
              className="touch-target px-4 border border-dashed border-hairline text-ink-2 rounded-full text-sm font-semibold"
            >
              Add exercise
            </button>
          </div>

          {addError && <p className="text-sm text-warn" role="alert">{addError}</p>}

          <button
            type="submit"
            disabled={!startingPlanIsValid || savingClient}
            className="touch-target px-8 bg-action hover:bg-action-hover disabled:opacity-50 text-on-action font-semibold rounded-full text-sm"
          >
            {savingClient ? "Saving..." : "Save & Create Link"}
          </button>
        </form>
      )}

      {toast && (
        <div role="status" className="mx-4 mt-3 p-3 bg-success-bg border border-success-line rounded-xl flex items-center gap-2 text-success text-sm font-semibold">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      <div className="px-4 pt-4 pb-2">
        <div className="relative max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted" />
          <input
            type="text"
            placeholder="Search clients..."
            aria-label="Search clients"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-surface border border-hairline rounded-xl text-sm text-ink placeholder-muted focus:outline-none focus:ring-1 focus:ring-ink"
          />
        </div>
      </div>

      <div className="flex-1 scrollable-container p-4 space-y-4">
        <TriageFeed cards={triageCards} onDismiss={dismissCard} />

        {loadError && <p className="p-4 bg-warn-bg border border-warn-line rounded-xl text-warn text-base">{loadError}</p>}
        {!loadError && plans === null && <p className="text-sm text-muted">Loading plans...</p>}
        {plans !== null && visiblePlans.length === 0 && !loadError && (
          <p className="text-base text-ink-2">
            {plans.length === 0 ? "No plans waiting for review. New drafts appear here after clients log workouts." : "No clients match that search."}
          </p>
        )}

        {groups.map((group) =>
          group.plans.length === 0 ? null : (
            <section key={group.key} className="space-y-3" aria-label={group.title}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className={`font-display text-lg font-medium ${group.key === "auto_approve" ? "text-success" : "text-danger"}`}>
                    {group.title} ({group.plans.length})
                  </h2>
                  <p className="text-sm text-ink-2">{group.subtitle}</p>
                </div>
                {group.key === "auto_approve" && routinePlans.length > 0 && (
                  <button
                    onClick={handleApproveAll}
                    disabled={bulkBusy}
                    className="touch-target px-6 bg-action hover:bg-action-hover disabled:opacity-50 text-on-action font-semibold rounded-full text-sm flex items-center gap-1.5"
                  >
                    {bulkBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                    <span>Approve All ({routinePlans.length}) Drafts</span>
                  </button>
                )}
              </div>
              {group.key === "auto_approve" && bulkError && <p className="text-sm text-warn" role="alert">{bulkError}</p>}
              {group.plans.map((plan) => {
          const editing = editingPlanId === plan.id;
          const busy = busyPlanId === plan.id;
          return (
            <article key={plan.id} className="p-4 rounded-2xl border bg-surface border-hairline space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-display text-lg font-medium text-ink">{plan.client_name}</h3>
                  {plan.badges.map((badge) => (
                    <span
                      key={badge}
                      className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                        badge === "Pain Reported" ? "bg-danger text-on-action" : "bg-danger-bg text-danger"
                      }`}
                    >
                      {badge}
                    </span>
                  ))}
                </div>
                <p className="text-sm text-ink-2">
                  {plan.last_workout_at
                    ? `Last workout ${new Date(plan.last_workout_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`
                    : "No workout logged"}
                  {" · "}
                  Session effort: {effortLabel(plan.overall_effort)}
                  {" · "}
                  {plan.week_label}
                </p>
              </div>

              {plan.safety_flags.map((flag, index) => (
                <div key={index} role="alert" className="p-3 bg-warn-bg border border-warn-line rounded-xl flex items-start gap-2 text-sm text-warn">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">{flag.message}</p>
                    <p>Weight is held. Keep the freeze, ask for a form video, or swap the exercise.</p>
                  </div>
                </div>
              ))}

              <div className="hidden md:grid grid-cols-[1.1fr_1fr_1fr_1.4fr] gap-3 px-3 text-xs font-semibold text-muted">
                <span>Exercise</span>
                <span>Last week</span>
                <span>Next week</span>
                <span>Why</span>
              </div>

              <ul className="space-y-2">
                {plan.exercises.map((exercise) => (
                  <li
                    key={exercise.exercise_id}
                    className={`p-3 rounded-xl border grid grid-cols-1 md:grid-cols-[1.1fr_1fr_1fr_1.4fr] gap-x-3 gap-y-1 md:items-center ${
                      exercise.pain_reported ? "bg-warn-bg border-warn-line" : "bg-ground border-hairline"
                    }`}
                  >
                    <span className="text-base font-semibold text-ink">{exercise.name}</span>
                    <span className="text-sm text-ink-2">
                      <span className="md:hidden font-semibold">Last week: </span>
                      {lastWeekSummary(exercise)} · {effortLabel(exercise.effort)}
                    </span>
                    {editing ? (
                      <span className="flex items-center gap-1 text-sm text-ink-2">
                        <span>{exercise.sets} ×</span>
                        <input
                          inputMode="numeric"
                          aria-label={`${exercise.name} target reps`}
                          value={edits[exercise.exercise_id]?.reps ?? ""}
                          onChange={(e) =>
                            setEdits((c) => ({ ...c, [exercise.exercise_id]: { ...c[exercise.exercise_id], reps: e.target.value } }))
                          }
                          className={editField}
                        />
                        <span>@</span>
                        <input
                          inputMode="decimal"
                          aria-label={`${exercise.name} target weight in pounds`}
                          placeholder="BW"
                          value={edits[exercise.exercise_id]?.weight ?? ""}
                          onChange={(e) =>
                            setEdits((c) => ({ ...c, [exercise.exercise_id]: { ...c[exercise.exercise_id], weight: e.target.value } }))
                          }
                          className={editField}
                        />
                      </span>
                    ) : (
                      <span className="text-sm font-semibold text-ink">
                        <span className="md:hidden">Next week: </span>
                        {exercise.sets} × {exercise.target_reps} @ {weightLabel(exercise.target_weight_lbs)}
                      </span>
                    )}
                    <span className="text-sm text-ink-2">{exercise.reason}</span>
                  </li>
                ))}
              </ul>

              {cardError?.planId === plan.id && <p className="text-sm text-warn" role="alert">{cardError.message}</p>}

              <div className="flex items-center gap-2">
                {(plan.review_group === "attention_required" || editing) && (
                <button
                  onClick={() => handleApprove(plan)}
                  disabled={busy || (editing && !editsAreValid)}
                  className="touch-target flex-1 md:flex-none md:px-8 py-2 bg-action hover:bg-action-hover disabled:opacity-50 text-on-action font-semibold rounded-full text-sm flex items-center justify-center gap-1.5"
                >
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  <span>{editing ? "Save & Approve" : "Approve Draft"}</span>
                </button>
                )}
                <button
                  onClick={() => (editing ? setEditingPlanId(null) : startEditing(plan))}
                  disabled={busy}
                  className="touch-target px-4 py-2 border border-hairline hover:bg-hairline text-ink-2 rounded-full text-sm font-semibold"
                >
                  {editing ? "Cancel" : "Edit Target"}
                </button>
              </div>
            </article>
          );
              })}
            </section>
          )
        )}

        {roster.length > 0 && <ClientRoster clients={roster} getClientLink={getClientLink} />}
      </div>
    </div>
  );
}
