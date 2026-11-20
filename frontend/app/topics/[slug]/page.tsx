"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, GraduationCap, Layers, Users } from "lucide-react";
import { SubjectBadge, TypeBadge } from "@/components/badges";
import { Inline } from "@/components/rich-text";
import { Button } from "@/components/ui/button";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { useApi } from "@/lib/api";
import { CATEGORY_STYLE, SUBJECT_STYLE, cn } from "@/lib/utils";

export default function TopicDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: t, error } = useApi<any>(`/api/topics/${slug}`);
  if (error) return <EmptyState icon="🤷" title="Topic not found" />;
  if (!t) return <Skeleton className="h-96" />;
  const s = SUBJECT_STYLE[t.subject];
  const byCat = { mit: t.documents.filter((d: any) => d.category === "mit"), student: t.documents.filter((d: any) => d.category === "student") };

  return (
    <div className="space-y-6">
      <Link href="/topics" className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-muted hover:text-ink"><ArrowLeft className="size-4" /> All topics</Link>
      <section className={cn("relative overflow-hidden rounded-4xl p-6 shadow-soft sm:p-8", s.soft)}>
        <div className="absolute -right-6 -top-6 text-[120px] opacity-20">{s.emoji}</div>
        <SubjectBadge subject={t.subject} />
        <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">{t.name}</h1>
        <p className="mt-1 max-w-2xl text-ink-soft">{t.description}</p>
        <div className="mt-4 flex flex-wrap gap-1.5">{t.keywords.map((k: string) => <span key={k} className="chip bg-white/80 text-ink-soft">{k}</span>)}</div>
        <div className="mt-6 grid max-w-xl grid-cols-3 gap-3">
          {[["MIT documents", t.coverage.mit, "text-mit-600"], ["Student documents", t.coverage.student, "text-student-600"], ["Sources", t.coverage.sources, "text-ink"]].map(([l, v, c]) => (
            <div key={l as string} className="rounded-3xl bg-white/80 p-3 text-center">
              <p className={cn("font-display text-2xl font-semibold", c as string)}>{v as number}</p>
              <p className="text-[11px] font-semibold uppercase text-ink-muted">{l}</p>
            </div>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {t.flashcard_counts.mit > 0 && <Button asChild variant="mit"><Link href={`/flashcards?topic=${t.slug}&category=mit`}><Layers /> {t.flashcard_counts.mit} MIT cards</Link></Button>}
          {t.flashcard_counts.student > 0 && <Button asChild variant="student"><Link href={`/flashcards?topic=${t.slug}&category=student`}><Layers /> {t.flashcard_counts.student} student cards</Link></Button>}
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        {(["mit", "student"] as const).map((cat) => {
          const st = CATEGORY_STYLE[cat];
          const Icon = cat === "mit" ? GraduationCap : Users;
          return (
            <section key={cat} className={cn("min-w-0 rounded-4xl border bg-white/70 p-4 sm:p-5", st.border)}>
              <h2 className="mb-3 flex items-center gap-2 font-display text-xl font-semibold">
                <span className={cn("grid size-8 place-items-center rounded-xl", st.solid)}><Icon className="size-4" /></span>
                {st.label} <span className="text-ink-muted">({byCat[cat].length})</span>
              </h2>
              {byCat[cat].length === 0 ? (
                <p className="rounded-2xl bg-canvas p-4 text-sm text-ink-muted">No {cat === "mit" ? "MIT" : "student"} documents cover this topic yet.</p>
              ) : (
                <div className="space-y-2.5">
                  {byCat[cat].map((d: any) => (
                    <div key={d.id} className="rounded-2xl border border-line bg-white p-3.5">
                      <div className="flex items-start justify-between gap-2">
                        <Link href={`/notes/${d.id}`} className="font-semibold leading-snug hover:underline">{d.title}</Link>
                        <span className="shrink-0 text-xs font-bold text-ink-muted">{d.hits} mentions</span>
                      </div>
                      <p className="text-xs text-ink-muted">{d.source?.name}{d.course ? ` · ${d.course.code}` : ""}</p>
                      {d.matched_sections.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {d.matched_sections.map((sec: any) => (
                            <Link key={sec.index} href={`/notes/${d.id}?section=${sec.index}`} className={cn("chip max-w-full overflow-hidden whitespace-nowrap py-1 hover:brightness-95", st.chip)}>
                              § <Inline text={sec.title.replace(/^Page \d+ · /, "") || `Section ${sec.index + 1}`} />{sec.page ? ` · p.${sec.page}` : ""}
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {t.flashcards[cat].length > 0 && (
                <div className="mt-4">
                  <p className="mb-2 text-xs font-bold uppercase tracking-wider text-ink-muted">Sample flashcards</p>
                  <div className="space-y-2">
                    {t.flashcards[cat].slice(0, 4).map((c: any) => (
                      <Link key={c.id} href={`/notes/${c.document_id}?card=${c.id}`} className={cn("block rounded-2xl p-3 text-sm hover:brightness-[.98]", st.soft)}>
                        <TypeBadge type={c.card_type} className="mb-1" />
                        <p className="font-medium"><Inline text={c.question} macros={c.document.katex_macros} /></p>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </section>
          );
        })}
      </div>

      {t.related.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-xl font-semibold">Related topics</h2>
          <div className="flex flex-wrap gap-2">
            {t.related.map((r: any) => (
              <Link key={r.id} href={`/topics/${r.slug}`} className={cn("chip py-1.5 text-[13px] hover:scale-105", SUBJECT_STYLE[r.subject]?.chip)}>
                {r.name} <span className="opacity-60">{r.shared_documents} shared docs</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
