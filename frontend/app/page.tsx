"use client";
import Link from "next/link";
import { ArrowRight, BookOpenText, Compass, FileText, GraduationCap, Layers, Library, Sparkles, Star, Users } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DocCard } from "@/components/doc-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { useApi } from "@/lib/api";
import { CATEGORY_STYLE, SUBJECT_STYLE, TYPE_STYLE, cn, compact, fmt } from "@/lib/utils";

export default function Dashboard() {
  const { data, isLoading } = useApi<any>("/api/dashboard");

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-56" />
        <div className="grid gap-4 md:grid-cols-3"><Skeleton className="h-72" /><Skeleton className="h-72" /><Skeleton className="h-72" /></div>
      </div>
    );
  }
  const t = data.totals;
  const mit = data.by_category.mit;
  const stu = data.by_category.student;
  const docTotal = mit.documents + stu.documents || 1;
  const subjectPie = data.by_subject.map((s: any) => ({ name: s.subject, value: s.mit_documents + s.student_documents }));
  const subjectBars = data.by_subject.map((s: any) => ({ subject: SUBJECT_STYLE[s.subject]?.short ?? s.subject, MIT: s.mit_documents, Student: s.student_documents }));
  const typeBars = data.by_card_type.map((r: any) => ({ type: TYPE_STYLE[r.type]?.label ?? r.type, MIT: r.mit, Student: r.student }));

  return (
    <div className="space-y-6">
      {/* hero */}
      <section className="relative overflow-hidden rounded-4xl bg-ink p-6 text-white shadow-lift animate-fade-up sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-24 size-72 rounded-full bg-cs-500/40 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 right-40 size-72 rounded-full bg-student-500/40 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -left-10 size-56 rounded-full bg-mit-500/30 blur-3xl" />
        <div className="relative grid gap-8 lg:grid-cols-[1.3fr_1fr] lg:items-center">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold"><Sparkles className="size-3.5" /> Computer Science · Physics · Biology</p>
            <h1 className="mt-4 font-display text-3xl font-semibold leading-tight tracking-tight sm:text-[42px]">
              University lecture notes,<br className="hidden sm:block" /> turned into <span className="bg-gradient-to-r from-pink-300 via-amber-200 to-sky-300 bg-clip-text text-transparent">flashcards you can trust</span>.
            </h1>
            <p className="mt-3 max-w-xl text-[15px] text-white/70">
              Compare MIT OpenCourseWare with student-written notes. Every card links back to the exact passage it came from.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Button asChild size="lg" className="bg-white text-ink hover:bg-white/90"><Link href="/flashcards"><Layers /> Study flashcards</Link></Button>
              <Button asChild size="lg" variant="ghost" className="text-white hover:bg-white/10 hover:text-white"><Link href="/evaluate"><Star /> Rate cards</Link></Button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Courses", value: t.courses, icon: Library, tint: "from-student-400/30" },
              { label: "Documents", value: t.documents, icon: FileText, tint: "from-phys-500/30" },
              { label: "Flashcards", value: t.flashcards, icon: Layers, tint: "from-pink-500/30" },
              { label: "Evaluations", value: t.evaluations, icon: Star, tint: "from-bio-500/30" },
            ].map(({ label, value, icon: Icon, tint }) => (
              <div key={label} className={cn("rounded-3xl bg-gradient-to-br to-white/5 p-4 ring-1 ring-white/10", tint)}>
                <Icon className="size-5 text-white/70" />
                <p className="mt-3 font-display text-3xl font-semibold">{compact(value)}</p>
                <p className="text-xs font-semibold uppercase tracking-wider text-white/60">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* MIT vs Student */}
      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>MIT vs student-created notes</CardTitle>
            <CardDescription>How the collection splits between the two kinds of source.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-5 flex h-4 overflow-hidden rounded-full bg-black/5">
              <div className="bg-mit-500 transition-all" style={{ width: `${(100 * mit.documents) / docTotal}%` }} />
              <div className="bg-student-500 transition-all" style={{ width: `${(100 * stu.documents) / docTotal}%` }} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {(["mit", "student"] as const).map((cat) => {
                const s = data.by_category[cat];
                const st = CATEGORY_STYLE[cat];
                const Icon = cat === "mit" ? GraduationCap : Users;
                return (
                  <div key={cat} className={cn("rounded-3xl p-4", st.soft)}>
                    <div className="flex items-center gap-2">
                      <span className={cn("grid size-9 place-items-center rounded-xl", st.solid)}><Icon className="size-4" /></span>
                      <p className="font-display text-lg font-semibold">{st.label}</p>
                      <span className={cn("ml-auto text-sm font-bold", st.text)}>{fmt((100 * s.documents) / docTotal)}%</span>
                    </div>
                    <div className="mt-4 grid grid-cols-4 gap-2 text-center">
                      {[["Courses", s.courses], ["Docs", s.documents], ["Cards", s.flashcards], ["Words", s.words]].map(([l, v]) => (
                        <div key={l as string} className="rounded-2xl bg-white/80 px-1 py-2">
                          <p className="font-display text-lg font-semibold">{compact(v as number)}</p>
                          <p className="text-[11px] font-semibold uppercase text-ink-muted">{l}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
            {mit.documents === 0 && (
              <p className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
                No MIT documents yet. Start a collection job from <Link href="/admin" className="font-semibold underline">Data Collection</Link> or run{" "}
                <code className="rounded bg-white px-1.5 py-0.5 text-xs">python -m app.cli collect --sources mit-ocw</code>.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Subject distribution</CardTitle>
            <CardDescription>Documents per subject</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-52">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={subjectPie} dataKey="value" nameKey="name" innerRadius={52} outerRadius={84} paddingAngle={3} cornerRadius={8} stroke="none">
                    {subjectPie.map((s: any) => <Cell key={s.name} fill={SUBJECT_STYLE[s.name]?.hex} />)}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 16, border: "1px solid #ECE4D9" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 space-y-2">
              {subjectPie.map((s: any) => (
                <div key={s.name} className="flex items-center gap-2 text-sm">
                  <span className={cn("size-3 rounded-full", SUBJECT_STYLE[s.name]?.dot)} />
                  <span className="font-medium">{s.name}</span>
                  <span className="ml-auto font-semibold text-ink-muted">{s.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Documents by subject & source</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer>
              <BarChart data={subjectBars} barGap={4}>
                <CartesianGrid vertical={false} stroke="#F1EBE2" />
                <XAxis dataKey="subject" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} width={32} />
                <Tooltip cursor={{ fill: "rgba(0,0,0,.03)" }} contentStyle={{ borderRadius: 16, border: "1px solid #ECE4D9" }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="MIT" fill={CATEGORY_STYLE.mit.hex} radius={[8, 8, 0, 0]} />
                <Bar dataKey="Student" fill={CATEGORY_STYLE.student.hex} radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Flashcards by type</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer>
              <BarChart data={typeBars} layout="vertical" barGap={2}>
                <CartesianGrid horizontal={false} stroke="#F1EBE2" />
                <XAxis type="number" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis type="category" dataKey="type" tickLine={false} axisLine={false} fontSize={12} width={88} />
                <Tooltip cursor={{ fill: "rgba(0,0,0,.03)" }} contentStyle={{ borderRadius: 16, border: "1px solid #ECE4D9" }} />
                <Bar dataKey="MIT" stackId="a" fill={CATEGORY_STYLE.mit.hex} />
                <Bar dataKey="Student" stackId="a" fill={CATEGORY_STYLE.student.hex} radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>

      {/* recent + topics */}
      <section className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-2xl font-semibold">Recently added</h2>
            <Button asChild variant="ghost" size="sm"><Link href="/notes">All notes <ArrowRight /></Link></Button>
          </div>
          {data.recent_documents.length === 0 ? (
            <EmptyState icon="📚" title="No documents yet">Run a collection job to bring in lecture notes.</EmptyState>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {data.recent_documents.slice(0, 6).map((d: any) => <DocCard key={d.id} doc={d} />)}
            </div>
          )}
        </div>
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Popular topics</CardTitle><CardDescription>Most covered across all sources</CardDescription></CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {data.top_topics.map((tp: any) => (
                <Link key={tp.id} href={`/topics/${tp.slug}`} className={cn("chip py-1.5 text-[13px] transition-transform hover:scale-105", SUBJECT_STYLE[tp.subject]?.chip)}>
                  {tp.name} <span className="opacity-60">{tp.document_count}</span>
                </Link>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Sources</CardTitle></CardHeader>
            <CardContent className="space-y-1">
              {data.sources.map((s: any) => (
                <a key={s.id} href={s.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm hover:bg-canvas">
                  <span className={cn("size-2.5 shrink-0 rounded-full", s.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
                  <span className="truncate">{s.name}</span>
                  <span className="ml-auto text-xs font-semibold text-ink-muted">{s.document_count}</span>
                </a>
              ))}
            </CardContent>
          </Card>
          <div className="grid grid-cols-2 gap-3">
            <Link href="/courses" className="card-surface flex flex-col gap-2 p-4 transition-all hover:-translate-y-0.5"><Compass className="size-5 text-student-500" /><span className="text-sm font-semibold">Explore courses</span></Link>
            <Link href="/topics" className="card-surface flex flex-col gap-2 p-4 transition-all hover:-translate-y-0.5"><BookOpenText className="size-5 text-bio-500" /><span className="text-sm font-semibold">Browse topics</span></Link>
          </div>
        </div>
      </section>
    </div>
  );
}
