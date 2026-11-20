"use client";
import Link from "next/link";
import * as React from "react";
import { BookOpenText, ExternalLink, MapPin, RotateCw } from "lucide-react";
import type { Flashcard } from "@/lib/api";
import { CATEGORY_STYLE, cn } from "@/lib/utils";
import { CategoryBadge, SubjectBadge, TypeBadge } from "./badges";
import { Inline, NoteText } from "./rich-text";
import { Button } from "./ui/button";

export function SourceLine({ card, compact }: { card: Flashcard; compact?: boolean }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-muted", compact && "text-[11px]")}>
      <MapPin className="size-3.5 shrink-0" />
      <span className="font-semibold text-ink-soft">{card.document.source}</span>
      <span>·</span>
      <span className="truncate">{card.document.title}</span>
      {card.section_title && (<><span>·</span><span className="truncate">§ {card.section_title.replace(/^Page \d+ · /, "")}</span></>)}
      {card.page && (<><span>·</span><span>p. {card.page}</span></>)}
    </div>
  );
}

export function FlashcardView({
  card, flipped, onFlip, className, actions,
}: {
  card: Flashcard; flipped: boolean; onFlip: () => void; className?: string; actions?: React.ReactNode;
}) {
  const cat = CATEGORY_STYLE[card.category];
  const macros = card.document.katex_macros;
  return (
    <div className={cn("flip-scene", className)}>
      <div className={cn("flip-card relative grid min-h-[340px]", flipped && "is-flipped")}>
        {/* front */}
        <div
          role="button"
          tabIndex={0}
          onClick={onFlip}
          onKeyDown={(e) => (e.key === " " || e.key === "Enter") && (e.preventDefault(), onFlip())}
          className={cn("flip-face focus-ring col-start-1 row-start-1 flex cursor-pointer flex-col rounded-4xl border-2 bg-white p-6 shadow-lift sm:p-8", cat.border)}
        >
          <div className="flex flex-wrap items-center gap-2">
            <CategoryBadge category={card.category} />
            <TypeBadge type={card.card_type} />
            <SubjectBadge subject={card.subject} />
          </div>
          <div className="flex flex-1 items-center justify-center py-8">
            <p className="text-center font-display text-xl font-medium leading-snug text-ink sm:text-2xl">
              <Inline text={card.question} macros={macros} />
            </p>
          </div>
          <div className="flex items-center justify-between gap-3">
            <SourceLine card={card} compact />
            <span className="hidden shrink-0 items-center gap-1 text-xs font-semibold text-ink-muted sm:flex"><RotateCw className="size-3.5" />Tap to flip</span>
          </div>
        </div>
        {/* back */}
        <div className={cn("flip-face flip-back col-start-1 row-start-1 flex flex-col rounded-4xl border-2 p-6 shadow-lift sm:p-8", cat.border, cat.soft)}>
          <div className="flex items-center justify-between gap-2">
            <span className={cn("text-xs font-bold uppercase tracking-wider", cat.text)}>Answer</span>
            <button onClick={onFlip} className="focus-ring flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold text-ink-muted hover:bg-white"><RotateCw className="size-3.5" />Question</button>
          </div>
          <div className="scrollbar-thin mt-2 max-h-[260px] flex-1 overflow-y-auto pr-1">
            <NoteText text={card.answer} macros={macros} className="text-base text-ink" />
          </div>
          <div className="mt-3 space-y-3 border-t border-black/5 pt-3">
            <SourceLine card={card} />
            <div className="flex flex-wrap gap-2">
              <Button asChild size="sm" variant={card.category === "mit" ? "mit" : "student"}>
                <Link href={`/notes/${card.document_id}?card=${card.id}`} onClick={(e) => e.stopPropagation()}>
                  <BookOpenText /> Find it in the notes
                </Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <a href={card.document.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}><ExternalLink /> Original source</a>
              </Button>
              {actions}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
