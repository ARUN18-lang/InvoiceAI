import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchAnalyticsDashboard, type AnalyticsDashboard } from "@/lib/api";
import { categoryLabel, formatMoney } from "@/lib/format";
import { AlertTriangle, BarChart3, Receipt, TrendingUp } from "lucide-react";

function Kpi({
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
    <div className="rounded-xl border border-line-strong bg-raised p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
          <p className="mt-2 text-xl font-semibold tracking-tight text-neutral-100 sm:text-2xl">{value}</p>
          {hint ? <p className="mt-1 text-xs text-muted-dim">{hint}</p> : null}
        </div>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent">
          <Icon className="h-4 w-4" strokeWidth={2} />
        </span>
      </div>
    </div>
  );
}

export function ReportsPage() {
  const { current } = useWorkspace();
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!current?.id) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const d = await fetchAnalyticsDashboard(12);
        if (!cancelled) setData(d);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load analytics");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [current?.id]);

  const maxMonthly = useMemo(() => {
    if (!data?.monthly?.length) return 1;
    return Math.max(...data.monthly.map((m) => m.total_amount), 1);
  }, [data]);

  const maxCat = useMemo(() => {
    if (!data?.by_category?.length) return 1;
    return Math.max(...data.by_category.map((c) => c.total_amount), 1);
  }, [data]);

  return (
    <div>
      <PageHeader
        breadcrumb="Home"
        title="Reports"
        subtitle="Live aggregates from your invoice collection via the analytics API — updates as you upload and process invoices."
      />
      <div className="space-y-8 px-8 py-8">
        {error ? <p className="text-sm text-red-400">{error}</p> : null}

        {loading ? (
          <p className="text-sm text-muted">Loading analytics…</p>
        ) : data ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              <Kpi label="Invoices" value={String(data.invoice_count)} hint="Completed in workspace" icon={Receipt} />
              <Kpi
                label="Total spend"
                value={formatMoney(data.total_spend, "INR")}
                hint="Sum of invoice totals"
                icon={TrendingUp}
              />
              <Kpi
                label="Total tax"
                value={formatMoney(data.total_tax, "INR")}
                hint="Sum of extracted tax"
                icon={Receipt}
              />
              <Kpi
                label="Overdue"
                value={String(data.overdue_count)}
                hint="Due date before today"
                icon={AlertTriangle}
              />
              <Kpi
                label="Due in 7 days"
                value={String(data.due_within_7d_count)}
                hint="Upcoming payments"
                icon={BarChart3}
              />
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-xl border border-line-strong bg-raised p-6 shadow-card">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Spend by category</h2>
                {data.by_category.length === 0 ? (
                  <p className="mt-6 text-sm text-muted">No data yet. Upload and complete invoices to see breakdowns.</p>
                ) : (
                  <ul className="mt-6 space-y-4">
                    {data.by_category.map((row) => {
                      const pct = Math.round((row.total_amount / maxCat) * 100);
                      return (
                        <li key={row.category}>
                          <div className="flex items-center justify-between gap-3 text-sm">
                            <span className="truncate font-medium text-neutral-100">{categoryLabel(row.category)}</span>
                            <span className="shrink-0 tabular-nums text-neutral-200">
                              {formatMoney(row.total_amount, "INR")}
                            </span>
                          </div>
                          <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface">
                            <div className="h-full rounded-full bg-accent/80" style={{ width: `${pct}%` }} />
                          </div>
                          <p className="mt-1 text-xs text-muted">{row.invoice_count} invoices</p>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              <div className="rounded-xl border border-line-strong bg-raised p-6 shadow-card">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Top vendors</h2>
                {data.top_vendors.length === 0 ? (
                  <p className="mt-6 text-sm text-muted">No vendor data yet.</p>
                ) : (
                  <ul className="mt-6 space-y-3">
                    {data.top_vendors.map((v) => (
                      <li
                        key={v.vendor_name}
                        className="flex items-center justify-between gap-3 border-b border-line pb-3 text-sm last:border-0 last:pb-0"
                      >
                        <span className="truncate font-medium text-neutral-100">{v.vendor_name}</span>
                        <span className="shrink-0 tabular-nums text-neutral-200">
                          {formatMoney(v.total_amount, "INR")}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>

            <section className="rounded-xl border border-line-strong bg-raised p-6 shadow-card">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Monthly spend</h2>
              {data.monthly.length === 0 ? (
                <p className="mt-6 text-sm text-muted">No invoice dates to chart yet.</p>
              ) : (
                <ul className="mt-6 space-y-3">
                  {[...data.monthly].reverse().map((row) => {
                    const pct = Math.round((row.total_amount / maxMonthly) * 100);
                    return (
                      <li key={row.month} className="flex items-center gap-4 text-sm">
                        <span className="w-24 shrink-0 font-mono text-xs text-muted">{row.month}</span>
                        <div className="min-w-0 flex-1">
                          <div className="h-6 overflow-hidden rounded-md bg-surface">
                            <div
                              className="flex h-full items-center bg-accent/70 pl-2 text-xs font-medium text-white"
                              style={{ width: `${Math.max(pct, 4)}%` }}
                            >
                              {pct > 18 ? formatMoney(row.total_amount, "INR") : null}
                            </div>
                          </div>
                        </div>
                        <span className="w-28 shrink-0 text-right tabular-nums text-neutral-200">
                          {formatMoney(row.total_amount, "INR")}
                        </span>
                        <span className="hidden w-16 shrink-0 text-right text-xs text-muted sm:block">
                          {row.invoice_count} inv.
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          </>
        ) : (
          <p className="text-sm text-muted">No analytics data.</p>
        )}
      </div>
    </div>
  );
}
