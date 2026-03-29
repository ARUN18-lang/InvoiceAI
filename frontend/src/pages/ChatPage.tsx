import { useEffect, useRef, useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { ChatMarkdown } from "@/components/chat/ChatMarkdown";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useWorkspace } from "@/context/WorkspaceContext";
import { chatInvoices, type ChatSourceCitation } from "@/lib/api";
import { categoryLabel, formatMoney } from "@/lib/format";
import { Send } from "lucide-react";

const MAX_HISTORY = 10;

type ThreadEntry =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; citations: ChatSourceCitation[] };

function storageKey(workspaceId: string) {
  return `smartinvoice_chat_${workspaceId}`;
}

export function ChatPage() {
  const { current } = useWorkspace();
  const wid = current?.id ?? "";
  const [input, setInput] = useState("");
  const [thread, setThread] = useState<ThreadEntry[]>([]);
  const [followUps, setFollowUps] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const skipSave = useRef(false);

  useEffect(() => {
    if (!wid) {
      setThread([]);
      return;
    }
    skipSave.current = true;
    try {
      const raw = localStorage.getItem(storageKey(wid));
      setThread(raw ? (JSON.parse(raw) as ThreadEntry[]) : []);
    } catch {
      setThread([]);
    }
  }, [wid]);

  useEffect(() => {
    if (!wid) return;
    if (skipSave.current) {
      skipSave.current = false;
      return;
    }
    try {
      localStorage.setItem(storageKey(wid), JSON.stringify(thread));
    } catch {
      /* quota or private mode */
    }
  }, [thread, wid]);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading || !wid) return;
    setLoading(true);
    setError(null);
    setFollowUps([]);
    const history = thread.slice(-MAX_HISTORY).map((t) => ({ role: t.role, content: t.content }));
    try {
      const res = await chatInvoices({ message: q, invoice_ids: null, history });
      setThread((prev) => [
        ...prev,
        { role: "user", content: q },
        {
          role: "assistant",
          content: res.answer,
          citations:
            (res.source_citations?.length ?? 0) > 0
              ? res.source_citations!
              : (res.source_invoice_ids ?? []).map((id) => ({
                  invoice_id: id,
                  vendor_name: null,
                  invoice_number: null,
                  total_amount: null,
                  category: null,
                  text_excerpt: "(Citation details not returned by server — update the API.)",
                  via: "semantic_search" as const,
                })),
        },
      ]);
      setInput("");
      setFollowUps(res.suggested_follow_ups ?? []);
      requestAnimationFrame(scrollToBottom);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  };

  const useFollowUp = (q: string) => {
    setInput(q);
  };

  return (
    <div>
      <PageHeader
        breadcrumb="Home"
        title="Chat"
        subtitle="Answers use invoices in the current workspace only. Source excerpts are chosen to match your question. This thread is saved in the browser per workspace."
      />
      <div className="px-8 py-8">
        {!wid ? (
          <p className="text-sm text-muted">Select a workspace in the sidebar to use chat.</p>
        ) : null}

        <div className="mb-6 max-h-[min(56vh,560px)] overflow-y-auto rounded-xl border border-line-strong bg-surface/40 p-4">
          {thread.length === 0 ? (
            <p className="text-sm text-muted">
              Ask anything about invoices in this workspace. The conversation persists when you navigate away.
            </p>
          ) : (
            <ul className="space-y-4">
              {thread.map((m, i) =>
                m.role === "user" ? (
                  <li
                    key={`${i}-user`}
                    className="ml-8 rounded-lg border border-line bg-raised px-4 py-3 text-sm leading-relaxed text-white/90"
                  >
                    <span className="mb-2 block text-[10px] font-semibold uppercase tracking-wide text-muted">You</span>
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  </li>
                ) : (
                  <li
                    key={`${i}-assistant`}
                    className="mr-8 rounded-lg border border-line-strong bg-raised px-4 py-3 text-sm text-white/90"
                  >
                    <span className="mb-2 block text-[10px] font-semibold uppercase tracking-wide text-muted">Assistant</span>
                    <ChatMarkdown>{m.content}</ChatMarkdown>
                    {m.citations.length > 0 ? (
                      <div className="mt-4 border-t border-line pt-3">
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Sources</h3>
                        <p className="mt-1 text-[11px] text-muted-dim">
                          Excerpts are query-matched slices of stored invoice text (not only the document header).
                        </p>
                        <ul className="mt-3 space-y-3">
                          {m.citations.map((c) => (
                            <li
                              key={`${c.invoice_id}-${c.via}`}
                              className="rounded-lg border border-line-strong bg-surface/60 p-3"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="min-w-0 text-xs text-neutral-200">
                                  <span className="font-medium text-white">{c.vendor_name || "Unknown vendor"}</span>
                                  {c.invoice_number ? (
                                    <span className="text-muted"> · #{c.invoice_number}</span>
                                  ) : null}
                                  {c.total_amount != null ? (
                                    <span className="text-muted"> · {formatMoney(c.total_amount, "INR")}</span>
                                  ) : null}
                                  {c.category ? <span className="text-muted"> · {categoryLabel(c.category)}</span> : null}
                                </div>
                                <div className="flex shrink-0 items-center gap-2">
                                  <span
                                    className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                                      c.via === "knowledge_graph"
                                        ? "bg-violet-500/20 text-violet-200"
                                        : "bg-accent/20 text-accent"
                                    }`}
                                  >
                                    {c.via === "knowledge_graph" ? "Graph" : "Semantic"}
                                  </span>
                                  <Link
                                    to={`/invoices/${c.invoice_id}`}
                                    className="text-[11px] font-medium text-accent hover:underline"
                                  >
                                    Open
                                  </Link>
                                </div>
                              </div>
                              <pre className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-line bg-black/35 p-2 font-mono text-[11px] leading-relaxed text-neutral-300">
                                {c.text_excerpt}
                              </pre>
                              <p className="mt-1.5 font-mono text-[10px] text-muted-dim">id: {c.invoice_id}</p>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </li>
                ),
              )}
            </ul>
          )}
          <div ref={bottomRef} />
        </div>

        {followUps.length > 0 ? (
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="w-full text-xs font-semibold uppercase tracking-wide text-muted">Next steps</span>
            {followUps.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => useFollowUp(f)}
                className="rounded-full border border-line-strong bg-raised px-3 py-1.5 text-left text-xs text-neutral-200 transition-colors hover:border-accent/40 hover:text-white"
              >
                {f}
              </button>
            ))}
          </div>
        ) : null}

        <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1">
            <label
              htmlFor="q"
              className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-neutral-400"
            >
              Message
            </label>
            <Input
              id="q"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. How much did we spend on software last month?"
              disabled={!wid}
            />
          </div>
          <Button
            type="submit"
            variant="primary"
            disabled={loading || !wid}
            className="h-[42px] shrink-0 sm:mb-0"
          >
            <Send className="h-4 w-4" strokeWidth={2} />
            {loading ? "Thinking…" : "Send"}
          </Button>
        </form>

        {error ? <p className="mt-6 text-sm text-red-400">{error}</p> : null}
      </div>
    </div>
  );
}
