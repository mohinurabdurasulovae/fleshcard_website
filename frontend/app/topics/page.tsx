"use client";
import Link from "next/link";
import * as React from "react";
import { ArrowRight, GitMerge, Layers, Network } from "lucide-react";
import { PageHeader } from "@/components/app-shell";
import { SubjectPills } from "@/components/filters";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/lib/api";
import { SUBJECT_STYLE, cn, qs } from "@/lib/utils";

export default function TopicsPage() {
  const [subject, setSubject] = React.useState("");
  const [onlyShared, setOnlyShared] = React.useState(false);
  const { data: topics, isLoading } = useApi<any[]>(`/api/topics${qs({ subject })}`);
  const { data: shared } = useApi<any[]>(`/api/topics/shared-headings${qs({ subject })}`);
  const list = (topics ?? []).filter((t) => (onlyShared ? t.cross_source || t.source_count > 1 : true));
  const max = Math.max(1, ...list.map((t) => t.document_count));

  return (
    <div>
      <PageHeader eyebrow="Topic explorer" title="Topics across sources" subtitle="Documents are organised into academic topics automatically. See where MIT and student notes cover the same ideas." accent="from-bio-500 to-teal-400" />
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <SubjectPills value={subject} onChange={setSubject} />
        <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-ink-soft">
          <input type="checkbox" className="accent-bio-500" checked={onlyShared} onChange={(e) => setOnlyShared(e.target.checked)} /> Only topics in 2+ sources
        </label>
      </div>
      <Tabs defaultValue="taxonomy">
        <TabsList>
          <TabsTrigger value="taxonomy"><Network /> Topic map</TabsTrigger>
          <TabsTrigger value="shared"><GitMerge /> Matching sections ({shared?.length ?? 0})</TabsTrigger>
        </TabsList>

        <TabsContent value="taxonomy">
          {isLoading && !topics ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-44" />)}</div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {list.map((t, i) => {
                const s = SUBJECT_STYLE[t.subject];
                const tot = t.document_count || 1;
                return (
                  <Link key={t.id} href={`/topics/${t.slug}`} style={{ animationDelay: `${Math.min(i, 12) * 30}ms` }}
                    className={cn("card-surface focus-ring group flex animate-fade-up flex-col p-5 transition-all hover:-translate-y-0.5 hover:shadow-lift", t.document_count === 0 && "opacity-60")}>
                    <div className="flex items-start justify-between gap-2">
                      <span className={cn("grid size-10 place-items-center rounded-2xl text-lg", s.soft)}>{s.emoji}</span>
                      {t.cross_source && <span className="chip bg-gradient-to-r from-mit-100 to-student-100 text-ink">MIT + Student</span>}
                    </div>
                    <h3 className="mt-3 font-display text-lg font-semibold">{t.name}</h3>
                    <p className="line-clamp-2 text-sm text-ink-muted">{t.description}</p>
                    <div className="mt-4">
                      <div className="flex h-2.5 overflow-hidden rounded-full bg-black/[.05]" style={{ width: `${Math.max(12, (100 * t.document_count) / max)}%` }}>
                        <div className="bg-mit-500" style={{ width: `${(100 * t.documents.mit) / tot}%` }} />
                        <div className="bg-student-500" style={{ width: `${(100 * t.documents.student) / tot}%` }} />
                      </div>
                      <div className="mt-2 flex items-center gap-3 text-xs font-semibold text-ink-muted">
                        <span className="text-mit-600">{t.documents.mit} MIT</span>
                        <span className="text-student-600">{t.documents.student} student</span>
                        <span>· {t.source_count} sources</span>
                        <span className="ml-auto flex items-center gap-1"><Layers className="size-3.5" />{t.flashcard_count}</span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="shared">
          <Card className="mb-4">
            <CardHeader>
              <CardTitle>Same section, different sources</CardTitle>
              <CardDescription>Section headings that appear (after normalisation) in notes from two or more sources — a quick way to compare how each source explains the same idea.</CardDescription>
            </CardHeader>
          </Card>
          {!shared ? <Skeleton className="h-64" /> : shared.length === 0 ? (
            <EmptyState icon="🧩" title="No overlaps found yet">Collect notes from more sources to find matching sections.</EmptyState>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {shared.map((g) => (
                <div key={g.key} className="card-surface p-4">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-display text-base font-semibold">{g.label}</h3>
                    <span className="chip bg-bio-100 text-bio-700">{g.source_count} sources</span>
                  </div>
                  <div className="mt-3 space-y-1.5">
                    {g.documents.slice(0, 5).map((d: any) => (
                      <Link key={d.id} href={`/notes/${d.id}?section=${d.section_index}`} className="flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm hover:bg-canvas">
                        <span className={cn("size-2.5 shrink-0 rounded-full", d.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
                        <span className="truncate">{d.title}</span>
                        <ArrowRight className="ml-auto size-3.5 shrink-0 text-ink-muted" />
                      </Link>
                    ))}
                    {g.document_count > 5 && <p className="px-2 text-xs text-ink-muted">+{g.document_count - 5} more</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

