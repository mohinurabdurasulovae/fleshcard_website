"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import { Check, ChevronLeft, ChevronRight, Layers, RotateCcw, Shuffle, Sparkles, Star, X } from "lucide-react";
import { PageHeader } from "@/components/app-shell";
import { CategoryToggle, SubjectPills } from "@/components/filters";
import { FlashcardView } from "@/components/flashcard-view";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input, Select } from "@/components/ui/input";
import { EmptyState, Progress, Skeleton } from "@/components/ui/misc";
import { api, useApi, useMeta, type DocBrief, type Flashcard } from "@/lib/api";
import { CATEGORY_STYLE, TYPE_STYLE, cn, qs } from "@/lib/utils";

function FlashcardsInner() {
  const sp = useSearchParams();
  const [category, setCategory] = React.useState<string>(sp.get("category") || "mit");
  const [subject, setSubject] = React.useState("");
  const [cardType, setCardType] = React.useState("");
  const [documentId, setDocumentId] = React.useState(sp.get("document") || "");
  const [topic, setTopic] = React.useState(sp.get("topic") || "");
  const [courseId] = React.useState(sp.get("course") || "");
  const [shuffle, setShuffle] = React.useState(false);
  const [seed, setSeed] = React.useState(0);
  const [idx, setIdx] = React.useState(0);
  const [flipped, setFlipped] = React.useState(false);
  const [known, setKnown] = React.useState<Record<number, boolean>>({});
  const [genOpen, setGenOpen] = React.useState(false);

  const { data: decks } = useApi<any[]>(`/api/flashcards/decks${qs({ category, subject })}`);
  const { data, isLoading, mutate } = useApi<{ total: number; items: Flashcard[] }>(
    `/api/flashcards${qs({ category, subject, card_type: cardType, document_id: documentId, topic, course_id: courseId, order: shuffle ? "random" : "document", limit: 200, s: shuffle ? seed : undefined })}`,
  );
  const cards = data?.items ?? [];
  const card = cards[idx];
  React.useEffect(() => { setIdx(0); setFlipped(false); }, [category, subject, cardType, documentId, topic, shuffle, seed]);

  const go = React.useCallback((d: number) => {
    setFlipped(false);
    setIdx((i) => Math.max(0, Math.min(cards.length - 1, i + d)));
  }, [cards.length]);
  const mark = (v: boolean) => { if (card) setKnown((k) => ({ ...k, [card.id]: v })); go(1); };

  React.useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName.match(/INPUT|TEXTAREA|SELECT/)) return;
      if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === " ") { e.preventDefault(); setFlipped((f) => !f); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [go]);

  const knownCount = cards.filter((c) => known[c.id] === true).length;
  const learningCount = cards.filter((c) => known[c.id] === false).length;
  const cat = CATEGORY_STYLE[category as "mit" | "student"];
  const activeDeck = decks?.find((d) => String(d.document_id) === documentId);

  return (
    <div>
      <PageHeader eyebrow="Study" title="Flashcards" accent="from-pink-500 to-mit-500"
        subtitle="MIT and student flashcards are kept in separate decks. Every card shows where it came from. Open the notes to check the answer in context."
        actions={<Button variant="primary" onClick={() => setGenOpen(true)}><Sparkles /> Generate from a document</Button>} />

      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <CategoryToggle value={category} onChange={(v) => { setCategory(v); setDocumentId(""); }} allowAll={false} />
        <SubjectPills value={subject} onChange={(v) => { setSubject(v); setDocumentId(""); }} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        {/* decks */}
        <aside className="order-2 lg:order-1">
          <div className={cn("card-surface overflow-hidden p-0")}>
            <div className={cn("px-4 py-3 text-white", category === "mit" ? "bg-mit-500" : "bg-student-500")}>
              <p className="text-xs font-bold uppercase tracking-wider text-white/80">{cat.label}</p>
              <p className="font-display text-lg font-semibold">Decks</p>
            </div>
            <div className="scrollbar-thin max-h-[60vh] space-y-0.5 overflow-y-auto p-2">
              <DeckButton active={!documentId && !topic && !courseId} onClick={() => { setDocumentId(""); setTopic(""); }} title="All cards" sub={subject || "Every subject"} count={undefined} />
              {decks?.map((d) => (
                <DeckButton key={d.document_id} active={String(d.document_id) === documentId} onClick={() => { setDocumentId(String(d.document_id)); setTopic(""); }} title={d.title} sub={d.course || d.source} count={d.count} />
              ))}
              {decks && decks.length === 0 && <p className="p-3 text-sm text-ink-muted">No {category === "mit" ? "MIT" : "student"} decks yet.</p>}
            </div>
          </div>
        </aside>

        {/* study area */}
        <section className="order-1 min-w-0 lg:order-2">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Select value={cardType} onChange={(e) => setCardType(e.target.value)} aria-label="Card type">
              <option value="">All card types</option>
              {Object.entries(TYPE_STYLE).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </Select>
            <Button variant={shuffle ? "default" : "outline"} size="sm" onClick={() => { setShuffle(true); setSeed((s) => s + 1); }}><Shuffle /> Shuffle</Button>
            {shuffle && <Button variant="ghost" size="sm" onClick={() => setShuffle(false)}><RotateCcw /> In order</Button>}
            {topic && <span className="chip bg-bio-100 text-bio-700">Topic: {topic.replace(/^[a-z]+-[a-z]+-|^[a-z]+-/, "")} <button onClick={() => setTopic("")}><X className="size-3" /></button></span>}
            {activeDeck && <span className="truncate text-sm font-semibold text-ink-muted">Deck: {activeDeck.title}</span>}
          </div>

          {isLoading && !data ? <Skeleton className="h-[380px]" /> : !card ? (
            <EmptyState icon="🃏" title="No flashcards here yet">
              {category === "mit" ? "MIT notes haven't been collected yet. Run the MIT OCW collector from the Data Collection page." : "Try another subject or generate cards from a document."}
            </EmptyState>
          ) : (
            <>
              <div className="mb-3 flex items-center gap-3">
                <Progress value={((idx + 1) / cards.length) * 100} barClassName={category === "mit" ? "bg-mit-500 bg-none" : "bg-student-500 bg-none"} />
                <span className="shrink-0 text-sm font-bold text-ink-muted">{idx + 1} / {cards.length}{data && data.total > cards.length ? ` (of ${data.total})` : ""}</span>
              </div>
              <FlashcardView key={card.id} card={card} flipped={flipped} onFlip={() => setFlipped((f) => !f)}
                actions={<Button asChild size="sm" variant="ghost"><Link href={`/evaluate?card=${card.id}`} onClick={(e) => e.stopPropagation()}><Star /> Rate</Link></Button>} />
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <Button variant="outline" onClick={() => go(-1)} disabled={idx === 0}><ChevronLeft /> Back</Button>
                <div className="flex gap-2">
                  <Button variant="danger" onClick={() => mark(false)}><X /> Still learning</Button>
                  <Button className="bg-emerald-500 hover:bg-emerald-600" onClick={() => mark(true)}><Check /> I knew it</Button>
                </div>
                <Button variant="outline" onClick={() => go(1)} disabled={idx >= cards.length - 1}>Next <ChevronRight /></Button>
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-4 text-sm font-semibold text-ink-muted">
                <span className="text-emerald-600">✓ {knownCount} known</span>
                <span className="text-rose-600">↻ {learningCount} learning</span>
                <span className="hidden sm:inline">Keys: ← → to move, Space to flip</span>
              </div>
            </>
          )}
        </section>
      </div>

      <GenerateDialog open={genOpen} onOpenChange={setGenOpen} onDone={(docId, docCat) => { setCategory(docCat); setDocumentId(String(docId)); mutate(); }} />
    </div>
  );
}

function DeckButton({ active, onClick, title, sub, count }: { active: boolean; onClick: () => void; title: string; sub: string; count?: number }) {
  return (
    <button onClick={onClick} className={cn("focus-ring flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-left transition-colors", active ? "bg-canvas shadow-inner" : "hover:bg-canvas/70")}>
      <span className={cn("grid size-8 shrink-0 place-items-center rounded-xl", active ? "bg-ink text-white" : "bg-black/[.05] text-ink-soft")}><Layers className="size-4" /></span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold">{title}</span>
        <span className="block truncate text-xs text-ink-muted">{sub}</span>
      </span>
      {count != null && <span className="text-xs font-bold text-ink-muted">{count}</span>}
    </button>
  );
}

function GenerateDialog({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (v: boolean) => void; onDone: (id: number, cat: string) => void }) {
  const [q, setQ] = React.useState("");
  const [busy, setBusy] = React.useState<number | null>(null);
  const [useAi, setUseAi] = React.useState(false);
  const [msg, setMsg] = React.useState("");
  const { data: meta } = useMeta();
  const { data } = useApi<{ items: DocBrief[] }>(open ? `/api/documents${qs({ q, page_size: 12, sort: "title" })}` : null);
  const run = async (d: DocBrief) => {
    setBusy(d.id); setMsg("");
    try {
      const r = await api.post(`/api/documents/${d.id}/flashcards/generate`, { use_ai: useAi });
      setMsg(`Created ${r.created} new cards (${r.total} total) for “${d.title}”.`);
      onDone(d.id, d.category);
    } catch (e: any) { setMsg(e.message); } finally { setBusy(null); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogTitle>Generate flashcards</DialogTitle>
        <DialogDescription>Pick a lecture document. The built-in generator needs no API key; AI generation is used only if configured on the server.</DialogDescription>
        <Input className="mt-4" placeholder="Search documents…" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className={cn("mt-3 flex items-center gap-2 text-sm font-semibold", !meta?.ai.enabled && "opacity-50")}>
          <input type="checkbox" disabled={!meta?.ai.enabled} checked={useAi} onChange={(e) => setUseAi(e.target.checked)} className="accent-cs-500" />
          Use AI ({meta?.ai.enabled ? `${meta.ai.provider} · ${meta.ai.model}` : "not configured"})
        </label>
        {msg && <p className="mt-3 rounded-2xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{msg}</p>}
        <div className="mt-3 max-h-80 space-y-1.5 overflow-y-auto">
          {data?.items.map((d) => (
            <div key={d.id} className="flex items-center gap-3 rounded-2xl border border-line p-2.5">
              <span className={cn("size-2.5 shrink-0 rounded-full", d.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">{d.title}</span>
                <span className="block truncate text-xs text-ink-muted">{d.source?.name} · {d.flashcard_count ?? 0} cards</span>
              </span>
              <Button size="sm" variant="soft" disabled={busy !== null} onClick={() => run(d)}>{busy === d.id ? "Working…" : "Generate"}</Button>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function FlashcardsPage() {
  return <React.Suspense fallback={<Skeleton className="h-96" />}><FlashcardsInner /></React.Suspense>;
}
