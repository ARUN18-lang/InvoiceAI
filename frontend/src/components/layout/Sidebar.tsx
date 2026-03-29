import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutGrid,
  FileText,
  MessageSquare,
  BarChart3,
  FolderOpen,
  ChevronDown,
  Sparkles,
  Plus,
} from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";

const linkBase =
  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-white/5 hover:text-white";
const linkActive = "bg-white/[0.06] text-white";

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="mb-2 mt-6 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted first:mt-0">
      {children}
    </p>
  );
}

export function Sidebar() {
  const { workspaces, current, selectWorkspace, createNew, loading, error } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, [open]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const n = newName.trim();
    if (!n || creating) return;
    setCreating(true);
    try {
      await createNew(n);
      setNewName("");
      setOpen(false);
    } catch {
      /* surfaced via workspace error if we plumb it */
    } finally {
      setCreating(false);
    }
  };

  const label = loading ? "Loading…" : current?.name ?? "Select workspace";

  return (
    <aside className="flex min-h-screen w-[260px] shrink-0 flex-col border-r border-black bg-surface">
      <div className="flex h-16 items-center px-5">
        <span className="text-lg font-semibold tracking-tight text-white">Smart Invoice</span>
      </div>

      <div className="relative px-4 pb-2" ref={wrapRef}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center gap-3 rounded-xl border border-line-strong bg-raised px-3 py-2.5 text-left text-sm text-neutral-100 transition-colors hover:border-accent/50"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
            <LayoutGrid className="h-4 w-4" strokeWidth={1.75} />
          </span>
          <span className="flex-1 truncate font-medium">{label}</span>
          <ChevronDown className={`h-4 w-4 shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`} />
        </button>

        {open ? (
          <div className="absolute left-4 right-4 top-full z-50 mt-1 rounded-xl border border-line-strong bg-[#141414] py-1 shadow-xl">
            <ul className="max-h-52 overflow-y-auto px-1 py-1">
              {workspaces.map((w) => (
                <li key={w.id}>
                  <button
                    type="button"
                    onClick={() => {
                      selectWorkspace(w.id);
                      setOpen(false);
                    }}
                    className={`flex w-full rounded-lg px-3 py-2 text-left text-sm ${
                      w.id === current?.id ? "bg-white/10 text-white" : "text-neutral-300 hover:bg-white/5"
                    }`}
                  >
                    {w.name}
                  </button>
                </li>
              ))}
            </ul>
            <form onSubmit={onCreate} className="border-t border-line-strong p-2">
              <p className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-wide text-muted">New workspace</p>
              <div className="flex gap-2">
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Name"
                  className="min-w-0 flex-1 rounded-lg border border-line bg-black/30 px-2 py-1.5 text-sm text-white placeholder:text-muted"
                  maxLength={120}
                />
                <button
                  type="submit"
                  disabled={creating || !newName.trim()}
                  className="flex shrink-0 items-center justify-center rounded-lg bg-accent/20 px-2 py-1.5 text-accent hover:bg-accent/30 disabled:opacity-40"
                  title="Create workspace"
                >
                  <Plus className="h-4 w-4" strokeWidth={2} />
                </button>
              </div>
            </form>
          </div>
        ) : null}
        {error ? <p className="mt-2 px-1 text-[11px] text-red-400">{error}</p> : null}
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        <SectionLabel>Workspace</SectionLabel>
        <NavLink
          to="/invoices"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
        >
          <FolderOpen className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
          All invoices
        </NavLink>

        <SectionLabel>Project</SectionLabel>
        <NavLink
          to="/overview"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
        >
          <LayoutGrid className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
          Overview
        </NavLink>
        <NavLink
          to="/invoices"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
        >
          <FileText className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
          Invoices
        </NavLink>
        <NavLink
          to="/chat"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
        >
          <MessageSquare className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
          Chat
        </NavLink>
        <NavLink
          to="/reports"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
        >
          <BarChart3 className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
          Reports
        </NavLink>
      </nav>

      <div className="border-t border-line p-4">
        <div className="flex items-center gap-3 rounded-xl bg-raised/80 px-3 py-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10">
            <Sparkles className="h-5 w-5 text-accent" strokeWidth={1.5} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{current?.name ?? "Workspace"}</p>
            <p className="truncate text-xs text-muted">Per-workspace data &amp; chat</p>
          </div>
        </div>
        <p className="mt-3 px-1 text-[11px] text-muted">© 2026 Smart Invoice</p>
      </div>
    </aside>
  );
}
