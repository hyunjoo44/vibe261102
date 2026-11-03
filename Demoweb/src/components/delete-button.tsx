"use client";

import { useTransition } from "react";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = {
  onDelete: () => Promise<void>;
  confirmMessage: string;
  label?: string;
};

export function DeleteButton({ onDelete, confirmMessage, label }: Props) {
  const [pending, startTransition] = useTransition();

  return (
    <Button
      variant="destructive"
      size={label ? "default" : "icon-xs"}
      disabled={pending}
      aria-label={label ?? "삭제"}
      onClick={() => {
        if (confirm(confirmMessage)) startTransition(() => onDelete());
      }}
    >
      <Trash2 />
      {label}
    </Button>
  );
}
