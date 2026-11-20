"use client";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import { Search } from "lucide-react";
import { PageHeader } from "@/components/app-shell";
import { DocCard } from "@/components/doc-card";
import { CategoryToggle, Pager, SubjectPills } from "@/components/filters";
import { Input, Select } from "@/components/ui/input";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { useApi, type DocBrief } from "@/lib/api";
import { qs } from "@/lib/utils";

function NotesInner() {
  const sp = useSearchParams();
  const [q, setQ] = React.useState(sp.get("q") ?? "");
  const [query, setQuery] = React.useState(sp.get("q") ?? "");
  const [subject, setSubject] = React.useState(sp.get("subject") ?? "");
  const [category, setCategory] = React.useState(sp.get("category") ?? "");
  const [source, setSource] = React.useState(sp.get("source") ?? "");
  const [topic, setTopic] = React.useState(sp.get("topic") ?? "");
  const [fmt, setFmt] = React.useState("");
  const [sort, setSort] = React.useState("recent");
  const [page, setPage] = React.useState(1);
  React.useEffect(() => { const t = setTimeout(() => setQuery(q), 300); return () => clearTimeout(t); }, [q]);
  React.useEffect(() => setPage(1), [query, subject, category, source, topic, fmt, sort]);
  React.useEffect(() => { const v = sp.get("q"); if (v !== null) { setQ(v); setQuery(v); } }, [sp]);

  const { data, isLoading } = useApi<{ total: number; items: DocBrief[] }>(
    `/api/documents${qs({ q: query, subject, category, source, topic, fmt, sort, page, page_size: 24 })}`,
  );
  const { data: search } = useApi<any>(query.length >= 2 ? `/api/search?q=${encodeURIComponent(query)}&limit=24` : null);
  const snippets: Record<number, string> = React.useMemo(
    () => Object.fromEntries((search?.documents ?? []).map((d: any) => [d.id, d.snippet])),
    [search],
  );
  const { data: sources } = useApi<any[]>("/api/sources");
  const { data: topics } = useApi<any[]>(`/api/topics${qs({ subject })}`);

  return (
    <div>
      <PageHeader eyebrow="Library" title="Lecture notes" subtitle="Every collected document with its original source, author, licence and topics. Open one to read it alongside its flashcards." accent="from-phys-500 to-orange-400" />
      <div className="card-surface mb-6 space-y-4 p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-ink-muted" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search inside the notes (full text)…" className="pl-10" />
          </div>
          <CategoryToggle value={category} onChange={setCategory} />
        </div>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <SubjectPills value={subject} onChange={(v) => { setSubject(v); setTopic(""); }} />
          <div className="flex flex-wrap gap-2">
            <Select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
              <option value="">All sources</option>
              {sources?.map((s) => <option key={s.key} value={s.key}>{s.name}</option>)}
            </Select>
            <Select value={topic} onChange={(e) => setTopic(e.target.value)} aria-label="Topic" className="max-w-[200px]">
              <option value="">All topics</option>
              {topics?.filter((t) => t.document_count > 0).map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
            </Select>
            <Select value={fmt} onChange={(e) => setFmt(e.target.value)} aria-label="Format">
              <option value="">Any format</option>
              <option value="pdf">PDF</option><option value="html">HTML</option><option value="md">Markdown</option><option value="tex">LaTeX</option>
            </Select>
            <Select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort">
              <option value="recent">Newest</option><option value="title">Title</option><option value="words">Longest</option>
            </Select>
          </div>
        </div>
      </div>
      <p className="mb-3 text-sm font-semibold text-ink-muted">{data ? `${data.total} documents` : " "}</p>
      {isLoading && !data ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-56" />)}</div>
      ) : data?.items.length === 0 ? (
        <EmptyState icon="📭" title="No documents found">Try a different search, or collect more notes from the Data Collection page.</EmptyState>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data?.items.map((d) => <DocCard key={d.id} doc={{ ...d, snippet: snippets[d.id] }} />)}
        </div>
      )}
      {data && <Pager page={page} total={data.total} pageSize={24} onPage={setPage} />}
    </div>
  );
}

export default function NotesPage() {
  return <React.Suspense fallback={<Skeleton className="h-64" />}><NotesInner /></React.Suspense>;
}
