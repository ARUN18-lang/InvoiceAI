import type { InputHTMLAttributes } from "react";

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-full border border-line-strong bg-raised px-4 py-2.5 text-sm text-neutral-100 placeholder:text-muted-dim outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/30 ${className}`}
      {...props}
    />
  );
}
