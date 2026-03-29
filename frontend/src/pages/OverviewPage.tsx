import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/layout/PageHeader";
import { useWorkspace } from "@/context/WorkspaceContext";
import {
  fetchInvoices,
  fetchNotifications,
  invoicesExportUrl,
  markNotificationRead,
  type InvoiceRecord,
  type NotificationRecord,
} from "@/lib/api";
import { categoryLabel, formatDate, formatMoney } from "@/lib/format";
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  FileText,
  MessageSquare,
  Receipt,
  TrendingUp,
  Upload,
} from "lucide-react";

function StatCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint?: string;
  icon: typeof Receipt;
}) {
  return (
    <div className="rounded-xl border border-line-strong bg-raised p-6 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-neutral-100 sm:text-3xl">{value}</p>
          {hint ? <p className="mt-2 text-xs text-muted-dim">{hint}</p> : null}
        </div>
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent">
          <Icon className="h-5 w-5" strokeWidth={1.75} />
        </span>
      </div>
    </div>
  );
}

export function OverviewPage() {
  const { current } = useWorkspace();
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<NotificationRecord[]>([]);

  useEffect(() => {
    if (!current?.id) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const list = await fetchInvoices(200);
        if (!cancelled) setInvoices(list);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [current?.id]);

  useEffect(() => {
    if (!current?.id) return;
    let cancelled = false;
    (async () => {
      try {
        const n = await fetchNotifications(25);
        if (!cancelled) setAlerts(n);
      } catch {
        if (!cancelled) setAlerts([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [current?.id]);

  const stats = useMemo(() => {
    const count = invoices.length;
    const completed = invoices.filter((i) => (i.status ?? "completed") === "completed");
    const sum = completed.reduce((a, i) => a + (i.total_amount ?? 0), 0);
    const taxSum = completed.reduce((a, i) => a + (i.tax_amount ?? 0), 0);
    const avg = completed.length ? sum / completed.length : 0;
    const flagged = completed.filter(
      (i) => !i.validation.is_valid || (i.validation.fraud_flags?.length ?? 0) > 0
    ).length;
    const byCat = new Map<string, number>();
    for (const i of completed) {
      const k = i.category || "other";
      byCat.set(k, (byCat.get(k) ?? 0) + (i.total_amount ?? 0));
    }
    const categories = [...byCat.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
    const recent = [...invoices].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 6);
    return { count, sum, taxSum, avg, flagged, categories, recent };
  }, [invoices]);

  const maxCat = stats.categories[0]?.[1] ?? 1;

  return (
    <div>
      <PageHeader
        breadcrumb="Home"
        title="Overview"
        subtitle="Spend, categories, validation signals, and recent activity across your workspace."
      />
      <div className="space-y-10 px-8 py-8">
        {error ? <p className="text-sm text-red-400">{error}</p> : null}

        {/* Quick actions — explicit contrast so labels always read clearly */}
        <section className="flex flex-col gap-3 rounded-xl border border-line-strong bg-surface p-5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-neutral-100">Quick actions</p>
            <p className="mt-1 text-xs text-muted-dim">Upload, review invoices, or ask the assistant.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/invoices"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-semibold !text-white shadow-md transition-colors hover:bg-accent-hover"
              style={{ color: "#ffffff", WebkitTextFillColor: "#ffffff" }}
            >
              <Upload className="h-4 w-4 shrink-0" strokeWidth={2.25} />
              Upload invoice
            </Link>
            <Link
              to="/invoices"
              className="inline-flex items-center justify-center gap-2 rounded-full border border-line-strong bg-raised px-5 py-2.5 text-sm font-medium text-neutral-100 transition-colors hover:bg-white/[0.08]"
            >
              <FileText className="h-4 w-4 shrink-0 text-neutral-300" strokeWidth={2} />
              View all
            </Link>
            <Link
              to="/chat"
              className="inline-flex items-center justify-center gap-2 rounded-full border border-line-strong bg-raised px-5 py-2.5 text-sm font-medium text-neutral-100 transition-colors hover:bg-white/[0.08]"
            >
              <MessageSquare className="h-4 w-4 shrink-0 text-neutral-300" strokeWidth={2} />
              Chat
            </Link>
            <a
              href={invoicesExportUrl("csv")}
              className="inline-flex items-center justify-center gap-2 rounded-full border border-line-strong bg-raised px-5 py-2.5 text-sm font-medium text-neutral-100 transition-colors hover:bg-white/[0.08]"
            >
              Export CSV
            </a>
            <a
              href={invoicesExportUrl("xlsx")}
              className="inline-flex items-center justify-center gap-2 rounded-full border border-line-strong bg-raised px-5 py-2.5 text-sm font-medium text-neutral-100 transition-colors hover:bg-white/[0.08]"
            >
              Export Excel
            </a>
          </div>
        </section>

        <section className="rounded-xl border border-line-strong bg-raised p-6 shadow-card">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-amber-400" strokeWidth={2} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Due-date alerts</h2>
          </div>
          <p className="mt-2 text-xs text-muted-dim">
            Created by the backend scheduler (on startup and daily 08:00 UTC) for overdue and due-soon invoices. Dismiss
            marks an alert read in the database.
          </p>
          {alerts.length === 0 ? (
            <p className="mt-4 text-sm text-muted">
              No alerts yet. They appear when invoices have a due date and match overdue or within-the-window rules.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {alerts.map((a) => (
                <li
                  key={a.id}
                  className={`flex flex-col gap-2 rounded-lg border px-3 py-3 sm:flex-row sm:items-center sm:justify-between ${
                    a.read ? "border-line bg-surface/50 opacity-80" : "border-amber-500/25 bg-surface"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-neutral-100">{a.message}</p>
                    <p className="mt-1 text-xs text-muted">
                      {a.kind === "overdue" ? "Overdue" : "Due soon"}
                      {a.due_date ? ` · due ${formatDate(a.due_date)}` : null}
                      {a.read ? " · read" : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Link
                      to={`/invoices/${a.invoice_id}`}
                      className="inline-flex items-center justify-center rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-neutral-200 hover:bg-white/[0.06]"
                    >
                      Open invoice
                    </Link>
                    {!a.read ? (
                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            await markNotificationRead(a.id);
                            setAlerts((prev) => prev.map((x) => (x.id === a.id ? { ...x, read: true } : x)));
                          } catch {
                            /* ignore */
                          }
                        }}
                        className="inline-flex items-center justify-center rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-muted hover:text-neutral-200"
                      >
                        Dismiss
                      </button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {loading ? (
          <p className="text-sm text-muted">Loading overview…</p>
        ) : (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard label="Invoices" value={String(stats.count)} hint="Digitized in this workspace" icon={Receipt} />
              <StatCard
                label="Total spend"
                value={formatMoney(stats.sum, "INR")}
                hint="Sum of invoice totals"
                icon={TrendingUp}
              />
              <StatCard
                label="Total tax"
                value={formatMoney(stats.taxSum, "INR")}
                hint="Sum of extracted tax"
                icon={Receipt}
              />
              <StatCard
                label="Avg invoice"
                value={stats.count ? formatMoney(stats.avg, "INR") : "—"}
                hint="Mean of totals"
                icon={TrendingUp}
              />
            </section>

            <section className="grid gap-6 lg:grid-cols-5">
              <div className="rounded-xl border border-line-strong bg-raised p-6 shadow-card lg:col-span-3">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Spend by category</h2>
                  <span className="text-xs text-muted-dim">{stats.categories.length} categories</span>
                </div>
                {stats.categories.length === 0 ? (
                  <p className="mt-6 text-sm text-muted-dim">No category data yet. Upload invoices to populate.</p>
                ) : (
                  <ul className="mt-6 space-y-4">
                    {stats.categories.map(([cat, amount]) => {
                      const pct = Math.round((amount / maxCat) * 100);
                      return (
                        <li key={cat}>
                          <div className="flex items-center justify-between gap-3 text-sm">
                            <span className="truncate font-medium text-neutral-100">{categoryLabel(cat)}</span>
                            <span className="shrink-0 tabular-nums text-neutral-200">{formatMoney(amount, "INR")}</span>
                          </div>
                          <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface">
                            <div
                              className="h-full rounded-full bg-accent/80 transition-all"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              <div className="rounded-xl border border-line-strong bg-raised p-6 shadow-card lg:col-span-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-400" strokeWidth={2} />
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Review queue</h2>
                </div>
                <p className="mt-4 text-3xl font-semibold text-neutral-100">{stats.flagged}</p>
                <p className="mt-1 text-xs text-muted-dim">
                  Invoices with validation errors or fraud heuristics — open detail to review.
                </p>
                {stats.flagged > 0 ? (
                  <Link
                    to="/invoices"
                    className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-accent hover:text-accent-hover"
                  >
                    Open invoices
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                ) : null}
              </div>
            </section>

            <section className="rounded-xl border border-line-strong bg-raised shadow-card">
              <div className="flex items-center justify-between border-b border-line px-6 py-4">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Recent invoices</h2>
                <Link to="/invoices" className="text-xs font-medium text-accent hover:text-accent-hover">
                  See all
                </Link>
              </div>
              {stats.recent.length === 0 ? (
                <p className="px-6 py-10 text-center text-sm text-muted-dim">Nothing here yet — upload your first invoice.</p>
              ) : (
                <ul className="divide-y divide-line">
                  {stats.recent.map((inv) => (
                    <li key={inv.id}>
                      <Link
                        to={`/invoices/${inv.id}`}
                        className="flex items-center justify-between gap-4 px-6 py-4 transition-colors hover:bg-white/[0.03]"
                      >
                        <div className="min-w-0">
                          <p className="truncate font-medium text-neutral-100">{inv.vendor_name || "Unknown vendor"}</p>
                          <p className="mt-0.5 truncate text-xs text-muted-dim">
                            {inv.invoice_number ? `#${inv.invoice_number}` : "No number"} · {categoryLabel(inv.category)}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-sm font-semibold tabular-nums text-neutral-100">
                            {formatMoney(inv.total_amount, inv.currency)}
                          </p>
                          <p className="text-xs text-muted-dim">{formatDate(inv.created_at)}</p>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
