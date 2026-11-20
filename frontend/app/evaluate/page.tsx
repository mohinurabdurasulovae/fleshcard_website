"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { BookOpenText, Check, EyeOff, Info, SkipForward, Trash2, UserRound } from "lucide-react";
import { PageHeader } from "@/components/app-shell";
import { CategoryBadge, SubjectBadge, TypeBadge } from "@/components/badges";
import { CategoryToggle, SubjectPills } from "@/components/filters";
import { SourceLine } from "@/components/flashcard-view";
import { Inline, NoteText } from "@/components/rich-text";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { api, useApi, useMeta, type Flashcard } from "@/lib/api";
import { RATING_STYLE, cn, qs, timeAgo } from "@/lib/utils";

function useEvaluator() {
  const [name, setName] = React.useState("");
  React.useEffect(() => {
    try { setName(localStorage.getItem("evaluator") || ""); } catch {}
  }, []);
  const save = (v: string) => { setName(v); try { localStorage.setItem("evaluator", v); } catch {} };
  return [name, save] as const;
}

function EvaluateInner() {
  const sp = useSearchParams();
  const router = useRouter();
  const cardParam = sp.get("card");
  const { data: meta } = useMeta();
  const [evaluator, setEvaluator] = useEvaluator();
  const [nameDraft, setNameDraft] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [blind, setBlind] = React.useState(true);
  const [skipped, setSkipped] = React.useState<number[]>([]);
  const [overall, setOverall] = React.useState<number | null>(null);
  const [criteria, setCriteria] = React.useState<Record<string, number>>({});
  const [comment, setComment] = React.useState("");
  const [showExcerpt, setShowExcerpt] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [toast, setToast] = React.useState("");
  const who = evaluator || "anonymous";

  const { data: next, mutate: mutateNext, isLoading } = useApi<{ card: Flashcard | null; remaining: number; rated_by_you: number }>(
    cardParam ? null : `/api/evaluations/next${qs({ evaluator: who, category, subject, exclude: skipped.join(",") })}`,
  );
  const { data: specific } = useApi<Flashcard & { evaluation_list: any[] }>(cardParam ? `/api/flashcards/${cardParam}` : null);
  const { data: mine, mutate: mutateMine } = useApi<{ total: number; items: any[] }>(`/api/evaluations${qs({ evaluator: who, limit: 8 })}`);
  const card = cardParam ? specific : next?.card;

  // prefill when this evaluator already rated the specific card
  React.useEffect(() => {
    setOverall(null); setCriteria({}); setComment("");
    if (specific && cardParam) {
      const prev = specific.evaluation_list?.find((e: any) => e.evaluator === who);
      if (prev) { setOverall(prev.overall); setCriteria(prev.criteria || {}); setComment(prev.comment || ""); }
    }
  }, [card?.id, specific, cardParam, who]);

  const submit = React.useCallback(async () => {
    if (!card || !overall) return;
    setSaving(true);
    try {
      const r = await api.post("/api/evaluations", { flashcard_id: card.id, overall, criteria, comment, evaluator: who });
      setToast(r.updated ? "Evaluation updated" : "Evaluation saved");
      setTimeout(() => setToast(""), 1800);
      mutateMine();
      if (cardParam) router.replace("/evaluate");
      else mutateNext();
    } catch (e: any) { setToast(e.message); } finally { setSaving(false); }
  }, [card, overall, criteria, comment, who, cardParam, router, mutateMine, mutateNext]);

  React.useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName.match(/INPUT|TEXTAREA|SELECT/)) return;
      if (["1", "2", "3", "4", "5"].includes(e.key)) setOverall(Number(e.key));
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [submit]);

  const skip = () => { if (card) { if (cardParam) router.replace("/evaluate"); else setSkipped((s) => [...s, card.id]); } };
  const macros = card?.document.katex_macros;

  return (
    <div>
      <PageHeader eyebrow="Research" title="Evaluate flashcards" accent="from-amber-400 to-phys-500"
        subtitle="Give each card an overall rating, then rate each quality criterion separately if you like. Your ratings feed the MIT vs student comparison." />

      <div className="mb-5 grid gap-3 lg:grid-cols-[1fr_auto]">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <CategoryToggle value={category} onChange={(v) => { setCategory(v); setSkipped([]); }} />
          <SubjectPills value={subject} onChange={(v) => { setSubject(v); setSkipped([]); }} />
        </div>
        <label className="flex cursor-pointer items-center gap-2 self-center rounded-2xl border border-line bg-white px-3 py-2 text-sm font-semibold">
          <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} className="accent-phys-500" />
          <EyeOff className="size-4" /> Blind mode (hide MIT/student label)
        </label>
      </div>

      {!evaluator && (
        <div className="card-surface mb-5 flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
          <UserRound className="size-5 text-phys-600" />
          <p className="flex-1 text-sm text-ink-soft">Add your name or an alias so your ratings are grouped (optional, stored on this device only).</p>
          <div className="flex gap-2">
            <Input value={nameDraft} onChange={(e) => setNameDraft(e.target.value)} placeholder="e.g. rater-01" className="w-44" />
            <Button onClick={() => nameDraft.trim() && setEvaluator(nameDraft.trim())}>Save</Button>
          </div>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="min-w-0 space-y-4">
          {isLoading && !card ? <Skeleton className="h-80" /> : !card ? (
            <EmptyState icon="🎉" title="Nothing left to rate">You've rated every card that matches these filters. Change the filters or check the Statistics page.</EmptyState>
          ) : (
            <>
              <Card className="overflow-hidden">
                <div className={cn("h-1.5", blind ? "bg-gradient-to-r from-phys-500 to-amber-300" : card.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
                <CardContent className="p-5 sm:p-7">
                  <div className="flex flex-wrap items-center gap-2">
                    {!blind && <CategoryBadge category={card.category} />}
                    <TypeBadge type={card.card_type} /><SubjectBadge subject={card.subject} />
                    <span className="ml-auto text-xs font-semibold text-ink-muted">Card #{card.id}{card.evaluations ? ` · ${card.evaluations.count} ratings` : ""}</span>
                  </div>
                  <p className="mt-5 text-xs font-bold uppercase tracking-wider text-ink-muted">Question</p>
                  <p className="mt-1 font-display text-xl font-medium leading-snug sm:text-2xl"><Inline text={card.question} macros={macros} /></p>
                  <p className="mt-5 text-xs font-bold uppercase tracking-wider text-ink-muted">Answer</p>
                  <div className="mt-1 rounded-2xl bg-canvas px-4 py-2"><NoteText text={card.answer} macros={macros} className="text-[15px] text-ink" /></div>
                  <div className="mt-4">
                    <button onClick={() => setShowExcerpt((s) => !s)} className="text-xs font-bold uppercase tracking-wider text-phys-700 hover:underline">
                      {showExcerpt ? "Hide" : "Show"} source passage
                    </button>
                    {showExcerpt && card.excerpt && (
                      <div className="mt-2 rounded-2xl border border-yellow-200 bg-yellow-50/70 px-4 py-2">
                        <NoteText text={card.excerpt} macros={macros} className="text-sm" />
                      </div>
                    )}
                  </div>
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
                    {blind ? <span className="text-xs text-ink-muted">Source hidden in blind mode</span> : <SourceLine card={card} />}
                    <Button asChild size="sm" variant="ghost"><Link href={`/notes/${card.document_id}?card=${card.id}`} target="_blank"><BookOpenText /> Open in notes</Link></Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Overall rating</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-5 gap-2">
                    {[1, 2, 3, 4, 5].map((lvl) => {
                      const r = RATING_STYLE[lvl];
                      const on = overall === lvl;
                      return (
                        <button key={lvl} onClick={() => setOverall(lvl)}
                          className={cn("focus-ring flex flex-col items-center gap-1 rounded-2xl border-2 px-1 py-3 transition-all", on ? cn(r.bg, "border-transparent text-white shadow-lift -translate-y-0.5") : "border-line bg-white hover:border-ink/20")}>
                          <span className="text-2xl">{r.emoji}</span>
                          <span className="text-center text-[11px] font-bold leading-tight sm:text-xs">{lvl}. {r.label}</span>
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-2 text-xs text-ink-muted">Tip: press 1–5 on your keyboard, Ctrl/⌘+Enter to save.</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Research quality criteria <span className="text-sm font-normal text-ink-muted">(optional, each rated separately)</span></CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {meta?.criteria.map((c) => (
                    <div key={c.key} className="flex flex-col gap-2 rounded-2xl bg-canvas/70 p-3 md:flex-row md:items-center">
                      <div className="min-w-0 flex-1">
                        <p className="flex items-center gap-1.5 text-sm font-semibold">{c.label}
                          <span title={c.description} className="text-ink-muted"><Info className="size-3.5" /></span></p>
                        <p className="text-xs text-ink-muted">{c.description}</p>
                      </div>
                      <div className="flex gap-1">
                        {[1, 2, 3, 4, 5].map((lvl) => {
                          const on = criteria[c.key] === lvl;
                          return (
                            <button key={lvl} title={RATING_STYLE[lvl].label}
                              onClick={() => setCriteria((cr) => { const n = { ...cr }; if (n[c.key] === lvl) delete n[c.key]; else n[c.key] = lvl; return n; })}
                              className={cn("focus-ring h-9 min-w-9 rounded-xl px-2 text-xs font-bold transition-all", on ? cn(RATING_STYLE[lvl].bg, "text-white shadow-soft") : "bg-white text-ink-muted ring-1 ring-line hover:ring-ink/20")}>
                              {lvl}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                  <p className="pt-1 text-xs text-ink-muted">Scale: 1 Excellent · 2 Very Good · 3 Acceptable · 4 Poor · 5 Unacceptable. Click again to clear.</p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="space-y-3 p-5">
                  <Textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional comment: what is wrong or particularly good about this card?" />
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Button variant="ghost" onClick={skip}><SkipForward /> Skip</Button>
                    <div className="flex items-center gap-3">
                      {toast && <span className="text-sm font-semibold text-emerald-600">{toast}</span>}
                      <Button size="lg" variant="primary" disabled={!overall || saving} onClick={submit}><Check /> {saving ? "Saving…" : cardParam ? "Save rating" : "Save & next"}</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </section>

        <aside className="space-y-4">
          <Card>
            <CardContent className="grid grid-cols-2 gap-3 p-5">
              <div className="rounded-2xl bg-phys-50 p-3 text-center">
                <p className="font-display text-3xl font-semibold text-phys-700">{next?.rated_by_you ?? mine?.total ?? 0}</p>
                <p className="text-[11px] font-bold uppercase text-ink-muted">Rated by you</p>
              </div>
              <div className="rounded-2xl bg-canvas p-3 text-center">
                <p className="font-display text-3xl font-semibold">{next?.remaining ?? "–"}</p>
                <p className="text-[11px] font-bold uppercase text-ink-muted">Left to rate</p>
              </div>
              <div className="col-span-2 flex items-center gap-2 text-sm">
                <UserRound className="size-4 text-ink-muted" />
                <span className="font-semibold">{who}</span>
                <button className="ml-auto text-xs font-semibold text-ink-muted underline" onClick={() => { setNameDraft(evaluator); setEvaluator(""); }}>change</button>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Your recent ratings</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {!mine?.items.length && <p className="text-sm text-ink-muted">No ratings yet.</p>}
              {mine?.items.map((e) => (
                <div key={e.id} className="flex items-start gap-2 rounded-2xl border border-line p-2.5">
                  <span className={cn("mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg text-xs font-bold text-white", RATING_STYLE[e.overall].bg)}>{e.overall}</span>
                  <Link href={`/evaluate?card=${e.flashcard_id}`} className="min-w-0 flex-1">
                    <p className="line-clamp-2 text-xs font-semibold"><Inline text={e.question} /></p>
                    <p className="text-[11px] text-ink-muted">{e.category === "mit" ? "MIT" : "Student"} · {timeAgo(e.created_at)}</p>
                  </Link>
                  <button aria-label="Delete rating" onClick={async () => { await api.del(`/api/evaluations/${e.id}`); mutateMine(); mutateNext(); }} className="text-ink-muted hover:text-rose-600">
                    <Trash2 className="size-4" />
                  </button>
                </div>
              ))}
              <Button asChild variant="soft" size="sm" className="w-full"><Link href="/statistics">See statistics</Link></Button>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}

export default function EvaluatePage() {
  return <React.Suspense fallback={<Skeleton className="h-96" />}><EvaluateInner /></React.Suspense>;
}
