import { useEffect, useRef, useState } from "react";

/**
 * Replicates the design handoff's sidebar toggle state machine exactly
 * (CareerAutomated Dashboard.dc.html): open by default at >=1024px, closed
 * below it, auto-syncing to viewport width on resize UNLESS the user has
 * manually toggled it (sidebarSetByUser) — once they have, their choice
 * sticks regardless of further resizing.
 */
export function useSidebarState() {
  // Both start matching the server-rendered default (open, wide) unconditionally —
  // branching on `window` here would make the client's first render disagree with
  // the SSR'd HTML, and React does not patch up a hydration mismatch on its own.
  // The real viewport is instead measured client-side in the effect below, as an
  // ordinary post-mount state update rather than part of hydration.
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isNarrow, setIsNarrow] = useState(false);
  const sidebarSetByUser = useRef(false);

  useEffect(() => {
    // SSR can't know the client's real viewport width, so the initial state
    // defaults open (matching desktop). Correct it against the actual client
    // width immediately on mount, then keep tracking on resize.
    const sync = () => {
      const vw = window.innerWidth;
      setIsNarrow(vw < 1024);
      if (!sidebarSetByUser.current) {
        setSidebarOpen(vw >= 1024);
      }
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, []);

  const toggleSidebar = () => {
    sidebarSetByUser.current = true;
    setSidebarOpen((v) => !v);
  };

  const closeSidebarOverlay = () => {
    sidebarSetByUser.current = true;
    setSidebarOpen(false);
  };

  return { sidebarOpen, isNarrow, toggleSidebar, closeSidebarOverlay };
}
