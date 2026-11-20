"use client";
import { GraduationCap, LayoutGrid, Users } from "lucide-react";
import { SUBJECTS, SUBJECT_STYLE, cn } from "@/lib/utils";

export function SubjectPills({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      <Pill active={!value} onClick={() => onChange("")}>All subjects</Pill>
      {SUBJECTS.map((s) => (
        <Pill key={s} active={value === s} onClick={() => onChange(value === s ? "" : s)} activeClass={SUBJECT_STYLE[s].chip}>
          <span aria-hidden>{SUBJECT_STYLE[s].emoji}</span> {s}
        </Pill>
      ))}
    </div>
  );
}

export function CategoryToggle({ value, onChange, allowAll = true }: { value: string; onChange: (v: string) => void; allowAll?: boolean }) {
  const opts = [
    ...(allowAll ? [{ v: "", label: "All", icon: LayoutGrid, cls: "bg-white text-ink shadow-soft" }] : []),
    { v: "mit", label: "MIT OCW", icon: GraduationCap, cls: "bg-mit-500 text-white shadow-soft" },
    { v: "student", label: "Student", icon: Users, cls: "bg-student-500 text-white shadow-soft" },
  ];
  return (
    <div className="inline-flex rounded-2xl bg-black/[.05] p-1">
      {opts.map(({ v, label, icon: Icon, cls }) => (
        <button
          key={v || "all"}
          onClick={() => onChange(v)}
          className={cn("focus-ring flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-semibold transition-all", value === v ? cls : "text-ink-muted hover:text-ink")}
        >
          <Icon className="size-4" /> {label}
        </button>
      ))}
    </div>
  );
}

function Pill({ active, onClick, children, activeClass }: { active: boolean; onClick: () => void; children: React.ReactNode; activeClass?: string }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "focus-ring inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-semibold transition-all",
        active ? cn("border-transparent shadow-soft", activeClass ?? "bg-ink text-white") : "border-line bg-white text-ink-soft hover:border-ink/20",
      )}
    >
      {children}
    </button>
  );
}

export function Pager({ page, total, pageSize, onPage }: { page: number; total: number; pageSize: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="mt-6 flex items-center justify-center gap-2 text-sm">
      <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="focus-ring rounded-xl border border-line bg-white px-3 py-1.5 font-semibold disabled:opacity-40">Previous</button>
      <span className="px-2 font-semibold text-ink-muted">Page {page} of {pages}</span>
      <button disabled={page >= pages} onClick={() => onPage(page + 1)} className="focus-ring rounded-xl border border-line bg-white px-3 py-1.5 font-semibold disabled:opacity-40">Next</button>
    </div>
  );
}
