import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { InvoiceCard } from "@/components/invoices/InvoiceCard";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchInvoices, uploadInvoice, type InvoiceRecord } from "@/lib/api";
import { Filter, Plus, Search } from "lucide-react";

type SortKey = "newest" | "oldest" | "vendor";

export function InvoicesPage() {
  const { current } = useWorkspace();
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) {
      setLoading(true);
      setError(null);
    }
    try {
      const list = await fetchInvoices(100);
      setInvoices(list);
    } catch (e) {
      if (!opts?.silent) {
        setError(e instanceof Error ? e.message : "Failed to load invoices");
      }
    } finally {
      if (!opts?.silent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (!current?.id) return;
    void load();
  }, [load, current?.id]);

  useEffect(() => {
    const busy = invoices.some((i) => (i.status ?? "completed") === "processing");
    if (!busy) return;
    const t = setInterval(() => void load({ silent: true }), 3000);
    return () => clearInterval(t);
  }, [invoices, load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = invoices;
    if (q) {
      list = list.filter((i) => {
        const hay = [
          i.vendor_name,
          i.invoice_number,
          i.category,
          i.id,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return hay.includes(q);
      });
    }
    const sorted = [...list];
    sorted.sort((a, b) => {
      if (sort === "vendor") {
        return (a.vendor_name || "").localeCompare(b.vendor_name || "");
      }
      const ta = new Date(a.created_at).getTime();
      const tb = new Date(b.created_at).getTime();
      return sort === "newest" ? tb - ta : ta - tb;
    });
    return sorted;
  }, [invoices, query, sort]);

  const onPickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const created = await uploadInvoice(file);
      setInvoices((prev) => {
        const rest = prev.filter((i) => i.id !== created.invoice.id);
        return [created.invoice, ...rest];
      });
      void load({ silent: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <PageHeader
        breadcrumb="Home"
        title="Invoices"
        subtitle="Upload, digitize, and manage invoices with AI extraction and validation."
        action={
          <>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp,.tiff,.bmp"
              className="hidden"
              onChange={onPickFile}
            />
            <Button
              variant="primary"
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
              className="min-w-[160px]"
            >
              <Plus className="h-4 w-4" strokeWidth={2.25} />
              {uploading ? "Uploading…" : "Upload invoice"}
            </Button>
          </>
        }
      />

      <div className="px-8 py-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative max-w-xl flex-1">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
            <Input
              placeholder="Search invoices…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-11"
            />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-muted-dim">
              <Filter className="h-4 w-4 text-neutral-400" strokeWidth={2} />
              <span className="text-xs font-semibold uppercase tracking-wide text-neutral-400">Sort</span>
            </div>
            <div className="w-48 min-w-[12rem]">
              <Select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
                <option className="bg-[#1a1a1a] text-neutral-100" value="newest">
                  Newest first
                </option>
                <option className="bg-[#1a1a1a] text-neutral-100" value="oldest">
                  Oldest first
                </option>
                <option className="bg-[#1a1a1a] text-neutral-100" value="vendor">
                  Vendor A–Z
                </option>
              </Select>
            </div>
            <p className="text-sm font-medium text-neutral-300">
              {filtered.length} of {invoices.length} invoices
            </p>
          </div>
        </div>

        {error ? <p className="mt-6 text-sm text-red-400">{error}</p> : null}

        {loading ? (
          <p className="mt-10 text-sm text-muted">Loading invoices…</p>
        ) : filtered.length === 0 ? (
          <p className="mt-10 text-sm text-muted">No invoices yet. Upload a PDF or image to get started.</p>
        ) : (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((inv) => (
              <InvoiceCard key={inv.id} invoice={inv} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
