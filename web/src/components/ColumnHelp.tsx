"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface ColumnHelpProps {
  help: string;
}

export function ColumnHelp({ help }: ColumnHelpProps) {
  const tooltipId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const updatePosition = useCallback(() => {
    const rect = buttonRef.current?.getBoundingClientRect();
    if (!rect) return;
    setCoords({
      top: rect.bottom + 8,
      left: rect.left + rect.width / 2,
    });
  }, []);

  const show = useCallback(() => {
    updatePosition();
    setOpen(true);
  }, [updatePosition]);

  const hide = useCallback(() => {
    setOpen(false);
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    const onScroll = () => updatePosition();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
    };
  }, [open, updatePosition]);

  return (
    <>
      <button
        ref={buttonRef}
        aria-describedby={open ? tooltipId : undefined}
        aria-label="Column help"
        className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-slate-500/50 bg-slate-900/40 text-[0.6rem] font-bold leading-none text-slate-400 transition hover:border-emerald-400/70 hover:bg-emerald-500/10 hover:text-emerald-200 focus-visible:border-emerald-400/70 focus-visible:bg-emerald-500/10 focus-visible:text-emerald-200 focus-visible:outline-none"
        title={help}
        type="button"
        onBlur={hide}
        onFocus={show}
        onMouseEnter={show}
        onMouseLeave={hide}
      >
        ?
      </button>

      {mounted && open
        ? createPortal(
            <div
              className="pointer-events-none fixed z-[9999] w-max max-w-[15rem] -translate-x-1/2 rounded-lg border border-slate-500/30 bg-[#0b1016] px-3 py-2 text-left text-xs font-normal normal-case leading-snug tracking-normal text-slate-100 shadow-[0_12px_32px_rgba(0,0,0,0.45)]"
              id={tooltipId}
              role="tooltip"
              style={{ top: coords.top, left: coords.left }}
            >
              {help}
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
