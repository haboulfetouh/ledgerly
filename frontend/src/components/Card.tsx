import clsx from "clsx";
import type { PropsWithChildren } from "react";

export function Card({ children, className }: PropsWithChildren<{ className?: string }>) {
  return (
    <div
      className={clsx(
        "rounded-2xl border border-surface-border bg-surface-raised p-6 shadow-card",
        className,
      )}
    >
      {children}
    </div>
  );
}
