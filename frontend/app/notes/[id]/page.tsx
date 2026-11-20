"use client";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import * as React from "react";
import {
  ArrowLeft, ChevronLeft, ChevronRight, Download, ExternalLink, Eye, EyeOff, FileText, Layers, ListTree, Scale, Sparkles, User,
} from "lucide-react";
import { CategoryBadge, FormatBadge, SubjectBadge, TypeBadge } from "@/components/badges";
import { Inline, NoteText } from "@/components/rich-text";
import { Button } from "@/components/ui/button";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, useApi, useMeta, type DocDetail, type Flashcard, type Section } from "@/lib/api";
import { CATEGORY_STYLE, SUBJECT_STYLE, cn, compact } from "@/lib/utils";

interface Content { sections: (Section & { index: number; text: string })[]; katex_macros: Record<string, string> }

function Viewer() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const cardParam = sp.get("card");
  const qParam = sp.get("q");
  const secParam = sp.get("section");
  const { data: doc, error, mutate: mutateDoc } = useApi<DocDetail>(`/api/documents/${id}`);
  const { data: content } = useApi<Content>(`/api/documents/${id}/content`);
  const { data: cardsRes, mutate: mutateCards } = useApi<{ total: number; items: Flashcard[] }>(`/api/flashcards?document_id=${id}&limit=200`);
  const { data: meta } = useMeta();
  const cards = cardsRes?.items ?? [];

  const [sectionIdx, setSectionIdx] = React.useState(0);
  const [highlight, setHighlight] = React.useState<[number, number] | null>(null);
  const [activeCard, setActiveCard] = React.useState<number | null>(null);
  const [hideAnswers, setHideAnswers] = React.useState(true);
  const [revealed, setRevealed] = React.useState<Record<number, boolean>>({});
  const [tab, setTab] = React.useState("reader");
  const [tocOpen, setTocOpen] = React.useState(false);
  const [generating, setGenerating] = React.useState(false);
  const markRef = React.useRef<HTMLElement>(null);
  const readerTop = React.useRef<HTMLDivElement>(null);

  const sections = content?.sections ?? [];
  const macros = content?.katex_macros ?? doc?.katex_macros;

  const focusCard = React.useCallback((c: Flashcard) => {
    if (c.section_index == null || c.char_start == null || c.char_end == null) return;
    setTab("reader");
    setSectionIdx(c.section_index);
    setHighlight([c.char_start, c.char_end]);
    setActiveCard(c.id);
  }, []);

  // deep link: ?card= or ?q=
  React.useEffect(() => {
    if (!sections.length) return;
    if (cardParam && cards.length) {
      const c = cards.find((x) => String(x.id) === cardParam);
      if (c) { focusCard(c); setRevealed((r) => ({ ...r, [c.id]: true })); return; }
    }
    if (secParam && !Number.isNaN(Number(secParam))) {
      setSectionIdx(Math.min(Number(secParam), sections.length - 1));
      if (!qParam) return;
    }
    if (qParam) {
      const needle = qParam.toLowerCase();
      for (const s of sections) {
        const i = s.text.toLowerCase().indexOf(needle);
        if (i >= 0) { setSectionIdx(s.index); setHighlight([s.start + i, s.start + i + needle.length]); return; }
      }
    }
  }, [sections.length, cards.length, cardParam, qParam, secParam, focusCard]); // eslint-disable-line react-hooks/exhaustive-deps

  React.useEffect(() => {
    const t = setTimeout(() => {
      if (highlight && markRef.current) markRef.current.scrollIntoView({ block: "center", behavior: "smooth" });
    }, 80);
    return () => clearTimeout(t);
  }, [highlight, sectionIdx]);

  const goSection = (i: number) => {
    setSectionIdx(i);
    setHighlight(null);
    setActiveCard(null);
    setTocOpen(false);
    readerTop.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const cardsBySection = React.useMemo(() => {
    const m: Record<number, Flashcard[]> = {};
    cards.forEach((c) => { if (c.section_index != null) (m[c.section_index] ||= []).push(c); });
    return m;
  }, [cards]);
  const topicSections = React.useMemo(() => {
    const m: Record<number, string[]> = {};
    doc?.topic_sections.forEach((t) => t.sections.forEach((s) => (m[s] ||= []).push(t.topic.name)));
    return m;
  }, [doc]);

  if (error) return <EmptyState icon="🤷" title="Document not found" />;
  if (!doc) return <Skeleton className="h-96" />;

  const cat = CATEGORY_STYLE[doc.category];
  const section = sections[sectionIdx];
  const relHighlight: [number, number] | null = highlight && section ? [highlight[0] - section.start, highlight[1] - section.start] : null;
  const sectionCards = cardsBySection[sectionIdx] ?? [];

  const regenerate = async (useAi: boolean) => {
    setGenerating(true);
    try {
      await api.post(`/api/documents/${id}/flashcards/generate`, { use_ai: useAi });
      await Promise.all([mutateCards(), mutateDoc()]);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const Toc = (
    <div className="scrollbar-thin max-h-[70vh] space-y-0.5 overflow-y-auto pr-1">
      {sections.map((s) => (
        <button
          key={s.index}
          onClick={() => goSection(s.index)}
          className={cn(
            "focus-ring flex w-full items-start gap-2 rounded-xl px-2.5 py-1.5 text-left text-[13px] transition-colors",
            s.index === sectionIdx ? cn("font-semibold text-ink", cat.soft) : "text-ink-soft hover:bg-black/[.03]",
          )}
          style={{ paddingLeft: `${0.6 + Math.min(s.level - 1, 2) * 0.75}rem` }}
        >
          <span className="min-w-0 flex-1 truncate"><Inline text={s.title} macros={macros} /></span>
          {cardsBySection[s.index] && (
            <span className={cn("shrink-0 rounded-full px-1.5 text-[11px] font-bold", cat.chip)}>{cardsBySection[s.index].length}</span>
          )}
        </button>
      ))}
    </div>
  );

  return (
    <div className="space-y-5">
      <Link href="/notes" className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-muted hover:text-ink"><ArrowLeft className="size-4" /> All notes</Link>

      {/* header */}
      <section className={cn("relative overflow-hidden rounded-4xl border bg-white p-5 shadow-soft sm:p-7", cat.border)}>
        <span className={cn("absolute inset-x-0 top-0 h-1.5", doc.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
        <div className="flex flex-wrap gap-2">
          <CategoryBadge category={doc.category} /><SubjectBadge subject={doc.subject} /><FormatBadge format={doc.format} />
          {doc.review_status === "approved" && <span className="chip bg-emerald-100 text-emerald-700">Reviewed</span>}
        </div>
        <h1 className="mt-3 font-display text-2xl font-semibold tracking-tight sm:text-3xl">{doc.title}</h1>
        {doc.course && (
          <Link href={`/courses/${doc.course.id}`} className="mt-1 inline-block text-sm font-semibold text-ink-muted hover:text-ink">
            {doc.course.code} · {doc.course.title}{doc.course.university && ` · ${doc.course.university}`}
          </Link>
        )}
        <div className="mt-4 grid gap-2 text-sm text-ink-soft md:grid-cols-2 [&>*]:min-w-0">
          <p className="flex items-start gap-2"><User className="mt-0.5 size-4 shrink-0" /><span><b>Author:</b> {doc.author || "Unknown"}</span></p>
          <p className="flex items-start gap-2"><Scale className="mt-0.5 size-4 shrink-0" /><span><b>Licence:</b> {doc.license || "—"}</span></p>
          <p className="flex items-start gap-2"><FileText className="mt-0.5 size-4 shrink-0" /><span><b>Source:</b> {doc.source?.name} · {compact(doc.word_count)} words{doc.page_count ? ` · ${doc.page_count} pages` : ""}</span></p>
          <p className="flex items-start gap-2"><ExternalLink className="mt-0.5 size-4 shrink-0" /><a href={doc.url} target="_blank" rel="noreferrer" className="min-w-0 truncate font-medium text-student-600 hover:underline">{doc.url}</a></p>
        </div>
        {doc.topic_sections.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-xs font-bold uppercase tracking-wider text-ink-muted">Topics</span>
            {doc.topic_sections.map((t) => (
              <button key={t.topic.id} onClick={() => t.sections[0] != null && goSection(t.sections[0])} title="Jump to the section that covers this topic most"
                className={cn("chip py-1 transition-transform hover:scale-105", SUBJECT_STYLE[doc.subject]?.chip)}>
                {t.topic.name}
              </button>
            ))}
          </div>
        )}
        <div className="mt-5 flex flex-wrap gap-2">
          <Button asChild variant={doc.category === "mit" ? "mit" : "student"}><Link href={`/flashcards?document=${doc.id}&category=${doc.category}`}><Layers /> Study {cards.length} cards</Link></Button>
          <Button asChild variant="outline"><a href={doc.url} target="_blank" rel="noreferrer"><ExternalLink /> Original</a></Button>
          {doc.has_file && <Button asChild variant="outline"><a href={`/api/documents/${doc.id}/file`} target="_blank" rel="noreferrer"><Download /> Stored copy</a></Button>}
        </div>
      </section>

      <Tabs value={tab} onValueChange={setTab}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TabsList>
            <TabsTrigger value="reader"><ListTree /> Reader</TabsTrigger>
            <TabsTrigger value="cards"><Layers /> Flashcards ({cards.length})</TabsTrigger>
            {doc.has_file && <TabsTrigger value="original"><FileText /> Original file</TabsTrigger>}
          </TabsList>
          <Button size="sm" variant="ghost" onClick={() => setHideAnswers((h) => !h)}>
            {hideAnswers ? <Eye /> : <EyeOff />} {hideAnswers ? "Quiz mode: answers hidden" : "Answers visible"}
          </Button>
        </div>

        <TabsContent value="reader">
          <div className="grid gap-4 lg:grid-cols-[230px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_320px]">
            <aside className="hidden lg:block">
              <div className="card-surface sticky top-24 p-3">
                <p className="mb-2 px-2 text-xs font-bold uppercase tracking-wider text-ink-muted">Contents · {sections.length}</p>
                {Toc}
              </div>
            </aside>

            <article ref={readerTop} className="card-surface min-w-0 scroll-mt-24 p-5 sm:p-8">
              <div className="mb-4 flex items-center gap-2 lg:hidden">
                <Button size="sm" variant="soft" onClick={() => setTocOpen((o) => !o)}><ListTree /> Contents</Button>
              </div>
              {tocOpen && <div className="mb-4 rounded-2xl border border-line p-2 lg:hidden">{Toc}</div>}
              {!section ? (
                <Skeleton className="h-64" />
              ) : (
                <>
                  <div className="mb-4 flex flex-wrap items-center gap-2 text-xs font-semibold text-ink-muted">
                    <span>Section {sectionIdx + 1} of {sections.length}</span>
                    {section.page && <span>· page {section.page}</span>}
                    {(topicSections[sectionIdx] ?? []).map((t) => <span key={t} className={cn("chip", SUBJECT_STYLE[doc.subject]?.chip)}>{t}</span>)}
                  </div>
                  <h2 className="font-display text-2xl font-semibold tracking-tight"><Inline text={section.title} macros={macros} /></h2>
                  <NoteText text={section.text} macros={macros} highlight={relHighlight} markRef={markRef} className="mt-3" />
                  <div className="mt-8 flex items-center justify-between border-t border-line pt-4">
                    <Button variant="outline" size="sm" disabled={sectionIdx === 0} onClick={() => goSection(sectionIdx - 1)}><ChevronLeft /> Previous</Button>
                    <Button variant="outline" size="sm" disabled={sectionIdx >= sections.length - 1} onClick={() => goSection(sectionIdx + 1)}>Next <ChevronRight /></Button>
                  </div>
                </>
              )}
            </article>

            {/* study panel */}
            <aside className="lg:col-span-2 xl:col-span-1">
              <div className="card-surface sticky top-24 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <p className="font-display text-base font-semibold">Cards in this section</p>
                  <span className={cn("chip", cat.chip)}>{sectionCards.length}</span>
                </div>
                {sectionCards.length === 0 ? (
                  <p className="rounded-2xl bg-canvas p-4 text-sm text-ink-muted">No flashcards point to this section. Use the contents list — numbers show where cards come from.</p>
                ) : (
                  <div className="scrollbar-thin max-h-[65vh] space-y-2.5 overflow-y-auto pr-1">
                    {sectionCards.map((c) => (
                      <MiniCard key={c.id} card={c} macros={macros} active={activeCard === c.id} hidden={hideAnswers && !revealed[c.id]}
                        onReveal={() => setRevealed((r) => ({ ...r, [c.id]: true }))} onLocate={() => focusCard(c)} />
                    ))}
                  </div>
                )}
              </div>
            </aside>
          </div>
        </TabsContent>

        <TabsContent value="cards">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Button size="sm" variant="outline" disabled={generating} onClick={() => regenerate(false)}><Sparkles /> {generating ? "Generating…" : "Regenerate (rules)"}</Button>
            {meta?.ai.enabled && <Button size="sm" variant="primary" disabled={generating} onClick={() => regenerate(true)}><Sparkles /> Generate with AI</Button>}
            <span className="text-xs text-ink-muted">Cards that already have ratings are kept when you regenerate.</span>
          </div>
          {cards.length === 0 ? (
            <EmptyState icon="🃏" title="No flashcards yet">Generate cards from this document with the button above.</EmptyState>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {cards.map((c) => (
                <MiniCard key={c.id} card={c} macros={macros} big hidden={hideAnswers && !revealed[c.id]}
                  onReveal={() => setRevealed((r) => ({ ...r, [c.id]: true }))} onLocate={() => focusCard(c)} />
              ))}
            </div>
          )}
        </TabsContent>

        {doc.has_file && (
          <TabsContent value="original">
            <OriginalFile doc={doc} page={section?.page ?? null} />
          </TabsContent>
        )}
      </Tabs>

      {doc.similar.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-xl font-semibold">Similar documents in other sources</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {doc.similar.map((s) => (
              <Link key={s.id} href={`/notes/${s.id}`} className="card-surface flex min-w-0 items-center gap-3 p-4 transition-all hover:-translate-y-0.5">
                <span className={cn("grid size-10 shrink-0 place-items-center rounded-2xl text-lg", SUBJECT_STYLE[s.subject]?.soft)}>{SUBJECT_STYLE[s.subject]?.emoji}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold">{s.title}</span>
                  <span className="block truncate text-xs text-ink-muted">{s.source?.name}</span>
                </span>
                <span className="ml-auto flex flex-col items-end gap-1">
                  <CategoryBadge category={s.category} short />
                  <span className="text-[11px] font-bold text-ink-muted">{Math.round(s.similarity * 100)}% match</span>
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function MiniCard({ card, macros, active, hidden, onReveal, onLocate, big }: {
  card: Flashcard; macros?: Record<string, string>; active?: boolean; hidden: boolean; onReveal: () => void; onLocate: () => void; big?: boolean;
}) {
  return (
    <div className={cn("rounded-2xl border bg-white p-3.5 transition-all", active ? "border-yellow-300 ring-4 ring-yellow-100" : "border-line", big && "p-4")}>
      <div className="mb-1.5 flex items-center gap-1.5">
        <TypeBadge type={card.card_type} />
        {card.page && <span className="text-[11px] font-semibold text-ink-muted">p. {card.page}</span>}
        <span className="ml-auto text-[11px] font-semibold text-ink-muted">#{card.id}</span>
      </div>
      <p className={cn("font-semibold leading-snug text-ink", big ? "text-[15px]" : "text-sm")}><Inline text={card.question} macros={macros} /></p>
      {hidden ? (
        <button onClick={onReveal} className="focus-ring mt-2 w-full rounded-xl border border-dashed border-line py-2 text-xs font-semibold text-ink-muted hover:bg-canvas">Show answer</button>
      ) : (
        <div className="mt-2 rounded-xl bg-canvas px-3 py-1.5 text-sm"><NoteText text={card.answer} macros={macros} className="text-sm leading-6" /></div>
      )}
      <div className="mt-2 flex flex-wrap gap-1.5">
        <button onClick={onLocate} className="focus-ring inline-flex items-center gap-1 rounded-lg bg-yellow-100 px-2 py-1 text-[11px] font-bold text-yellow-900 hover:bg-yellow-200">
          <Eye className="size-3.5" /> Find answer in the notes
        </button>
        <Link href={`/evaluate?card=${card.id}`} className="inline-flex items-center gap-1 rounded-lg bg-black/[.04] px-2 py-1 text-[11px] font-bold text-ink-soft hover:bg-black/[.07]">Rate</Link>
      </div>
    </div>
  );
}

function OriginalFile({ doc, page }: { doc: DocDetail; page: number | null }) {
  const src = `/api/documents/${doc.id}/file`;
  const [raw, setRaw] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (doc.format === "md" || doc.format === "tex") fetch(src).then((r) => r.text()).then(setRaw).catch(() => setRaw("Could not load file"));
  }, [doc.format, src]);
  if (doc.format === "pdf") return <iframe title="PDF preview" src={`${src}#page=${page ?? 1}`} className="h-[80vh] w-full rounded-3xl border border-line bg-white" />;
  if (doc.format === "html") return <iframe title="HTML preview" src={src} sandbox="" className="h-[80vh] w-full rounded-3xl border border-line bg-white" />;
  return <pre className="scrollbar-thin max-h-[80vh] overflow-auto rounded-3xl border border-line bg-white p-5 text-xs leading-5">{raw ?? "Loading…"}</pre>;
}

export default function NotePage() {
  return <React.Suspense fallback={<Skeleton className="h-96" />}><Viewer /></React.Suspense>;
}
