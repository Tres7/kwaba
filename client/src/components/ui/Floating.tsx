"use client";

import { forwardRef, useLayoutEffect, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

interface FloatingProps {
  anchor: React.RefObject<HTMLElement | null>;
  /** Desired width on large screens (px); by default the trigger's. */
  width?: number;
  /** Alignment on the trigger. */
  align?: "start" | "end";
  /** On mobile, shows as a bottom panel with a darkened background. */
  sheetOnMobile?: boolean;
  onClose: () => void;
  label: string;
  className?: string;
  children: React.ReactNode;
}

const MD = 768;
const MARGE = 16;

/**
 * Panel rendered in <body>: never cut by an overflow-hidden or animated parent,
 * positioned under its trigger and recomputed on scroll and resize.
 */
const Floating = forwardRef<HTMLDivElement, FloatingProps>(function Floating(
  { anchor, width, align = "start", sheetOnMobile = false, onClose, label, className, children }, ref
) {
  const [pos, setPos] = useState<{ top: number; left: number; w: number; mobile: boolean } | null>(null);

  useLayoutEffect(() => {
    const calculer = () => {
      const el = anchor.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const vw = window.innerWidth;
      const mobile = vw < MD;
      const w = Math.min(width ?? r.width, vw - 2 * MARGE);
      let left = align === "end" ? r.right - w : r.left;
      left = Math.max(MARGE, Math.min(left, vw - w - MARGE));
      setPos({ top: r.bottom + 8, left, w, mobile });
    };
    calculer();
    window.addEventListener("resize", calculer);
    window.addEventListener("scroll", calculer, true);
    return () => {
      window.removeEventListener("resize", calculer);
      window.removeEventListener("scroll", calculer, true);
    };
  }, [anchor, width, align]);

  if (!pos) return null;

  const enFeuille = sheetOnMobile && pos.mobile;

  return createPortal(
    <>
      {enFeuille && <div className="fixed inset-0 z-[80] bg-black/40" onClick={onClose} aria-hidden />}
      <div
        ref={ref} role="dialog" aria-label={label}
        style={enFeuille ? undefined : { top: pos.top, left: pos.left, width: pos.w }}
        className={cn(
          "fixed z-[90] bg-white shadow-card-hover border border-gray-100",
          enFeuille ? "inset-x-0 bottom-0 max-h-[85vh] overflow-auto rounded-t-3xl p-5" : "rounded-2xl max-h-[calc(100vh-6rem)] overflow-auto",
          className,
        )}
      >
        {children}
      </div>
    </>,
    document.body,
  );
});

export default Floating;
