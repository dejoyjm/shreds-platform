import { useImperativeHandle, forwardRef, useRef } from "react";
import { logViolation } from "@/utils/api";

/**
 * Checks webcam, screen, and fullscreen permissions,
 * and returns media streams and statuses to parent.
 *
 * Usage: wrap with `forwardRef` and call `ref.current.checkPermissions()` from parent
 */
const PermissionChecker = forwardRef(({ onUpdate, antiCheatLevel = "low" }, ref) => {
  const hasEnteredFullscreenRef = useRef(false);

  useImperativeHandle(ref, () => ({
    checkPermissions,
  }));

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
      screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: "monitor",
          logicalSurface: true,
          cursor: "always",
        },
      });
      window.__activeScreenStream = screenStream;
      if (screenStream) screen = true;
    } catch (err) {
      console.warn("🚫 Screen permission denied", err);
      if (antiCheatLevel === "high") {
        console.error("🚨 Screen share required at high antiCheatLevel");
      }
    }

    fullscreen = document.fullscreenElement !== null;
    if (fullscreen) {
      hasEnteredFullscreenRef.current = true;
    }

    // 🧠 Log violations
    if (!camera) {
      logViolation("camera_lost", { reason: "Camera stream missing" }, 2);
    }
    if (!screen) {
      logViolation("screen_lost", { reason: "Screen share stopped" }, 3);
    }
    if (!fullscreen && hasEnteredFullscreenRef.current) {
      logViolation("fullscreen_exit", { reason: "Fullscreen exited" }, 1);
    }

    const result = {
      camera,
      screen,
      fullscreen,
      cameraStream,
      screenStream,
    };

    console.log("✅ PermissionChecker: streams prepared", result);
    onUpdate(result);
  };

  return null;
});

export default PermissionChecker;
PermissionChecker.displayName = "PermissionChecker";