import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn("focus-ring h-10 w-full rounded-2xl border border-line bg-white px-3.5 text-sm placeholder:text-ink-muted/70", className)}
    {...props}
  />
));
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn("focus-ring min-h-[90px] w-full rounded-2xl border border-line bg-white px-3.5 py-2.5 text-sm placeholder:text-ink-muted/70", className)}
    {...props}
  />
));
Textarea.displayName = "Textarea";

const CHEVRON =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%237A716A' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")";

export function Select({ className, children, style, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn("focus-ring h-10 appearance-none rounded-2xl border border-line bg-white pl-3.5 pr-9 text-sm", className)}
      style={{ backgroundImage: CHEVRON, backgroundSize: 16, backgroundPosition: "right .7rem center", backgroundRepeat: "no-repeat", ...style }}
      {...props}
    >
      {children}
    </select>
  );
}

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("text-xs font-semibold uppercase tracking-wide text-ink-muted", className)} {...props} />;
}
