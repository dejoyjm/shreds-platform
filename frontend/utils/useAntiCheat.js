// utils/useAntiCheat.js
import { useEffect } from "react";
import toast from "react-hot-toast";

const ENABLE_ANTICHEAT = false;
const MAX_VIOLATIONS = 3;
let violationCount = 0;

export function useAntiCheat(onViolation) {
  useEffect(() => {
    if (!ENABLE_ANTICHEAT) return;

    // ✅ Safe client-side sessionStorage access
    violationCount = parseInt(sessionStorage.getItem("violationCount") || "0");

    const warn = (reason) => {
      violationCount += 1;
      sessionStorage.setItem("violationCount", violationCount.toString());
      toast.error(`⚠️ ${reason} [${violationCount}/${MAX_VIOLATIONS}]`);

      if (typeof onViolation === "function") {
        onViolation(reason);
      }

      if (violationCount >= MAX_VIOLATIONS) {
        toast.error("❌ Too many violations. Submitting your test.");
        setTimeout(() => {
          window.dispatchEvent(new CustomEvent("autoSubmitDueToCheating"));
        }, 1000);
      }
    };

    const requestFullscreenSafely = () => {
      setTimeout(() => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
        }
      }, 1500);
    };

    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) {
        warn("Exited fullscreen");
        requestFullscreenSafely();
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) warn("Switched tab or minimized");
    };

    const handleBlur = () => {
      warn("Lost browser focus");
    };

    const handleContextMenu = (e) => {
      e.preventDefault();
      warn("Right-click detected");
    };

    const handleKeyDown = (e) => {
      const key = e.key.toLowerCase();
      if (
        (e.ctrlKey && ["c", "u", "s"].includes(key)) ||
        key === "f12" ||
        (e.ctrlKey && e.shiftKey && ["i", "j"].includes(key))
      ) {
        e.preventDefault();
        warn("Restricted shortcut detected");
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleBlur);
    document.addEventListener("contextmenu", handleContextMenu);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleBlur);
      document.removeEventListener("contextmenu", handleContextMenu);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onViolation]);
}