"use client";
import Link from "next/link";
import * as React from "react";
import {
  Ban, CheckCircle2, Database, ExternalLink, FileUp, Library, ListChecks, Pencil, Play, Plus, RefreshCw, RotateCcw, Server, Sparkles, Square, Terminal, Trash2,
} from "lucide-react";
import { PageHeader } from "@/components/app-shell";
import { CategoryBadge, FormatBadge, SubjectBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { EmptyState, Progress, Skeleton } from "@/components/ui/misc";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, useApi, useMeta, type Course, type DocBrief, type Job } from "@/lib/api";
import { SUBJECTS, SUBJECT_STYLE, cn, qs, timeAgo } from "@/lib/utils";

export default function AdminPage() {
  const { data: summary, mutate: mutateSummary } = useApi<any>("/api/admin/summary", { refreshInterval: 5000 });
  return (
    <div>
      <PageHeader eyebrow="Admin" title="Data collection" accent="from-slate-600 to-slate-400"
        subtitle="Start collection jobs, watch their progress, review collected documents, retry failed downloads and manage courses." />
      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label="Collected" value={summary?.status?.collected ?? 0} tone="text-emerald-600" />
        <Stat label="Failed" value={summary?.status?.failed ?? 0} tone="text-rose-600" />
        <Stat label="Pending review" value={summary?.review?.pending ?? 0} tone="text-amber-600" />
        <Stat label="Approved" value={summary?.review?.approved ?? 0} tone="text-bio-600" />
        <Stat label="Database" value={summary?.database?.startsWith("postgres") ? "PostgreSQL" : summary?.database ?? "–"} tone="text-ink" small />
        <Stat label="AI generation" value={summary?.ai?.enabled ? summary.ai.provider : "Off (rules)"} tone="text-cs-600" small />
      </div>
      <Tabs defaultValue="jobs">
        <TabsList>
          <TabsTrigger value="jobs"><Play /> Collection jobs</TabsTrigger>
          <TabsTrigger value="documents"><ListChecks /> Review documents</TabsTrigger>
          <TabsTrigger value="courses"><Library /> Courses</TabsTrigger>
          <TabsTrigger value="upload"><FileUp /> Upload</TabsTrigger>
        </TabsList>
        <TabsContent value="jobs"><JobsTab onChange={mutateSummary} /></TabsContent>
        <TabsContent value="documents"><DocumentsTab onChange={mutateSummary} /></TabsContent>
        <TabsContent value="courses"><CoursesTab /></TabsContent>
        <TabsContent value="upload"><UploadTab onChange={mutateSummary} /></TabsContent>
      </Tabs>
    </div>
  );
}

function Stat({ label, value, tone, small }: { label: string; value: React.ReactNode; tone: string; small?: boolean }) {
  return (
    <div className="card-surface p-4">
      <p className={cn("font-display font-semibold capitalize", small ? "text-lg" : "text-3xl", tone)}>{value}</p>
      <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">{label}</p>
    </div>
  );
}

// ------------------------------------------------------------------ jobs
function JobsTab({ onChange }: { onChange: () => void }) {
  const { data: meta } = useMeta();
  const { data: sources, mutate: mutateSources } = useApi<any[]>("/api/sources");
  const [subjects, setSubjects] = React.useState<string[]>([...SUBJECTS]);
  const [picked, setPicked] = React.useState<string[]>([]);
  const [maxPerSource, setMaxPerSource] = React.useState(0);
  const [maxPerCourse, setMaxPerCourse] = React.useState(8);
  const [genCards, setGenCards] = React.useState(true);
  const [useAi, setUseAi] = React.useState(false);
  const [force, setForce] = React.useState(false);
  const [err, setErr] = React.useState("");
  const [openJob, setOpenJob] = React.useState<number | null>(null);
  const { data: jobs, mutate: mutateJobs } = useApi<Job[]>("/api/admin/jobs", {
    refreshInterval: (latest?: Job[]) => (latest?.some((j: Job) => j.status === "running" || j.status === "queued") ? 1500 : 8000),
  });

  const visible = (sources ?? []).filter((s) => s.kind !== "upload" && s.subjects.some((x: string) => subjects.includes(x)));
  const toggle = (arr: string[], v: string) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  const start = async () => {
    setErr("");
    try {
      const j = await api.post<Job>("/api/admin/jobs", {
        subjects, source_keys: picked.length ? picked : visible.filter((s) => s.enabled).map((s) => s.key),
        max_docs_per_source: maxPerSource, max_docs_per_course: maxPerCourse, generate_flashcards: genCards, use_ai: useAi, force,
      });
      setOpenJob(j.id);
      mutateJobs(); onChange();
    } catch (e: any) { setErr(e.message); }
  };

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle>New collection job</CardTitle>
          <CardDescription>Choose subjects and sources. Leave all sources unticked to run every enabled source.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <Label>Subjects</Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {SUBJECTS.map((s) => (
                <button key={s} onClick={() => setSubjects((x) => toggle(x, s))}
                  className={cn("focus-ring chip border py-1.5 text-sm", subjects.includes(s) ? cn(SUBJECT_STYLE[s].chip, "border-transparent") : "border-line bg-white text-ink-muted")}>
                  {SUBJECT_STYLE[s].emoji} {s}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between">
              <Label>Sources ({picked.length || "all enabled"})</Label>
              {picked.length > 0 && <button className="text-xs font-semibold text-ink-muted underline" onClick={() => setPicked([])}>clear</button>}
            </div>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              {visible.map((s) => (
                <div key={s.key} onClick={() => setPicked((p) => toggle(p, s.key))} role="checkbox" aria-checked={picked.includes(s.key)} tabIndex={0}
                  onKeyDown={(e) => e.key === " " && (e.preventDefault(), setPicked((p) => toggle(p, s.key)))}
                  className={cn("focus-ring min-w-0 cursor-pointer rounded-2xl border-2 p-3 transition-all", picked.includes(s.key) ? (s.category === "mit" ? "border-mit-400 bg-mit-50" : "border-student-400 bg-student-50") : "border-line bg-white hover:border-ink/20", !s.enabled && "opacity-50")}>
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-semibold leading-snug">{s.name}</p>
                    <CategoryBadge category={s.category} short />
                  </div>
                  <p className="mt-1 text-xs text-ink-muted">{s.kind === "github" ? "GitHub repository" : s.kind === "mit_ocw" ? "OCW crawler" : s.kind === "pdf" ? "Direct PDF" : "Website crawler"} · {s.document_count} docs</p>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <a href={s.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} className="min-w-0 truncate text-[11px] text-student-600 hover:underline">{s.url.replace(/^https?:\/\//, "")}</a>
                    <button onClick={async (e) => { e.stopPropagation(); await api.patch(`/api/admin/sources/${s.key}`, { enabled: !s.enabled }); mutateSources(); }}
                      className="shrink-0 text-[11px] font-semibold text-ink-muted underline">{s.enabled ? "disable" : "enable"}</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><Label>Max documents per source (0 = no limit)</Label><Input type="number" min={0} value={maxPerSource} onChange={(e) => setMaxPerSource(Number(e.target.value))} className="mt-1" /></div>
            <div><Label>MIT: PDFs per course</Label><Input type="number" min={1} value={maxPerCourse} onChange={(e) => setMaxPerCourse(Number(e.target.value))} className="mt-1" /></div>
          </div>
          <div className="flex flex-wrap gap-4 text-sm font-semibold">
            <label className="flex items-center gap-2"><input type="checkbox" checked={genCards} onChange={(e) => setGenCards(e.target.checked)} className="accent-cs-500" /> Generate flashcards</label>
            <label className={cn("flex items-center gap-2", !meta?.ai.enabled && "opacity-50")}><input type="checkbox" disabled={!meta?.ai.enabled} checked={useAi} onChange={(e) => setUseAi(e.target.checked)} className="accent-cs-500" /> Use AI {meta?.ai.enabled ? "" : "(not configured)"}</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} className="accent-cs-500" /> Re-process existing</label>
          </div>
          {err && <p className="rounded-2xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</p>}
          <Button variant="primary" size="lg" onClick={start} disabled={!subjects.length}><Play /> Start collection</Button>
          <div className="rounded-2xl bg-ink p-4 text-sm text-white/90">
            <p className="flex items-center gap-2 font-semibold"><Terminal className="size-4" /> Prefer the terminal?</p>
            <code className="mt-2 block overflow-x-auto whitespace-pre text-xs text-emerald-200">cd backend{"\n"}python -m app.cli collect --subjects cs physics biology{"\n"}python -m app.cli collect --sources mit-ocw --max-per-course 5{"\n"}python -m app.cli retry</code>
          </div>
        </CardContent>
      </Card>

      <div className="min-w-0 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-display text-xl font-semibold">Jobs</h3>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={async () => { await api.post("/api/admin/retry-failed", {}); mutateJobs(); }}><RotateCcw /> Retry all failed</Button>
            <Button size="sm" variant="outline" onClick={async () => { if (confirm("Regenerate flashcards for every document? Rated cards are kept.")) { await api.post("/api/admin/regenerate", {}); mutateJobs(); } }}><Sparkles /> Regenerate cards</Button>
          </div>
        </div>
        {!jobs ? <Skeleton className="h-40" /> : jobs.length === 0 ? <EmptyState icon="🛰️" title="No jobs yet">Start your first collection on the left.</EmptyState> : (
          jobs.map((j) => <JobCard key={j.id} job={j} open={openJob === j.id} onToggle={() => setOpenJob(openJob === j.id ? null : j.id)} onCancel={async () => { await api.post(`/api/admin/jobs/${j.id}/cancel`); mutateJobs(); }} />)
        )}
      </div>
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  running: "bg-sky-100 text-sky-700", queued: "bg-amber-100 text-amber-800", completed: "bg-emerald-100 text-emerald-700",
  failed: "bg-rose-100 text-rose-700", cancelled: "bg-black/5 text-ink-soft",
};

function JobCard({ job: j, open, onToggle, onCancel }: { job: Job; open: boolean; onToggle: () => void; onCancel: () => void }) {
  const running = j.status === "running" || j.status === "queued";
  const { data: full } = useApi<Job>(open ? `/api/admin/jobs/${j.id}` : null, { refreshInterval: open && running ? 1500 : 0 });
  const logRef = React.useRef<HTMLPreElement>(null);
  React.useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [full?.log?.length]);
  return (
    <div className="card-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn("chip capitalize", STATUS_TONE[j.status])}>{running && <RefreshCw className="size-3 animate-spin" />}{j.status}</span>
        <span className="text-sm font-semibold">#{j.id} · {j.kind}</span>
        <span className="text-xs text-ink-muted">{timeAgo(j.created_at)}</span>
        <div className="ml-auto flex gap-1.5">
          {running && <Button size="sm" variant="danger" onClick={onCancel}><Square /> Stop</Button>}
          <Button size="sm" variant="soft" onClick={onToggle}>{open ? "Hide log" : "Log"}</Button>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <Progress value={j.total ? (100 * j.processed) / j.total : running ? 5 : 100} />
        <span className="shrink-0 text-xs font-bold text-ink-muted">{j.processed}/{j.total || "?"}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs font-semibold">
        <span className="text-emerald-600">✓ {j.succeeded} collected</span>
        <span className="text-ink-muted">· {j.skipped} skipped</span>
        <span className="text-rose-600">✗ {j.failed} failed</span>
        {j.subjects.length > 0 && <span className="text-ink-muted">· {j.subjects.map((s) => SUBJECT_STYLE[s]?.short ?? s).join(", ")}</span>}
      </div>
      {running && j.current && <p className="mt-1 truncate text-xs text-ink-muted">Now: {j.current}</p>}
      {open && (
        <pre ref={logRef} className="scrollbar-thin mt-3 max-h-72 overflow-auto rounded-2xl bg-ink p-3 text-[11px] leading-5 text-white/85">
          {(full?.log ?? j.log_tail).join("\n") || "No log yet"}
        </pre>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ documents review
function DocumentsTab({ onChange }: { onChange: () => void }) {
  const [status, setStatus] = React.useState("collected");
  const [review, setReview] = React.useState("");
  const [q, setQ] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [editing, setEditing] = React.useState<DocBrief | null>(null);
  const [busy, setBusy] = React.useState<number | null>(null);
  const { data, mutate } = useApi<{ total: number; items: DocBrief[] }>(`/api/documents${qs({ status, review, q, page, page_size: 20, sort: "recent" })}`);
  React.useEffect(() => setPage(1), [status, review, q]);
  const act = async (id: number, fn: () => Promise<any>) => {
    setBusy(id);
    try { await fn(); } catch (e: any) { alert(e.message); } finally { setBusy(null); mutate(); onChange(); }
  };

  return (
    <div className="space-y-4">
      <div className="card-surface flex flex-col gap-3 p-4 md:flex-row md:items-center">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by title or text…" className="md:max-w-xs" />
        <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="collected">Collected</option><option value="failed">Failed downloads</option><option value="all">All statuses</option>
        </Select>
        <Select value={review} onChange={(e) => setReview(e.target.value)} aria-label="Review">
          <option value="">Any review state</option><option value="pending">Pending review</option><option value="approved">Approved</option><option value="rejected">Rejected</option>
        </Select>
        <span className="text-sm font-semibold text-ink-muted md:ml-auto">{data?.total ?? 0} documents</span>
        {status === "failed" && (data?.total ?? 0) > 0 && (
          <Button size="sm" variant="outline" onClick={async () => { await api.post("/api/admin/retry-failed", {}); alert("Retry job started. Follow its progress in the Collection jobs tab."); }}><RotateCcw /> Retry all</Button>
        )}
      </div>
      {!data ? <Skeleton className="h-64" /> : data.items.length === 0 ? <EmptyState icon="✨" title="Nothing here" /> : (
        <div className="card-surface overflow-x-auto p-2">
          <table className="w-full min-w-[860px] text-sm">
            <thead><tr className="text-left text-xs uppercase tracking-wider text-ink-muted"><th className="p-3">Document</th><th>Source</th><th>Status</th><th>Cards</th><th className="text-right pr-3">Actions</th></tr></thead>
            <tbody>
              {data.items.map((d) => (
                <tr key={d.id} className="border-t border-line align-top">
                  <td className="max-w-[340px] p-3">
                    <div className="flex items-center gap-2">
                      <span className={cn("size-2.5 shrink-0 rounded-full", d.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
                      {d.status === "collected" ? <Link href={`/notes/${d.id}`} className="truncate font-semibold hover:underline">{d.title}</Link> : <span className="truncate font-semibold">{d.title}</span>}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5 pl-[18px]">
                      <SubjectBadge subject={d.subject} />{d.format && <FormatBadge format={d.format} />}
                      <a href={d.url} target="_blank" rel="noreferrer" className="text-xs text-student-600 hover:underline"><ExternalLink className="inline size-3" /> original</a>
                    </div>
                    {d.error && <p className="mt-1 line-clamp-2 pl-[18px] text-xs text-rose-600">{d.error}</p>}
                  </td>
                  <td className="py-3 text-xs text-ink-muted">{d.source?.name}<br />{d.course?.code}</td>
                  <td className="py-3">
                    <span className={cn("chip capitalize", d.status === "collected" ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700")}>{d.status}</span>
                    {d.status === "collected" && <span className={cn("chip ml-1 capitalize", d.review_status === "approved" ? "bg-bio-100 text-bio-700" : d.review_status === "rejected" ? "bg-black/5 text-ink-muted line-through" : "bg-amber-100 text-amber-800")}>{d.review_status}</span>}
                    {d.attempts > 1 && <p className="mt-1 text-[11px] text-ink-muted">{d.attempts} attempts</p>}
                  </td>
                  <td className="py-3 font-semibold">{d.flashcard_count ?? 0}</td>
                  <td className="py-3 pr-3">
                    <div className="flex flex-wrap justify-end gap-1">
                      {d.status === "failed" && <IconBtn label="Retry" disabled={busy === d.id} onClick={() => act(d.id, () => api.post("/api/admin/retry-failed", { document_ids: [d.id] }))}><RotateCcw /></IconBtn>}
                      {d.status === "collected" && (
                        <>
                          <IconBtn label="Approve" onClick={() => act(d.id, () => api.patch(`/api/documents/${d.id}`, { review_status: "approved" }))}><CheckCircle2 className="text-emerald-600" /></IconBtn>
                          <IconBtn label="Reject (hide from site)" onClick={() => act(d.id, () => api.patch(`/api/documents/${d.id}`, { review_status: "rejected" }))}><Ban className="text-amber-600" /></IconBtn>
                          <IconBtn label="Regenerate flashcards" disabled={busy === d.id} onClick={() => act(d.id, () => api.post(`/api/documents/${d.id}/flashcards/generate`, {}))}><Sparkles className="text-cs-600" /></IconBtn>
                          <IconBtn label="Edit" onClick={() => setEditing(d)}><Pencil /></IconBtn>
                        </>
                      )}
                      <IconBtn label="Delete" onClick={() => confirm(`Delete “${d.title}” and its flashcards?`) && act(d.id, () => api.del(`/api/documents/${d.id}`))}><Trash2 className="text-rose-600" /></IconBtn>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-center gap-2 p-3 text-sm">
            <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
            <span className="font-semibold text-ink-muted">Page {page} / {Math.max(1, Math.ceil(data.total / 20))}</span>
            <Button size="sm" variant="outline" disabled={page * 20 >= data.total} onClick={() => setPage(page + 1)}>Next</Button>
          </div>
        </div>
      )}
      {editing && <EditDocDialog doc={editing} onClose={() => { setEditing(null); mutate(); }} />}
    </div>
  );
}

function IconBtn({ label, children, onClick, disabled }: { label: string; children: React.ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <button title={label} aria-label={label} disabled={disabled} onClick={onClick}
      className="focus-ring grid size-8 place-items-center rounded-xl text-ink-soft hover:bg-black/[.05] disabled:opacity-40 [&_svg]:size-4">
      {children}
    </button>
  );
}

function EditDocDialog({ doc, onClose }: { doc: DocBrief; onClose: () => void }) {
  const [f, setF] = React.useState({ title: doc.title, subject: doc.subject, author: doc.author, license: doc.license });
  const [err, setErr] = React.useState("");
  const save = async () => { try { await api.patch(`/api/documents/${doc.id}`, f); onClose(); } catch (e: any) { setErr(e.message); } };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogTitle>Edit document</DialogTitle>
        <DialogDescription>Correct metadata extracted from the source.</DialogDescription>
        <div className="mt-4 space-y-3">
          <div><Label>Title</Label><Input className="mt-1" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></div>
          <div><Label>Subject</Label><Select className="mt-1 w-full" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })}>{SUBJECTS.map((s) => <option key={s}>{s}</option>)}</Select></div>
          <div><Label>Author</Label><Input className="mt-1" value={f.author} onChange={(e) => setF({ ...f, author: e.target.value })} /></div>
          <div><Label>Licence</Label><Textarea className="mt-1" value={f.license} onChange={(e) => setF({ ...f, license: e.target.value })} /></div>
          {err && <p className="text-sm text-rose-600">{err}</p>}
          <Button onClick={save} className="w-full">Save</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ------------------------------------------------------------------ courses
function CoursesTab() {
  const [q, setQ] = React.useState("");
  const [editing, setEditing] = React.useState<Partial<Course> | null>(null);
  const { data, mutate } = useApi<{ total: number; items: Course[] }>(`/api/courses${qs({ q, page_size: 100 })}`);
  return (
    <div className="space-y-4">
      <div className="card-surface flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search courses…" className="sm:max-w-xs" />
        <span className="text-sm font-semibold text-ink-muted sm:ml-auto">{data?.total ?? 0} courses</span>
        <Button size="sm" onClick={() => setEditing({ subject: "Computer Science" })}><Plus /> Add course</Button>
      </div>
      <div className="card-surface overflow-x-auto p-2">
        <table className="w-full min-w-[760px] text-sm">
          <thead><tr className="text-left text-xs uppercase tracking-wider text-ink-muted"><th className="p-3">Course</th><th>Subject</th><th>Source</th><th>Docs</th><th className="pr-3 text-right">Actions</th></tr></thead>
          <tbody>
            {data?.items.map((c) => (
              <tr key={c.id} className="border-t border-line">
                <td className="p-3"><Link href={`/courses/${c.id}`} className="font-semibold hover:underline">{c.code}</Link><span className="block max-w-[320px] truncate text-xs text-ink-muted">{c.title} · {c.university}</span></td>
                <td><SubjectBadge subject={c.subject} /></td>
                <td className="text-xs text-ink-muted">{c.source.name}</td>
                <td className="font-semibold">{c.document_count}</td>
                <td className="pr-3">
                  <div className="flex justify-end gap-1">
                    <IconBtn label="Edit" onClick={() => setEditing(c)}><Pencil /></IconBtn>
                    <IconBtn label="Delete" onClick={async () => { if (confirm(`Delete course ${c.code}? Documents are kept.`)) { await api.del(`/api/courses/${c.id}`); mutate(); } }}><Trash2 className="text-rose-600" /></IconBtn>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && <CourseDialog course={editing} onClose={() => { setEditing(null); mutate(); }} />}
    </div>
  );
}

function CourseDialog({ course, onClose }: { course: Partial<Course>; onClose: () => void }) {
  const { data: sources } = useApi<any[]>("/api/sources");
  const isNew = !course.id;
  const [f, setF] = React.useState<any>({
    source_key: course.source?.key ?? "mit-ocw", code: course.code ?? "", title: course.title ?? "", subject: course.subject ?? "Computer Science",
    university: course.university ?? "", url: course.url ?? "", term: course.term ?? "", instructors: course.instructors ?? "", description: course.description ?? "",
  });
  const [err, setErr] = React.useState("");
  const save = async () => {
    try { isNew ? await api.post("/api/courses", f) : await api.patch(`/api/courses/${course.id}`, f); onClose(); } catch (e: any) { setErr(e.message); }
  };
  const field = (k: string, label: string) => <div><Label>{label}</Label><Input className="mt-1" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></div>;
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogTitle>{isNew ? "Add course" : `Edit ${course.code}`}</DialogTitle>
        <DialogDescription>{isNew ? "New MIT courses are picked up by the OCW collector on the next run." : "Update course metadata."}</DialogDescription>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {isNew && (
            <div className="sm:col-span-2"><Label>Source</Label>
              <Select className="mt-1 w-full" value={f.source_key} onChange={(e) => setF({ ...f, source_key: e.target.value })}>{sources?.map((s) => <option key={s.key} value={s.key}>{s.name}</option>)}</Select>
            </div>
          )}
          {field("code", "Code")}
          <div><Label>Subject</Label><Select className="mt-1 w-full" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })}>{SUBJECTS.map((s) => <option key={s}>{s}</option>)}</Select></div>
          <div className="sm:col-span-2">{field("title", "Title")}</div>
          {field("university", "University")}
          {field("term", "Term")}
          <div className="sm:col-span-2">{field("url", "Course URL (e.g. https://ocw.mit.edu/courses/…/)")}</div>
          <div className="sm:col-span-2">{field("instructors", "Instructors")}</div>
          <div className="sm:col-span-2"><Label>Description</Label><Textarea className="mt-1" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></div>
        </div>
        {err && <p className="mt-2 text-sm text-rose-600">{err}</p>}
        <Button onClick={save} className="mt-4 w-full">Save</Button>
      </DialogContent>
    </Dialog>
  );
}

// ------------------------------------------------------------------ upload
function UploadTab({ onChange }: { onChange: () => void }) {
  const [file, setFile] = React.useState<File | null>(null);
  const [f, setF] = React.useState({ subject: "Computer Science", category: "student", title: "", course_code: "", course_title: "", university: "", author: "", license: "", url: "" });
  const [msg, setMsg] = React.useState<{ ok: boolean; text: string; id?: number } | null>(null);
  const [busy, setBusy] = React.useState(false);
  const submit = async () => {
    if (!file) return;
    setBusy(true); setMsg(null);
    const form = new FormData();
    form.append("file", file);
    Object.entries(f).forEach(([k, v]) => form.append(k, v || (k === "course_code" ? "General" : "")));
    form.set("source_key", f.category === "mit" ? "mit-upload" : "manual-upload");
    try {
      const d = await api.upload<DocBrief>("/api/documents/upload", form);
      setMsg({ ok: true, text: `Added “${d.title}”.`, id: d.id }); onChange();
    } catch (e: any) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };
  const field = (k: keyof typeof f, label: string) => <div><Label>{label}</Label><Input className="mt-1" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></div>;
  return (
    <Card className="max-w-3xl">
      <CardHeader><CardTitle>Upload a document</CardTitle><CardDescription>Add PDF, HTML, Markdown or LaTeX notes you have the right to use. They are processed like collected documents.</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-3xl border-2 border-dashed border-line bg-canvas/60 p-8 text-center hover:border-cs-500/50">
          <FileUp className="size-8 text-cs-500" />
          <span className="text-sm font-semibold">{file ? file.name : "Choose a file (.pdf, .html, .md, .tex)"}</span>
          <input type="file" accept=".pdf,.html,.htm,.md,.markdown,.tex" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <div><Label>Subject</Label><Select className="mt-1 w-full" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })}>{SUBJECTS.map((s) => <option key={s}>{s}</option>)}</Select></div>
          <div><Label>Category</Label><Select className="mt-1 w-full" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}><option value="student">Student-created</option><option value="mit">MIT OpenCourseWare</option></Select></div>
          {field("title", "Title")}{field("url", "Original URL")}
          {field("course_code", "Course code")}{field("course_title", "Course title")}
          {field("university", "University")}{field("author", "Author")}
          <div className="sm:col-span-2">{field("license", "Licence")}</div>
        </div>
        {msg && <p className={cn("rounded-2xl px-3 py-2 text-sm", msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-rose-50 text-rose-700")}>{msg.text} {msg.id && <Link className="font-semibold underline" href={`/notes/${msg.id}`}>Open</Link>}</p>}
        <Button variant="primary" disabled={!file || busy} onClick={submit}><Database /> {busy ? "Processing…" : "Upload & process"}</Button>
        <p className="flex items-center gap-1.5 text-xs text-ink-muted"><Server className="size-3.5" /> Files are stored in backend/data/files.</p>
      </CardContent>
    </Card>
  );
}
