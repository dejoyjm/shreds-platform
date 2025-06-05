import { useEffect, useRef, useState } from "react";
import { logViolation } from "@/utils/api";

/**
 * Checks webcam, screen, and fullscreen permissions,
 * and returns media streams and statuses to parent.
 *
 * Props:
 * - onUpdate({ camera, screen, fullscreen, cameraStream, screenStream })
 * - antiCheatLevel: "low" | "moderate" | "high"
 */
export default function PermissionChecker({ onUpdate, antiCheatLevel = "low" }) {
  const hasCheckedRef = useRef(false);
  const hasEnteredFullscreenRef = useRef(false);

  useEffect(() => {
    if (hasCheckedRef.current) return;
    hasCheckedRef.current = true;

    const checkPermissions = async () => {
      let camera = false, screen = false, fullscreen = false;
      let cameraStream = null, screenStream = null;

      // 🎥 Camera check
      try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (cameraStream) camera = true;
      } catch (err) {
        console.warn("🚫 Camera permission denied", err);
        if (antiCheatLevel === "high") {
          console.error("🚨 Camera access required at high antiCheatLevel");
        }
      }

      // 🖥️ Screen share check
      try {
        if (!window.__activeScreenStream) {
          screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: {
              displaySurface: "monitor",
              logicalSurface: true,
              cursor: "always",
            },
          });
          window.__activeScreenStream = screenStream;
        } else {
          screenStream = window.__activeScreenStream;
        }
        if (screenStream) screen = true;
      } catch (err) {
        console.warn("🚫 Screen permission denied", err);
        if (antiCheatLevel === "high") {
          console.error("🚨 Screen share required at high antiCheatLevel");
        }
      }

      fullscreen = document.fullscreenElement !== null;

      // 🧠 Track if fullscreen was ever entered
      if (fullscreen) {
        hasEnteredFullscreenRef.current = true;
      }

      // ✅ Log violations conditionally
      if (!camera) {
        logViolation("camera_lost", { reason: "Camera stream missing" }, 2);
      }
      if (!screen) {
        logViolation("screen_lost", { reason: "Screen share stopped" }, 3);
      }
      if (!fullscreen && hasEnteredFullscreenRef.current) {
        logViolation("fullscreen_exit", { reason: "Fullscreen exited" }, 1);
      }

      // ✅ Send status to parent
      const result = {
        camera,
        screen,
        fullscreen,
        cameraStream,
        screenStream,
      };

      console.log("✅ PermissionChecker: streams prepared", { cameraStream, screenStream });
      onUpdate(result);
    };

    checkPermissions();

    return () => {
      if (window.__activeScreenStream) {
        window.__activeScreenStream.getTracks().forEach((track) => track.stop());
        window.__activeScreenStream = null;
      }
    };
  }, [onUpdate, antiCheatLevel]);

  return null;
}
