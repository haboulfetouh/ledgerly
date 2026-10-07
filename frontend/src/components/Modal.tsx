import * as Dialog from "@radix-ui/react-dialog";
import clsx from "clsx";
import type { PropsWithChildren } from "react";

export function Modal({
  open,
  onOpenChange,
  title,
  maxWidthClassName = "max-w-lg",
  children,
}: PropsWithChildren<{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  maxWidthClassName?: string;
}>) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-[2px]" />
        <Dialog.Content
          className={clsx(
            "fixed left-1/2 top-1/2 w-full -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-surface-border bg-surface-raised p-6 shadow-raised",
            maxWidthClassName,
          )}
        >
          <div className="flex items-center justify-between">
            <Dialog.Title className="text-lg font-semibold text-slate-900">{title}</Dialog.Title>
            <Dialog.Close className="text-slate-400 hover:text-slate-600">✕</Dialog.Close>
          </div>
          <div className="mt-4">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
