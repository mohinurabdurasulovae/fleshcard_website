"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";
import {
  BarChart3, BookOpenText, Compass, Database, Layers, LayoutDashboard, Menu, Network, Search, Sparkles, Star, X,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { CategoryBadge } from "./badges";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, color: "from-cs-500 to-student-500" },
  { href: "/courses", label: "Explore Courses", icon: Compass, color: "from-student-500 to-sky-400" },
  { href: "/notes", label: "Lecture Notes", icon: BookOpenText, color: "from-phys-500 to-orange-400" },
  { href: "/topics", label: "Topic Explorer", icon: Network, color: "from-bio-500 to-teal-400" },
  { href: "/flashcards", label: "Flashcards", icon: Layers, color: "from-pink-500 to-mit-500" },
  { href: "/evaluate", label: "Evaluation", icon: Star, color: "from-amber-400 to-phys-500" },
  { href: "/statistics", label: "Statistics", icon: BarChart3, color: "from-violet-500 to-fuchsia-500" },
  { href: "/admin", label: "Data Collection", icon: Database, color: "from-slate-600 to-slate-400" },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const path = usePathname();
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map(({ href, label, icon: Icon, color }) => {
        const active = href === "/" ? path === "/" : path.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "focus-ring group flex items-center gap-3 rounded-2xl px-2.5 py-2 text-sm font-semibold transition-all",
              active ? "bg-white text-ink shadow-soft" : "text-ink-soft hover:bg-white/60 hover:text-ink",
            )}
          >
            <span className={cn("grid size-8 place-items-center rounded-xl bg-gradient-to-br text-white shadow-sm transition-transform group-hover:scale-105", color, !active && "opacity-80")}>
              <Icon className="size-4" />
            </span>
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 px-1">
      <span className="relative grid size-10 place-items-center rounded-2xl bg-ink text-white shadow-lift">
        <Sparkles className="size-5" />
        <span className="absolute -right-1 -top-1 size-3 rounded-full bg-mit-500 ring-2 ring-canvas" />
        <span className="absolute -bottom-1 -left-1 size-3 rounded-full bg-student-500 ring-2 ring-canvas" />
      </span>
      <span className="leading-tight">
        <span className="block font-display text-[17px] font-semibold tracking-tight">NoteCards</span>
        <span className="block text-[11px] font-medium text-ink-muted">Lecture notes → flashcards</span>
      </span>
    </Link>
  );
}

function GlobalSearch() {
  const [q, setQ] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [open, setOpen] = React.useState(false);
  const router = useRouter();
  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);
  const { data } = useApi<any>(debounced.length >= 2 ? `/api/search?q=${encodeURIComponent(debounced)}&limit=6` : null);
  const close = () => { setOpen(false); setQ(""); };
  return (
    <div className="relative w-full max-w-md">
      <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-ink-muted" />
      <input
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 180)}
        onKeyDown={(e) => { if (e.key === "Enter" && q.trim()) { router.push(`/notes?q=${encodeURIComponent(q.trim())}`); close(); } }}
        placeholder="Search notes, courses, topics…"
        className="focus-ring h-11 w-full rounded-2xl border border-line bg-white/90 pl-10 pr-4 text-sm shadow-soft placeholder:text-ink-muted/70"
      />
      {open && data && debounced.length >= 2 && (
        <div className="absolute left-0 right-0 top-12 z-40 max-h-[70vh] overflow-y-auto rounded-3xl border border-line bg-white p-2 shadow-lift">
          {data.topics.length > 0 && (
            <Group title="Topics">
              {data.topics.map((t: any) => (
                <Link key={t.id} href={`/topics/${t.slug}`} onClick={close} className="block rounded-xl px-3 py-2 text-sm hover:bg-canvas">
                  {t.name} <span className="text-ink-muted">· {t.subject}</span>
                </Link>
              ))}
            </Group>
          )}
          {data.courses.length > 0 && (
            <Group title="Courses">
              {data.courses.map((c: any) => (
                <Link key={c.id} href={`/courses/${c.id}`} onClick={close} className="flex items-center justify-between gap-2 rounded-xl px-3 py-2 text-sm hover:bg-canvas">
                  <span className="truncate"><b>{c.code}</b> {c.title}</span>
                  <CategoryBadge category={c.category} short />
                </Link>
              ))}
            </Group>
          )}
          {data.documents.length > 0 && (
            <Group title="Documents">
              {data.documents.map((d: any) => (
                <Link key={d.id} href={`/notes/${d.id}?q=${encodeURIComponent(debounced)}`} onClick={close} className="block rounded-xl px-3 py-2 text-sm hover:bg-canvas">
                  <span className="flex items-center justify-between gap-2"><span className="truncate font-semibold">{d.title}</span><CategoryBadge category={d.category} short /></span>
                  {d.snippet && <span className="mt-0.5 line-clamp-2 block text-xs text-ink-muted">{d.snippet}</span>}
                </Link>
              ))}
            </Group>
          )}
          {!data.topics.length && !data.courses.length && !data.documents.length && (
            <p className="px-3 py-6 text-center text-sm text-ink-muted">No results for “{debounced}”</p>
          )}
        </div>
      )}
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-1">
      <p className="px-3 pb-1 pt-2 text-[11px] font-bold uppercase tracking-wider text-ink-muted">{title}</p>
      {children}
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [menu, setMenu] = React.useState(false);
  return (
    <div className="bg-blobs min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col gap-6 border-r border-line/70 bg-canvas/70 p-4 backdrop-blur-xl lg:flex">
        <Logo />
        <NavLinks />
        <div className="mt-auto rounded-3xl bg-gradient-to-br from-ink to-ink-soft p-4 text-white shadow-lift">
          <p className="text-xs font-semibold uppercase tracking-wider text-white/60">Two kinds of notes</p>
          <div className="mt-3 space-y-2 text-sm">
            <p className="flex items-center gap-2"><span className="size-2.5 rounded-full bg-mit-500" /> MIT OpenCourseWare</p>
            <p className="flex items-center gap-2"><span className="size-2.5 rounded-full bg-student-500" /> Student-created notes</p>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-line/60 bg-canvas/75 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 sm:px-6">
            <button onClick={() => setMenu(true)} className="focus-ring grid size-11 shrink-0 place-items-center rounded-2xl border border-line bg-white lg:hidden" aria-label="Open menu">
              <Menu className="size-5" />
            </button>
            <div className="lg:hidden"><span className="font-display text-lg font-semibold">NoteCards</span></div>
            <div className="ml-auto flex w-full justify-end lg:ml-0 lg:justify-start">
              <div className="hidden w-full sm:block"><GlobalSearch /></div>
            </div>
          </div>
          <div className="px-4 pb-3 sm:hidden"><GlobalSearch /></div>
        </header>
        <main className="mx-auto max-w-7xl px-4 pb-20 pt-6 sm:px-6">{children}</main>
      </div>

      <Dialog open={menu} onOpenChange={setMenu}>
        <DialogContent side="left" className="flex flex-col gap-6">
          <DialogTitle className="sr-only">Navigation</DialogTitle>
          <div className="flex items-center justify-between"><Logo /><button onClick={() => setMenu(false)} className="sr-only"><X /></button></div>
          <NavLinks onNavigate={() => setMenu(false)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function PageHeader({ title, subtitle, eyebrow, actions, accent = "from-cs-500 to-student-500" }: {
  title: string; subtitle?: React.ReactNode; eyebrow?: string; actions?: React.ReactNode; accent?: string;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 animate-fade-up sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && (
          <p className={cn("mb-1 inline-block bg-gradient-to-r bg-clip-text text-xs font-bold uppercase tracking-[.16em] text-transparent", accent)}>{eyebrow}</p>
        )}
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-1.5 max-w-2xl text-[15px] text-ink-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
