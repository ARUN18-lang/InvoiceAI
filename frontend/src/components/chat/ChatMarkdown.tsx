import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

const components: Components = {
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0 leading-relaxed text-white/90">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5 text-white/90">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5 text-white/90">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }) => <em className="italic text-neutral-200">{children}</em>,
  h1: ({ children }) => <h1 className="mb-2 mt-3 text-lg font-semibold text-white first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-2 mt-3 text-base font-semibold text-white first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-1.5 mt-3 text-sm font-semibold uppercase tracking-wide text-muted first:mt-0">{children}</h3>,
  a: ({ href, children }) => (
    <a href={href} className="text-accent underline-offset-2 hover:underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-accent/50 pl-3 text-neutral-300">{children}</blockquote>
  ),
  hr: () => <hr className="my-4 border-line" />,
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-line">
      <table className="w-full border-collapse text-left text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="border-b border-line bg-surface">{children}</thead>,
  th: ({ children }) => <th className="px-3 py-2 font-semibold text-neutral-200">{children}</th>,
  td: ({ children }) => <td className="border-t border-line px-3 py-2 text-neutral-300">{children}</td>,
  code({ className, children }) {
    const text = String(children);
    const isBlock = Boolean(className?.startsWith("language-")) || text.includes("\n");
    if (!isBlock) {
      return (
        <code className="rounded bg-white/[0.08] px-1.5 py-0.5 font-mono text-[0.9em] text-amber-100/90">{children}</code>
      );
    }
    return <code className="block whitespace-pre-wrap font-mono text-xs leading-relaxed text-neutral-200">{children}</code>;
  },
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg border border-line-strong bg-black/40 p-3">{children}</pre>
  ),
};

type Props = {
  children: string;
  className?: string;
};

export function ChatMarkdown({ children, className }: Props) {
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
