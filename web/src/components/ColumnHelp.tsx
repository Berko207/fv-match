"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

const HIDE_DELAY_MS = 220;

interface ColumnHelpProps {
  help: string;
}

export function ColumnHelp({ help }: ColumnHelpProps) {
  const tooltipId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const hideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0, bridgeTop: 0, bridgeHeight: 0 });
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => {
      if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current);
    };
  }, []);

  const cancelHide = useCallback(() => {
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
  }, []);

  const scheduleHide = useCallback(() => {
    cancelHide();
    hideTimeoutRef.current = setTimeout(() => setOpen(false), HIDE_DELAY_MS);
  }, [cancelHide]);

  const updatePosition = useCallback(() => {
    const rect = buttonRef.current?.getBoundingClientRect();
    if (!rect) return;
    const gap = 6;
    setCoords({
      top: rect.bottom + gap,
      left: rect.left + rect.width / 2,
      bridgeTop: rect.bottom,
      bridgeHeight: gap,
    });
  }, []);

  const show = useCallback(() => {
    cancelHide();
    updatePosition();
    setOpen(true);
  }, [cancelHide, updatePosition]);

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

  const keepOpen = useCallback(() => {
    cancelHide();
    setOpen(true);
  }, [cancelHide]);

  return (
    <>
      <button
        ref={buttonRef}
        aria-describedby={open ? tooltipId : undefined}
        aria-label="Column help"
        className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-slate-500/50 bg-slate-900/40 text-[0.6rem] font-bold leading-none text-slate-400 transition hover:border-emerald-400/70 hover:bg-emerald-500/10 hover:text-emerald-200 focus-visible:border-emerald-400/70 focus-visible:bg-emerald-500/10 focus-visible:text-emerald-200 focus-visible:outline-none"
        type="button"
        onBlur={scheduleHide}
        onFocus={show}
        onMouseEnter={show}
        onMouseLeave={scheduleHide}
      >
        ?
      </button>

      {mounted && open
        ? createPortal(
            <>
              {/* Invisible bridge so the cursor can travel to the tooltip */}
              <div
                aria-hidden="true"
                className="fixed z-[9998]"
                style={{
                  top: coords.bridgeTop,
                  left: coords.left - 24,
                  width: 48,
                  height: coords.bridgeHeight,
                }}
                onMouseEnter={keepOpen}
                onMouseLeave={scheduleHide}
              />
              <div
                className="fixed z-[9999] w-max max-w-[15rem] -translate-x-1/2 rounded-lg border border-slate-500/30 bg-[#0b1016] px-3 py-2 text-left text-xs font-normal normal-case leading-snug tracking-normal text-slate-100 shadow-[0_12px_32px_rgba(0,0,0,0.45)]"
                id={tooltipId}
                role="tooltip"
                style={{ top: coords.top, left: coords.left }}
                onMouseEnter={keepOpen}
                onMouseLeave={scheduleHide}
              >
                {help}
              </div>
            </>,
            document.body,
          )
        : null}
    </>
  );
}
