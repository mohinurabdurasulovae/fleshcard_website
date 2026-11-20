import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const SUBJECTS = ["Computer Science", "Physics", "Biology"] as const;
export type Subject = (typeof SUBJECTS)[number];
export type Category = "mit" | "student";

export const SUBJECT_STYLE: Record<string, { chip: string; dot: string; soft: string; text: string; hex: string; emoji: string; short: string }> = {
  "Computer Science": { chip: "bg-cs-100 text-cs-700", dot: "bg-cs-500", soft: "bg-cs-50", text: "text-cs-600", hex: "#8B5CF6", emoji: "💻", short: "CS" },
  Physics: { chip: "bg-phys-100 text-phys-700", dot: "bg-phys-500", soft: "bg-phys-50", text: "text-phys-600", hex: "#F59E0B", emoji: "🪐", short: "Physics" },
  Biology: { chip: "bg-bio-100 text-bio-700", dot: "bg-bio-500", soft: "bg-bio-50", text: "text-bio-600", hex: "#10B981", emoji: "🧬", short: "Bio" },
};

export const CATEGORY_STYLE: Record<Category, { label: string; chip: string; solid: string; soft: string; text: string; ring: string; hex: string; border: string }> = {
  mit: { label: "MIT OCW", chip: "bg-mit-100 text-mit-700", solid: "bg-mit-500 text-white", soft: "bg-mit-50", text: "text-mit-600", ring: "ring-mit-200", hex: "#E5484D", border: "border-mit-200" },
  student: { label: "Student notes", chip: "bg-student-100 text-student-700", solid: "bg-student-500 text-white", soft: "bg-student-50", text: "text-student-600", ring: "ring-student-200", hex: "#2F7CF6", border: "border-student-200" },
};

export const TYPE_STYLE: Record<string, { label: string; chip: string; hex: string }> = {
  definition: { label: "Definition", chip: "bg-violet-100 text-violet-700", hex: "#8B5CF6" },
  concept: { label: "Conceptual", chip: "bg-sky-100 text-sky-700", hex: "#0EA5E9" },
  explanation: { label: "Explanation", chip: "bg-amber-100 text-amber-800", hex: "#F59E0B" },
  formula: { label: "Formula", chip: "bg-pink-100 text-pink-700", hex: "#EC4899" },
  comparison: { label: "Comparison", chip: "bg-teal-100 text-teal-700", hex: "#14B8A6" },
};

export const RATING_STYLE: Record<number, { label: string; bg: string; text: string; hex: string; emoji: string }> = {
  1: { label: "Excellent", bg: "bg-emerald-500", text: "text-emerald-700", hex: "#10B981", emoji: "🤩" },
  2: { label: "Very Good", bg: "bg-lime-500", text: "text-lime-700", hex: "#84CC16", emoji: "😊" },
  3: { label: "Acceptable", bg: "bg-amber-400", text: "text-amber-700", hex: "#FBBF24", emoji: "🙂" },
  4: { label: "Poor", bg: "bg-orange-500", text: "text-orange-700", hex: "#F97316", emoji: "😕" },
  5: { label: "Unacceptable", bg: "bg-rose-500", text: "text-rose-700", hex: "#F43F5E", emoji: "😣" },
};

export function fmt(n: number | null | undefined, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function compact(n: number) {
  return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export function timeAgo(iso?: string | null) {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const u = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== false) u.set(k, String(v));
  });
  const s = u.toString();
  return s ? `?${s}` : "";
}
