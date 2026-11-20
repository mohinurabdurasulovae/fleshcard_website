import { GraduationCap, Users } from "lucide-react";
import { CATEGORY_STYLE, SUBJECT_STYLE, TYPE_STYLE, cn, type Category } from "@/lib/utils";

export function CategoryBadge({ category, className, short }: { category: Category; className?: string; short?: boolean }) {
  const s = CATEGORY_STYLE[category] ?? CATEGORY_STYLE.student;
  const Icon = category === "mit" ? GraduationCap : Users;
  return (
    <span className={cn("chip", s.chip, className)}>
      <Icon className="size-3.5" />
      {short ? (category === "mit" ? "MIT" : "Student") : s.label}
    </span>
  );
}

export function SubjectBadge({ subject, className }: { subject: string; className?: string }) {
  const s = SUBJECT_STYLE[subject];
  return (
    <span className={cn("chip", s?.chip ?? "bg-black/5 text-ink-soft", className)}>
      <span aria-hidden>{s?.emoji}</span>
      {subject}
    </span>
  );
}

export function TypeBadge({ type, className }: { type: string; className?: string }) {
  const s = TYPE_STYLE[type];
  return <span className={cn("chip", s?.chip ?? "bg-black/5", className)}>{s?.label ?? type}</span>;
}

export function FormatBadge({ format }: { format: string }) {
  const map: Record<string, string> = { pdf: "bg-rose-50 text-rose-700", html: "bg-sky-50 text-sky-700", md: "bg-emerald-50 text-emerald-700", tex: "bg-amber-50 text-amber-800" };
  return <span className={cn("chip uppercase tracking-wide", map[format] ?? "bg-black/5")}>{format === "tex" ? "LaTeX" : format}</span>;
}
