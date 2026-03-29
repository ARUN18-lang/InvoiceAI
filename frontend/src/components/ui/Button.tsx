import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

const variants: Record<Variant, string> = {
  primary:
    "bg-accent shadow-md hover:bg-accent-hover " +
    "!text-white font-semibold tracking-tight " +
    "[&_svg]:shrink-0 [&_svg]:!text-white [&_svg]:stroke-white " +
    "disabled:opacity-60 disabled:pointer-events-none disabled:shadow-none",
  secondary:
    "border border-line-strong bg-raised !text-neutral-100 shadow-sm hover:bg-white/[0.08] " +
    "font-medium [&_svg]:shrink-0 [&_svg]:!text-neutral-200 [&_svg]:stroke-neutral-200 " +
    "disabled:opacity-50 disabled:pointer-events-none",
  ghost:
    "!text-neutral-200 hover:bg-white/10 hover:!text-white " +
    "[&_svg]:shrink-0 [&_svg]:!text-neutral-300 [&_svg]:stroke-neutral-300 " +
    "disabled:opacity-50 disabled:pointer-events-none",
};

/** Ensures label stays white on accent (some browsers ignore inherited color on buttons). */
const primaryLabelStyle: CSSProperties = {
  color: "#ffffff",
  WebkitTextFillColor: "#ffffff",
};

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  style,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
}) {
  const mergedStyle: CSSProperties | undefined =
    variant === "primary" ? { ...primaryLabelStyle, ...style } : style;

  return (
    <button
      type={type}
      style={mergedStyle}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm transition-colors ${variants[variant]} ${className}`}
      {...props}
    />
  );
}
