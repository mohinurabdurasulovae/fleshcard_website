"use client";
import Link from "next/link";
import * as React from "react";
import { FileText, Layers, Search, University } from "lucide-react";
import { PageHeader } from "@/components/app-shell";
import { CategoryBadge, SubjectBadge } from "@/components/badges";
import { CategoryToggle, Pager, SubjectPills } from "@/components/filters";
import { Input, Select } from "@/components/ui/input";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { useApi, type Course } from "@/lib/api";
import { SUBJECT_STYLE, cn, qs } from "@/lib/utils";

export default function CoursesPage() {
  const [subject, setSubject] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [university, setUniversity] = React.useState("");
  const [source, setSource] = React.useState("");
  const [q, setQ] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [withDocs, setWithDocs] = React.useState(false);
  const [page, setPage] = React.useState(1);
  React.useEffect(() => { const t = setTimeout(() => setQuery(q), 250); return () => clearTimeout(t); }, [q]);
  React.useEffect(() => setPage(1), [subject, category, university, source, query, withDocs]);

  const { data, isLoading } = useApi<{ total: number; items: Course[] }>(
    `/api/courses${qs({ subject, category, university, source, q: query, has_documents: withDocs, page, page_size: 24 })}`,
  );
  const { data: unis } = useApi<string[]>("/api/universities");
  const { data: sources } = useApi<any[]>("/api/sources");

  return (
    <div>
      <PageHeader eyebrow="Explore" title="Courses" subtitle="Browse courses from MIT OpenCourseWare and student-written notes by subject, university and source." accent="from-student-500 to-sky-400" />
      <div className="card-surface mb-6 space-y-4 p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-ink-muted" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by course code, title, instructor…" className="pl-10" />
          </div>
          <CategoryToggle value={category} onChange={setCategory} />
        </div>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <SubjectPills value={subject} onChange={setSubject} />
          <div className="flex flex-wrap gap-2">
            <Select value={university} onChange={(e) => setUniversity(e.target.value)} aria-label="University">
              <option value="">All universities</option>
              {unis?.map((u) => <option key={u}>{u}</option>)}
            </Select>
            <Select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
              <option value="">All sources</option>
              {sources?.map((s) => <option key={s.key} value={s.key}>{s.name}</option>)}
            </Select>
            <label className="flex cursor-pointer items-center gap-2 rounded-2xl border border-line bg-white px-3 text-sm font-semibold">
              <input type="checkbox" checked={withDocs} onChange={(e) => setWithDocs(e.target.checked)} className="accent-cs-500" /> With notes only
            </label>
          </div>
        </div>
      </div>

      <p className="mb-3 text-sm font-semibold text-ink-muted">{data ? `${data.total} courses` : " "}</p>
      {isLoading && !data ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-48" />)}</div>
      ) : data && data.items.length === 0 ? (
        <EmptyState icon="🔎" title="No courses match">Try clearing a filter.</EmptyState>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data?.items.map((c) => <CourseCard key={c.id} course={c} />)}
        </div>
      )}
      {data && <Pager page={page} total={data.total} pageSize={24} onPage={setPage} />}
    </div>
  );
}

function CourseCard({ course: c }: { course: Course }) {
  const s = SUBJECT_STYLE[c.subject];
  return (
    <Link href={`/courses/${c.id}`} className="card-surface focus-ring group relative flex flex-col overflow-hidden p-5 transition-all hover:-translate-y-0.5 hover:shadow-lift">
      <div className={cn("absolute -right-8 -top-8 size-28 rounded-full opacity-60 blur-2xl transition-opacity group-hover:opacity-100", c.category === "mit" ? "bg-mit-200" : "bg-student-200")} />
      <div className="relative flex items-center justify-between gap-2">
        <span className={cn("rounded-xl px-2.5 py-1 font-mono text-sm font-bold", s?.chip)}>{c.code.length > 22 ? c.code.slice(0, 22) + "…" : c.code}</span>
        <CategoryBadge category={c.category} short />
      </div>
      <h3 className="relative mt-3 line-clamp-2 font-display text-lg font-semibold leading-snug">{c.title}</h3>
      <p className="relative mt-1 flex items-center gap-1.5 text-xs font-medium text-ink-muted">
        <University className="size-3.5" /> {c.university || "—"} {c.term && `· ${c.term}`}
      </p>
      {c.description && <p className="relative mt-2 line-clamp-2 text-sm text-ink-muted">{c.description}</p>}
      <div className="relative mt-auto flex items-center gap-3 pt-4 text-xs font-semibold text-ink-muted">
        <SubjectBadge subject={c.subject} />
        <span className="ml-auto flex items-center gap-1"><FileText className="size-3.5" />{c.document_count ?? 0}</span>
        <span className="flex items-center gap-1"><Layers className="size-3.5" />{c.flashcard_count ?? 0}</span>
      </div>
    </Link>
  );
}
