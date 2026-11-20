"use client";
import katex from "katex";
import * as React from "react";
import { cn } from "@/lib/utils";

const MATH_RE = /\$\$[\s\S]+?\$\$|\$[^$\n]+?\$/g;
const cache = new Map<string, string>();

function renderMath(tex: string, display: boolean, macros?: Record<string, string>) {
  const key = `${display ? "D" : "I"}|${tex}|${macros ? Object.keys(macros).length : 0}`;
  const hit = cache.get(key);
  if (hit) return hit;
  let html: string;
  try {
    html = katex.renderToString(tex, {
      displayMode: display,
      throwOnError: false,
      strict: "ignore",
      trust: false,
      macros: macros ? { ...macros } : undefined,
      output: "html",
    });
  } catch {
    html = `<code>${tex.replace(/</g, "&lt;")}</code>`;
  }
  if (cache.size > 5000) cache.clear();
  cache.set(key, html);
  return html;
}

function renderBold(text: string, keyBase: string) {
  const parts = text.split(/\*\*([^*\n]+)\*\*/g);
  return parts.map((p, i) =>
    i % 2 === 1 ? (
      <strong key={`${keyBase}-b${i}`} className="font-semibold text-ink">
        {p}
      </strong>
    ) : (
      <React.Fragment key={`${keyBase}-t${i}`}>{p.replace(/\*\*/g, "")}</React.Fragment>
    ),
  );
}

/** Render a short string with $maths$ and **bold**. */
export function Inline({ text, macros, className }: { text: string; macros?: Record<string, string>; className?: string }) {
  return <span className={className}>{inlineNodes(text, macros, "i")}</span>;
}

function inlineNodes(text: string, macros: Record<string, string> | undefined, keyBase: string) {
  const out: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  const re = new RegExp(MATH_RE.source, "g");
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(...renderBold(text.slice(last, m.index), `${keyBase}-${i}`));
    const raw = m[0];
    const display = raw.startsWith("$$");
    const tex = display ? raw.slice(2, -2) : raw.slice(1, -1);
    out.push(
      <span
        key={`${keyBase}-m${i}`}
        className={display ? "block" : undefined}
        dangerouslySetInnerHTML={{ __html: renderMath(tex, display, macros) }}
      />,
    );
    last = m.index + raw.length;
    i++;
  }
  if (last < text.length) out.push(...renderBold(text.slice(last), `${keyBase}-e`));
  return out;
}

/** Push highlight boundaries out of maths spans so formulas are never cut. */
function safeRange(text: string, a: number, b: number): [number, number] {
  const re = new RegExp(MATH_RE.source, "g");
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const s = m.index, e = m.index + m[0].length;
    if (a > s && a < e) a = s;
    if (b > s && b < e) b = e;
  }
  return [a, b];
}

function withHighlight(text: string, offset: number, hl: [number, number] | null, macros: Record<string, string> | undefined, key: string, markRef?: React.Ref<HTMLElement>) {
  if (!hl) return inlineNodes(text, macros, key);
  const a = Math.max(0, hl[0] - offset), b = Math.min(text.length, hl[1] - offset);
  if (b <= 0 || a >= text.length || a >= b) return inlineNodes(text, macros, key);
  return [
    ...inlineNodes(text.slice(0, a), macros, `${key}-pre`),
    <mark key={`${key}-hl`} ref={markRef as React.Ref<HTMLElement>} className="note-highlight">
      {inlineNodes(text.slice(a, b), macros, `${key}-mid`)}
    </mark>,
    ...inlineNodes(text.slice(b), macros, `${key}-post`),
  ];
}

/**
 * Render lecture-note text: paragraphs, bullet lists, maths and bold, optionally
 * highlighting the character range [highlight[0], highlight[1]).
 */
export function NoteText({
  text,
  macros,
  highlight,
  className,
  markRef,
}: {
  text: string;
  macros?: Record<string, string>;
  highlight?: [number, number] | null;
  className?: string;
  markRef?: React.Ref<HTMLElement>;
}) {
  const hl = React.useMemo(() => (highlight ? safeRange(text, highlight[0], highlight[1]) : null), [text, highlight]);
  let firstMarkUsed = false;
  const blocks: React.ReactNode[] = [];
  const paraRe = /(?:(?!\n\s*\n)[\s\S])+/g;
  let pm: RegExpExecArray | null;
  let pi = 0;
  while ((pm = paraRe.exec(text))) {
    const pStart = pm.index;
    const para = pm[0];
    const lines: { text: string; start: number; bullet: boolean }[] = [];
    let pos = 0;
    for (const line of para.split("\n")) {
      const lead = line.length - line.trimStart().length;
      const t = line.trim();
      if (t) {
        const bullet = t.startsWith("• ");
        lines.push({ text: bullet ? t.slice(2) : t, start: pStart + pos + lead + (bullet ? 2 : 0), bullet });
      }
      pos += line.length + 1;
    }
    // merge soft-wrapped non-bullet lines into one run (keeping offsets roughly right)
    const groups: { bullet: boolean; items: { text: string; start: number }[] }[] = [];
    for (const l of lines) {
      const g = groups[groups.length - 1];
      if (l.bullet) {
        if (g && g.bullet) g.items.push(l);
        else groups.push({ bullet: true, items: [l] });
      } else if (g && !g.bullet) {
        g.items.push(l);
      } else groups.push({ bullet: false, items: [l] });
    }
    groups.forEach((g, gi) => {
      const key = `p${pi}-${gi}`;
      const ref = (start: number, len: number) => {
        if (!hl || firstMarkUsed) return undefined;
        if (hl[0] < start + len && hl[1] > start) {
          firstMarkUsed = true;
          return markRef;
        }
        return undefined;
      };
      if (g.bullet) {
        blocks.push(
          <ul key={key} className="my-2 space-y-1.5 pl-1">
            {g.items.map((it, ii) => (
              <li key={ii} className="flex gap-2.5">
                <span className="mt-[11px] size-1.5 shrink-0 rounded-full bg-cs-500/60" />
                <span className="min-w-0">{withHighlight(it.text, it.start, hl, macros, `${key}-${ii}`, ref(it.start, it.text.length))}</span>
              </li>
            ))}
          </ul>,
        );
      } else {
        blocks.push(
          <p key={key} className="my-2.5 [overflow-wrap:anywhere]">
            {g.items.map((it, ii) => (
              <React.Fragment key={ii}>
                {ii > 0 && " "}
                {withHighlight(it.text, it.start, hl, macros, `${key}-${ii}`, ref(it.start, it.text.length))}
              </React.Fragment>
            ))}
          </p>,
        );
      }
    });
    pi++;
  }
  return <div className={cn("prose-notes", className)}>{blocks}</div>;
}
