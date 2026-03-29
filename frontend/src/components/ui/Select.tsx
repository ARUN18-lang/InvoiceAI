import type { SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";

export function Select({
  className = "",
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative">
      <select
        className={`w-full cursor-pointer appearance-none rounded-full border border-line-strong bg-[#1a1a1a] py-2.5 pl-4 pr-10 text-sm font-medium text-neutral-100 outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/30 ${className}`}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400"
        aria-hidden
      />
    </div>
  );
}
