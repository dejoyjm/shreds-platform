import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/utils/api";
import { useProctoring } from "@/components/ProctoringContext";

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

  // 🚨 Catch improper fallback
  useEffect(() => {
    if (!ctxBaseFrequency && !ctxViolationBoostFactor) {
      console.warn("⚠️ Default props in use — check proctoringConfig not passed via context!");
    }
  }, [ctxBaseFrequency, ctxViolationBoostFactor]);

  // 🧠 Log on first render
  useEffect(() => {
    console.log("🧩 PeriodicCapture mounted with props:", {
      baseFrequency,
      violationBoostFactor,
      screenStreamExists: !!screenStream,
      sessionToken,
    });
  }, []);

  // 🧠 Listen for violation events from elsewhere in the app
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

    const startInterval = () => {
      intervalId = setInterval(async () => {
        const currentFrequency = computeFrequency();
        console.log("🔄 Triggered interval with:", {
          baseFrequency,
          violationBoostFactor,
          violationCount,
          currentFrequency,
          timestamp: new Date().toLocaleTimeString(),
        });

        const webcam = document.querySelector("#proctoring");
        if (!webcam || !webcam.videoWidth || !webcam.videoHeight) {
          console.warn("⚠️ Webcam not ready or missing.");
          return;
        }

        // 🖼️ Face Capture
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
          }
        }, "image/jpeg");

        // 🖥️ Screen Capture
        if (!screenStream) {
          console.warn("🛑 Skipping screen capture: screenStream not provided.");
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
            }
          }, "image/jpeg");
        } catch (err) {
          console.error("🛑 Screen capture error", err);
        }
      }, adjustedFrequency * 1000);
    };

    startInterval();

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [baseFrequency, violationBoostFactor, violationCount, screenStream, sessionToken]);

  return null;
}
