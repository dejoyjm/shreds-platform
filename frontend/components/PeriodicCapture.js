import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/utils/api";
import { useProctoring } from "@/components/ProctoringContext";
import { logViolation } from "@/utils/api";

export default function PeriodicCapture({
  sessionToken,
  candidateId,
  assignmentId,
  screenStream,
  baseFrequency: propBaseFrequency = 60,
  violationBoostFactor: propViolationBoostFactor = 1.0,
}) {
  const [violationCount, setViolationCount] = useState(0);
  const {
    baseFrequency: ctxBaseFrequency,
    violationBoostFactor: ctxViolationBoostFactor,
  } = useProctoring() || {};

  const baseFrequency = ctxBaseFrequency || propBaseFrequency;
  const violationBoostFactor = ctxViolationBoostFactor || propViolationBoostFactor;

  useEffect(() => {
    if (!ctxBaseFrequency && !ctxViolationBoostFactor) {
      console.warn("⚠️ Default props in use — check proctoringConfig not passed via context!");
    }
  }, [ctxBaseFrequency, ctxViolationBoostFactor]);

  useEffect(() => {
    console.log("🧩 PeriodicCapture mounted with props:", {
      baseFrequency,
      violationBoostFactor,
      screenStreamExists: !!screenStream,
      sessionToken,
    });
  }, []);

  useEffect(() => {
    const onViolation = (e) => {
      console.warn("🚨 Violation triggered:", e.detail);
      setViolationCount((prev) => prev + 1);
    };
    window.addEventListener("proctoringViolation", onViolation);
    return () => window.removeEventListener("proctoringViolation", onViolation);
  }, []);

  useEffect(() => {
    const computeFrequency = () => {
      return Math.max(
        10,
        Math.floor(baseFrequency / Math.max(1, Math.pow(violationBoostFactor, violationCount)))
      );
    };

    const adjustedFrequency = computeFrequency();
    console.log("📏 Computed adjustedFrequency:", {
      baseFrequency,
      violationBoostFactor,
      violationCount,
      adjustedFrequency,
    });

    let intervalId = null;

    const handleFocusLoss = () => {
      logViolation("tab_switch", { reason: "Tab or window lost focus" }, 2);
    };

    const handleKeydown = (e) => {
      if (e.key === "Tab" || e.ctrlKey || e.altKey || e.metaKey) {
        logViolation("keyboard_activity", { key: e.key, reason: "Prohibited key pressed" }, 2);
      }
    };

    const handleContextMenu = (e) => {
      e.preventDefault();
      logViolation("right_click", { reason: "Right click detected" }, 2);
    };

    window.addEventListener("blur", handleFocusLoss);
    window.addEventListener("keydown", handleKeydown);
    window.addEventListener("contextmenu", handleContextMenu);

    const startInterval = () => {
      intervalId = setInterval(async () => {
        if (!document.fullscreenElement) {
          logViolation("fullscreen_exit", { reason: "Fullscreen exited during test" }, 1);
        }

        const screenTrack = screenStream?.getTracks?.()[0];
        const screenLive = !!screenTrack && screenTrack.readyState === "live";

        // Always try to upload, but mark screen_ok = false if stream is lost
        if (!screenLive) {
          logViolation("screen_lost", { reason: "Screen stream not active or stopped" }, 3);

          try {
            await fetch(`${API_BASE_URL}/api/proctoring/update-heartbeat/`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                assignment_id: assignmentId,
                screen_ok: false,
                reason: "stream_stopped_or_inactive",
                session_token: sessionToken || "",
              }),
            });
            console.log("🔴 Updated screen_ok = false in heartbeat");
          } catch (err) {
            console.error("❌ Failed to update heartbeat for screen lost", err);
          }
        }


        const webcam = document.querySelector("#proctoring");

        if (!webcam || !webcam.videoWidth || !webcam.videoHeight) {
          console.warn("⚠️ Webcam not ready or missing.");
          logViolation("camera_lost", { reason: "Webcam not accessible in DOM" }, 2);
          return;
        }

        try {
          const canvasFace = document.createElement("canvas");
          canvasFace.width = webcam.videoWidth;
          canvasFace.height = webcam.videoHeight;
          const ctxFace = canvasFace.getContext("2d");
          ctxFace.drawImage(webcam, 0, 0);

          canvasFace.toBlob(async (blob) => {
            if (!blob) return;
            const file = new File([blob], "face.jpg", { type: "image/jpeg" });

            const formData = new FormData();
            formData.append("candidate_id", parseInt(candidateId || "0"));
            formData.append("assignment_id", parseInt(assignmentId || "0"));
            formData.append("photo_type", "face");
            formData.append("context", "periodic");
            if (sessionToken) formData.append("session_token", sessionToken);
            formData.append("image", file);

            try {
              const res = await fetch(`${API_BASE_URL}/api/proctoring/upload-photo/`, {
                method: "POST",
                body: formData,
              });
              const json = await res.json();
              console.log("✅ Face uploaded", json);
            } catch (err) {
              console.error("🔴 Face upload failed", err);
              logViolation("camera_capture_failed", { error: err.message }, 2);
            }
          }, "image/jpeg");
        } catch (err) {
          console.error("🧨 Error during face capture", err);
          logViolation("camera_capture_failed", { error: err.message }, 2);
        }

        if (!screenStream) {
          console.warn("🛑 Skipping screen capture: screenStream not provided.");
          logViolation("screen_lost", { reason: "screenStream null during periodic check" }, 3);
          return;
        }

        try {
          const videoTrack = screenStream.getVideoTracks()[0];
          const imageCapture = new ImageCapture(videoTrack);
          const bitmap = await imageCapture.grabFrame();

          const canvasScreen = document.createElement("canvas");
          canvasScreen.width = bitmap.width;
          canvasScreen.height = bitmap.height;
          const ctxScreen = canvasScreen.getContext("2d");
          ctxScreen.drawImage(bitmap, 0, 0);

          canvasScreen.toBlob(async (blob) => {
            if (!blob) return;
            const file = new File([blob], "screen.jpg", { type: "image/jpeg" });

            const formData = new FormData();
            formData.append("candidate_id", candidateId);
            formData.append("assignment_id", assignmentId);
            formData.append("photo_type", "screen");
            formData.append("context", "periodic");
            if (sessionToken) formData.append("session_token", sessionToken);
            formData.append("image", file);

            try {
              const res = await fetch(`${API_BASE_URL}/api/proctoring/upload-photo/`, {
                method: "POST",
                body: formData,
              });
              const json = await res.json();
              console.log("✅ Screen uploaded", json);
            } catch (err) {
              console.error("🔴 Screen upload failed", err);
              logViolation("screen_capture_failed", { error: err.message }, 3);
            }
          }, "image/jpeg");
        } catch (err) {
          console.error("🛑 Screen capture error", err);
          logViolation("screen_capture_failed", { error: err.message }, 3);
        }
      }, adjustedFrequency * 1000);
    };

    startInterval();

    return () => {
      if (intervalId) clearInterval(intervalId);
      window.removeEventListener("blur", handleFocusLoss);
      window.removeEventListener("keydown", handleKeydown);
      window.removeEventListener("contextmenu", handleContextMenu);
    };
  }, [baseFrequency, violationBoostFactor, violationCount, screenStream, sessionToken]);

  return null;
}
