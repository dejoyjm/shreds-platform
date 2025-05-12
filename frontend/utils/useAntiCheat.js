// utils/useAntiCheat.js
import { useEffect } from "react";

const ENABLE_ANTICHEAT = false; // 🔁 Toggle this flag to enable/disable

export function useAntiCheat(triggerWarning) {
  useEffect(() => {
    if (!ENABLE_ANTICHEAT) return;

    const handleVisibilityChange = () => {
      if (document.hidden) triggerWarning("Tab switch / window hidden");
    };
    const handleBlur = () => {
      triggerWarning("Switched away from browser");
    };
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) {
        alert("⚠️ Please return to fullscreen.");
      }
    };

    window.addEventListener("blur", handleBlur);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    document.addEventListener("fullscreenchange", handleFullscreenChange);

    return () => {
      window.removeEventListener("blur", handleBlur);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, [triggerWarning]);
}
