"use client";
import Link from "next/link";
import * as React from "react";
import { Download, FileJson, FileSpreadsheet, GraduationCap, Scale, Trophy, Users } from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { PageHeader } from "@/components/app-shell";
import { SubjectPills } from "@/components/filters";
import { Inline } from "@/components/rich-text";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { useApi } from "@/lib/api";
import { CATEGORY_STYLE, RATING_STYLE, SUBJECT_STYLE, TYPE_STYLE, cn, fmt, qs } from "@/lib/utils";

const MIT = CATEGORY_STYLE.mit.hex;
const STU = CATEGORY_STYLE.student.hex;
const tip = { borderRadius: 16, border: "1px solid #ECE4D9", fontSize: 12 };

export default function StatisticsPage() {
  const [evaluator, setEvaluator] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [docCat, setDocCat] = React.useState("");
  const params = qs({ evaluator, subject });
  const { data, isLoading } = useApi<any>(`/api/stats/overview${params}`);

  const exportLinks = (
    <div className="flex flex-wrap gap-2">
      <Button asChild variant="outline" size="sm"><a href={`/api/stats/export${qs({ format: "csv", evaluator, subject })}`}><FileSpreadsheet /> Ratings CSV</a></Button>
      <Button asChild variant="outline" size="sm"><a href={`/api/stats/export${qs({ format: "json", evaluator, subject })}`}><FileJson /> Ratings JSON</a></Button>
      <Button asChild variant="outline" size="sm"><a href={`/api/stats/export${qs({ format: "csv", scope: "summary", evaluator, subject })}`}><Download /> Summary CSV</a></Button>
      <Button asChild variant="outline" size="sm"><a href={`/api/stats/export${qs({ format: "json", scope: "summary", evaluator, subject })}`}><Download /> Summary JSON</a></Button>
      <Button asChild variant="ghost" size="sm"><a href={`/api/flashcards/export${qs({ format: "csv", subject })}`}><Download /> All flashcards CSV</a></Button>
    </div>
  );

  return (
    <div>
      <PageHeader eyebrow="Results" title="Statistics" accent="from-violet-500 to-fuchsia-500"
        subtitle="How evaluators rate MIT-based versus student-note-based flashcards, overall, per criterion, per card type and per document." />

      <div className="card-surface mb-6 flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <Select value={evaluator} onChange={(e) => setEvaluator(e.target.value)} aria-label="Evaluator">
            <option value="">All evaluators</option>
            {data?.evaluators?.map((e: string) => <option key={e}>{e}</option>)}
          </Select>
          <SubjectPills value={subject} onChange={setSubject} />
        </div>
        {exportLinks}
      </div>

      {isLoading && !data ? <Skeleton className="h-96" /> : !data || data.total_evaluations === 0 ? (
        <EmptyState icon="📊" title="No ratings yet">
          Rate a few flashcards on the <Link href="/evaluate" className="font-semibold underline">Evaluation</Link> page and the comparison will appear here.
        </EmptyState>
      ) : (
        <Results data={data} docCat={docCat} setDocCat={setDocCat} />
      )}
    </div>
  );
}

function Results({ data, docCat, setDocCat }: { data: any; docCat: string; setDocCat: (v: string) => void }) {
  const s = data.summary;
  const pref = data.preference;
  const dist = [1, 2, 3, 4, 5].map((lvl) => ({
    label: RATING_STYLE[lvl].label,
    MIT: s.mit.distribution[lvl - 1].pct,
    Student: s.student.distribution[lvl - 1].pct,
  }));
  const radar = data.criteria.map((c: any) => ({ criterion: c.label, MIT: c.mit ?? 0, Student: c.student ?? 0 }));
  const types = data.by_type.map((r: any) => ({ ...r, label: TYPE_STYLE[r.key]?.label ?? r.key }));
  const docs = data.by_document.filter((d: any) => !docCat || d.category === docCat);

  return (
    <div className="space-y-5">
      {/* head to head */}
      <section className="grid gap-4 lg:grid-cols-[1fr_1fr_1.1fr]">
        {(["mit", "student"] as const).map((cat) => {
          const x = s[cat];
          const st = CATEGORY_STYLE[cat];
          const Icon = cat === "mit" ? GraduationCap : Users;
          return (
            <div key={cat} className={cn("relative overflow-hidden rounded-4xl border p-5 shadow-soft", st.soft, st.border)}>
              <div className="flex items-center gap-2">
                <span className={cn("grid size-9 place-items-center rounded-xl", st.solid)}><Icon className="size-4" /></span>
                <p className="font-display text-lg font-semibold">{st.label} flashcards</p>
              </div>
              <p className={cn("mt-4 font-display text-5xl font-semibold", st.text)}>{fmt(x.mean_score, 2)}<span className="text-xl text-ink-muted"> / 5</span></p>
              <p className="text-xs font-semibold text-ink-muted">mean quality score {x.sd != null && `· SD ${fmt(x.sd, 2)}`}</p>
              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <Mini label="Ratings" value={fmt(x.evaluations)} />
                <Mini label="Positive" value={x.pct_positive != null ? `${fmt(x.pct_positive)}%` : "–"} />
                <Mini label="Negative" value={x.pct_negative != null ? `${fmt(x.pct_negative)}%` : "–"} />
              </div>
              <p className="mt-3 text-xs text-ink-muted">{x.cards_rated} of {x.total_cards} cards rated</p>
            </div>
          );
        })}
        <div className="rounded-4xl bg-ink p-5 text-white shadow-lift">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-white/60"><Trophy className="size-4" /> Preference</p>
          {pref ? (
            <>
              <p className="mt-3 font-display text-2xl font-semibold leading-snug">
                {pref.preferred === "tie" ? "Both rated equally" : <>Ratings favour <span className={pref.preferred === "mit" ? "text-mit-400" : "text-student-400"}>{pref.preferred === "mit" ? "MIT" : "student"}</span> cards</>}
              </p>
              <p className="mt-1 text-sm text-white/70">Difference in mean score: <b>{pref.difference > 0 ? "+" : ""}{fmt(pref.difference, 2)}</b> (MIT − student)</p>
            </>
          ) : <p className="mt-3 text-sm text-white/70">Rate cards from both categories to compare them.</p>}
          {data.test && (
            <div className="mt-4 rounded-2xl bg-white/10 p-3 text-sm">
              <p className="flex items-center gap-1.5 font-semibold"><Scale className="size-4" /> Mann–Whitney U test</p>
              <p className="mt-1 text-white/80">U = {data.test.u}, z = {data.test.z}, p = {data.test.p_value} · r = {data.test.effect_size_r}</p>
              <p className={cn("mt-1 text-xs font-bold", pref?.significant ? "text-emerald-300" : "text-amber-200")}>
                {pref?.significant ? "Statistically significant at α = 0.05" : "Not statistically significant (yet)"}
              </p>
            </div>
          )}
          <p className="mt-3 text-[11px] text-white/50">Score = 6 − level (1 Excellent → 5 points … 5 Unacceptable → 1 point).</p>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Rating distribution</CardTitle><CardDescription>Share of ratings at each level (%)</CardDescription></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer>
              <BarChart data={dist}>
                <CartesianGrid vertical={false} stroke="#F1EBE2" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis tickLine={false} axisLine={false} fontSize={11} width={30} unit="%" />
                <Tooltip contentStyle={tip} cursor={{ fill: "rgba(0,0,0,.03)" }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="MIT" fill={MIT} radius={[8, 8, 0, 0]} />
                <Bar dataKey="Student" fill={STU} radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Quality criteria</CardTitle><CardDescription>Mean score per independently rated criterion</CardDescription></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer>
              <RadarChart data={radar} outerRadius="72%">
                <PolarGrid stroke="#ECE4D9" />
                <PolarAngleAxis dataKey="criterion" fontSize={10} />
                <PolarRadiusAxis domain={[0, 5]} tickCount={6} fontSize={9} />
                <Radar name="MIT" dataKey="MIT" stroke={MIT} fill={MIT} fillOpacity={0.25} />
                <Radar name="Student" dataKey="Student" stroke={STU} fill={STU} fillOpacity={0.25} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Tooltip contentStyle={tip} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader><CardTitle>Criteria table</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead><tr className="text-left text-xs uppercase tracking-wider text-ink-muted"><th className="py-2">Criterion</th><th>MIT</th><th>Student</th><th>Δ (MIT − student)</th></tr></thead>
            <tbody>
              {data.criteria.map((c: any) => {
                const d = c.mit != null && c.student != null ? c.mit - c.student : null;
                return (
                  <tr key={c.key} className="border-t border-line">
                    <td className="py-2.5 font-semibold">{c.label}</td>
                    <td><ScoreCell v={c.mit} n={c.mit_n} /></td>
                    <td><ScoreCell v={c.student} n={c.student_n} /></td>
                    <td className={cn("font-bold", d == null ? "text-ink-muted" : d > 0 ? "text-mit-600" : d < 0 ? "text-student-600" : "")}>{d == null ? "–" : `${d > 0 ? "+" : ""}${fmt(d, 2)}`}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <section className="grid gap-4 lg:grid-cols-3">
        <GroupChart title="By card type" rows={types} />
        <GroupChart title="By subject" rows={data.by_subject.map((r: any) => ({ ...r, label: SUBJECT_STYLE[r.key]?.short ?? r.key }))} />
        <GroupChart title="By generator" rows={data.by_generator.map((r: any) => ({ ...r, label: r.key === "rules" ? "Rule-based" : r.key === "ai" ? "AI" : r.key }))} />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <Card>
          <CardHeader><CardTitle>By source</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {data.by_source.map((r: any) => (
              <div key={r.source} className="flex items-center gap-3">
                <span className={cn("size-2.5 shrink-0 rounded-full", r.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
                <span className="min-w-0 flex-1 truncate text-sm font-medium">{r.source}</span>
                <div className="h-2 w-24 overflow-hidden rounded-full bg-black/5"><div className={cn("h-full", r.category === "mit" ? "bg-mit-500" : "bg-student-500")} style={{ width: `${((r.mean ?? 0) / 5) * 100}%` }} /></div>
                <span className="w-16 text-right text-sm font-bold">{fmt(r.mean, 2)} <span className="text-xs font-medium text-ink-muted">({r.n})</span></span>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Ratings over time</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer>
              <AreaChart data={data.timeline}>
                <CartesianGrid vertical={false} stroke="#F1EBE2" />
                <XAxis dataKey="date" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis tickLine={false} axisLine={false} fontSize={11} width={30} allowDecimals={false} />
                <Tooltip contentStyle={tip} />
                <Area type="monotone" dataKey="mit" name="MIT" stackId="1" stroke={MIT} fill={MIT} fillOpacity={0.35} />
                <Area type="monotone" dataKey="student" name="Student" stackId="1" stroke={STU} fill={STU} fillOpacity={0.35} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-2">
          <div><CardTitle>Per-document results</CardTitle><CardDescription>How each lecture document's flashcards were rated</CardDescription></div>
          <Select value={docCat} onChange={(e) => setDocCat(e.target.value)} aria-label="Category">
            <option value="">MIT + student</option><option value="mit">MIT only</option><option value="student">Student only</option>
          </Select>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-ink-muted">
                <th className="py-2">Document</th><th>Mean</th><th>Ratings</th>
                {data.criteria.map((c: any) => <th key={c.key} title={c.label} className="px-1 text-center">{c.label.split(" ")[0].slice(0, 8)}</th>)}
              </tr>
            </thead>
            <tbody>
              {docs.map((d: any) => (
                <tr key={d.id} className="border-t border-line">
                  <td className="max-w-[280px] py-2.5">
                    <Link href={`/notes/${d.id}`} className="flex items-center gap-2 font-semibold hover:underline">
                      <span className={cn("size-2.5 shrink-0 rounded-full", d.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
                      <span className="truncate">{d.title}</span>
                    </Link>
                    <span className="block truncate pl-[18px] text-xs text-ink-muted">{d.source}</span>
                  </td>
                  <td><ScoreCell v={d.mean} /></td>
                  <td className="text-ink-muted">{d.n}</td>
                  {data.criteria.map((c: any) => <td key={c.key} className="px-1 text-center"><Heat v={d.criteria[c.key]} /></td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {data.comments.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Recent comments</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {data.comments.map((c: any) => (
              <div key={c.id} className="rounded-2xl border border-line p-3">
                <div className="flex items-center gap-2">
                  <span className={cn("grid size-6 place-items-center rounded-lg text-xs font-bold text-white", RATING_STYLE[c.overall].bg)}>{c.overall}</span>
                  <span className={cn("chip", CATEGORY_STYLE[c.category as "mit" | "student"].chip)}>{c.category === "mit" ? "MIT" : "Student"}</span>
                  <span className="ml-auto text-xs text-ink-muted">{c.evaluator}</span>
                </div>
                <p className="mt-2 text-sm">“{c.comment}”</p>
                <p className="mt-1 line-clamp-1 text-xs text-ink-muted">on: <Inline text={c.question} /></p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl bg-white/80 p-2"><p className="font-display text-lg font-semibold">{value}</p><p className="text-[10px] font-bold uppercase text-ink-muted">{label}</p></div>;
}

function ScoreCell({ v, n }: { v: number | null; n?: number }) {
  if (v == null) return <span className="text-ink-muted">–</span>;
  return <span className="font-bold">{fmt(v, 2)}{n != null && <span className="ml-1 text-xs font-medium text-ink-muted">({n})</span>}</span>;
}

function Heat({ v }: { v: number | null }) {
  if (v == null) return <span className="text-ink-muted">·</span>;
  const lvl = Math.min(5, Math.max(1, Math.round(6 - v)));
  return <span className={cn("inline-block min-w-10 rounded-lg px-1.5 py-0.5 text-xs font-bold text-white", RATING_STYLE[lvl].bg)}>{fmt(v, 1)}</span>;
}

function GroupChart({ title, rows }: { title: string; rows: any[] }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="h-60">
        <ResponsiveContainer>
          <BarChart data={rows}>
            <CartesianGrid vertical={false} stroke="#F1EBE2" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={10} interval={0} />
            <YAxis domain={[0, 5]} tickLine={false} axisLine={false} fontSize={10} width={24} />
            <Tooltip contentStyle={tip} cursor={{ fill: "rgba(0,0,0,.03)" }} />
            <Bar dataKey="mit" name="MIT" fill={MIT} radius={[6, 6, 0, 0]} />
            <Bar dataKey="student" name="Student" fill={STU} radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
