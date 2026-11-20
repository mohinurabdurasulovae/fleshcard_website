"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ExternalLink, Layers, Scale, User } from "lucide-react";
import { CategoryBadge, SubjectBadge } from "@/components/badges";
import { DocCard } from "@/components/doc-card";
import { Button } from "@/components/ui/button";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { useApi } from "@/lib/api";
import { CATEGORY_STYLE, cn } from "@/lib/utils";

export default function CourseDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: c, error } = useApi<any>(`/api/courses/${id}`);
  if (error) return <EmptyState icon="🤷" title="Course not found" />;
  if (!c) return <Skeleton className="h-64" />;
  const cat = CATEGORY_STYLE[c.category as "mit" | "student"];
  return (
    <div className="space-y-6">
      <Link href="/courses" className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-muted hover:text-ink"><ArrowLeft className="size-4" /> All courses</Link>
      <section className={cn("relative overflow-hidden rounded-4xl border p-6 shadow-soft sm:p-8", cat.soft, cat.border)}>
        <div className="flex flex-wrap gap-2"><CategoryBadge category={c.category} /><SubjectBadge subject={c.subject} /></div>
        <p className="mt-4 font-mono text-sm font-bold text-ink-muted">{c.code}</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">{c.title}</h1>
        <p className="mt-1 text-ink-muted">{[c.university, c.term].filter(Boolean).join(" · ")}</p>
        {c.description && <p className="mt-4 max-w-3xl text-[15px] text-ink-soft">{c.description}</p>}
        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink-soft">
          {c.instructors && <span className="flex items-center gap-1.5"><User className="size-4" />{c.instructors}</span>}
          {c.license && <span className="flex items-center gap-1.5"><Scale className="size-4" />{c.license}</span>}
          <span>Source: <b>{c.source.name}</b></span>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {c.document_count > 0 && (
            <Button asChild variant={c.category === "mit" ? "mit" : "student"}><Link href={`/flashcards?course=${c.id}&category=${c.category}`}><Layers /> Study {c.flashcard_count} flashcards</Link></Button>
          )}
          {c.url && <Button asChild variant="outline"><a href={c.url} target="_blank" rel="noreferrer"><ExternalLink /> Original course page</a></Button>}
        </div>
      </section>
      <div>
        <h2 className="mb-3 font-display text-2xl font-semibold">Lecture notes <span className="text-ink-muted">({c.documents.length})</span></h2>
        {c.documents.length === 0 ? (
          <EmptyState icon="📥" title="No documents collected yet">
            Start a collection job for <b>{c.source.name}</b> on the <Link className="font-semibold underline" href="/admin">Data Collection</Link> page.
          </EmptyState>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {c.documents.map((d: any) => <DocCard key={d.id} doc={d} />)}
          </div>
        )}
      </div>
    </div>
  );
}
