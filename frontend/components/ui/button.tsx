import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "focus-ring inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-2xl text-sm font-semibold transition-all active:scale-[.98] disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-ink text-white shadow-soft hover:bg-ink/90",
        primary: "bg-gradient-to-r from-cs-500 to-student-500 text-white shadow-soft hover:brightness-110",
        mit: "bg-mit-500 text-white shadow-soft hover:bg-mit-600",
        student: "bg-student-500 text-white shadow-soft hover:bg-student-600",
        outline: "border border-line bg-white text-ink hover:bg-canvas",
        ghost: "text-ink-soft hover:bg-black/[.04] hover:text-ink",
        soft: "bg-black/[.04] text-ink hover:bg-black/[.07]",
        danger: "bg-rose-50 text-rose-700 hover:bg-rose-100",
      },
      size: { default: "h-10 px-4", sm: "h-8 rounded-xl px-3 text-xs", lg: "h-12 px-6 text-base", icon: "h-10 w-10" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
});
Button.displayName = "Button";
export { buttonVariants };
