import { useEffect, useRef } from "react";

/**
 * Calls `callback` every `intervalMs` milliseconds:
 * - never two calls in parallel (the next one is scheduled when the previous one ends);
 * - paused when the tab is hidden;
 * - immediate call when coming back to the tab or when the window gets the focus back
 *   (two windows side by side, where the tab stays visible all the time).
 */
export function usePolling(callback: () => Promise<void> | void, intervalMs: number, enabled = true) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;

    let timer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;
    let running = false;

    const tick = async () => {
      if (running || cancelled) return;
      running = true;
      try {
        if (document.visibilityState === "visible") await savedCallback.current();
      } catch {
        // One-off network error: try again at the next tick
      } finally {
        running = false;
        if (!cancelled) timer = setTimeout(tick, intervalMs);
      }
    };

    const refreshNow = () => {
      if (document.visibilityState === "visible" && !running) {
        clearTimeout(timer);
        tick();
      }
    };

    timer = setTimeout(tick, intervalMs);
    document.addEventListener("visibilitychange", refreshNow);
    window.addEventListener("focus", refreshNow);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", refreshNow);
      window.removeEventListener("focus", refreshNow);
    };
  }, [intervalMs, enabled]);
}
