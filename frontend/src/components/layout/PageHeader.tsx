import type { ReactNode } from "react";
import { FolderOpen } from "lucide-react";

export function PageHeader({
  breadcrumb = "Home",
  title,
  subtitle,
  action,
}: {
  breadcrumb?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <header className="border-b border-black bg-canvas/80 px-8 py-8 backdrop-blur-sm">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="mb-3 flex items-center gap-2 text-xs font-medium text-muted">
            <FolderOpen className="h-3.5 w-3.5" strokeWidth={2} />
            {breadcrumb}
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-white">{title}</h1>
          {subtitle ? <p className="mt-2 max-w-2xl text-sm text-muted">{subtitle}</p> : null}
        </div>
        {action ? <div className="shrink-0 text-neutral-100">{action}</div> : null}
      </div>
    </header>
  );
}
