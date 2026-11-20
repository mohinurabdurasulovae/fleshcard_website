import Link from "next/link";
import { FileText, Layers } from "lucide-react";
import type { DocBrief } from "@/lib/api";
import { CATEGORY_STYLE, SUBJECT_STYLE, cn, compact } from "@/lib/utils";
import { CategoryBadge, FormatBadge } from "./badges";

export function DocCard({ doc, className, extra }: { doc: DocBrief; className?: string; extra?: React.ReactNode }) {
  const subj = SUBJECT_STYLE[doc.subject];
  const cat = CATEGORY_STYLE[doc.category];
  return (
    <Link
      href={`/notes/${doc.id}`}
      className={cn("card-surface focus-ring group relative flex flex-col overflow-hidden p-5 transition-all hover:-translate-y-0.5 hover:shadow-lift", className)}
    >
      <span className={cn("absolute inset-x-0 top-0 h-1", doc.category === "mit" ? "bg-mit-500" : "bg-student-500")} />
      <div className="flex items-start justify-between gap-3">
        <span className={cn("grid size-11 shrink-0 place-items-center rounded-2xl text-xl", subj?.soft)}>{subj?.emoji ?? <FileText />}</span>
        <div className="flex flex-wrap justify-end gap-1.5">
          <CategoryBadge category={doc.category} short />
          <FormatBadge format={doc.format} />
        </div>
      </div>
      <h3 className="mt-3 line-clamp-2 font-display text-[17px] font-semibold leading-snug group-hover:text-ink">{doc.title}</h3>
      <p className="mt-0.5 truncate text-xs font-medium text-ink-muted">
        {doc.course ? `${doc.course.code}${doc.course.university ? " · " + doc.course.university : ""}` : doc.source?.name}
      </p>
      {doc.snippet ? (
        <p className="mt-2 line-clamp-3 text-sm text-ink-soft">{doc.snippet}</p>
      ) : (
        doc.summary && <p className="mt-2 line-clamp-2 text-sm text-ink-muted">{doc.summary.replace(/\*\*|\$/g, "")}</p>
      )}
      {doc.topics.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {doc.topics.slice(0, 3).map((t) => (
            <span key={t.id} className={cn("chip", subj?.chip)}>{t.name}</span>
          ))}
        </div>
      )}
      <div className="mt-auto flex items-center gap-4 pt-4 text-xs font-semibold text-ink-muted">
        <span>{compact(doc.word_count)} words</span>
        {doc.page_count > 0 && <span>{doc.page_count} pages</span>}
        {doc.flashcard_count != null && (
          <span className={cn("ml-auto flex items-center gap-1", cat.text)}><Layers className="size-3.5" />{doc.flashcard_count}</span>
        )}
      </div>
      {extra}
    </Link>
  );
}
