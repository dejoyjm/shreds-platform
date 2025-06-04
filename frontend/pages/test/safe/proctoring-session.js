// /pages/test/proctoring-session.js

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import { API_BASE_URL } from "@/utils/api";

export default function ProctoringSession() {
  const router = useRouter();
  const webcamPinnedRef = useRef(null);
  const [status, setStatus] = useState("");

  const candidate_id = sessionStorage.getItem("candidate_id");
  const assignment_id = sessionStorage.getItem("assignment_id");

  const screenStreamRef = useRef(null);

  useEffect(() => {
      if (!window.__proctoringStarted) {
        window.__proctoringStarted = true;

        if (!candidate_id || !assignment_id) {
          alert("Missing candidate or assignment ID");
          router.push("/test");
          return;
        }

        if (sessionStorage.getItem("screen_share_rejected")) {
          sessionStorage.removeItem("screen_share_rejected");
          router.push("/test/proctoring-setup");
          return;
        }

        // ✅ Check persistent flag
        if (sessionStorage.getItem("screen_share_done") === "1") {
          console.log("✅ Screen share previously completed. Skipping prompt.");
          setStatus("✅ Screen already shared. Continuing...");
          return;
        }

        console.log("📺 Initiating proctoring...");
        startProctoring();
      }
  }, []);

  useEffect(() => {
    if (status) {
      const timeout = setTimeout(() => setStatus(""), 5000);
      return () => clearTimeout(timeout);
    }
  }, [status]);

  const startProctoring = async () => {
    if (screenStreamRef.current) {
      console.warn("Screen stream already active, skipping.");
      return;
    }

    try {
      setStatus("🔍 Requesting screen share...");

      const screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: "monitor",
          logicalSurface: true,
          cursor: "always",
        },
      });

      screenStreamRef.current = screenStream;
      console.log("🎥 screenStream settings:", screenStream.getVideoTracks()[0].getSettings());

      const surface = screenStream.getVideoTracks()[0].getSettings().displaySurface;
      if (surface !== "monitor") {
        alert("❌ You must share your ENTIRE SCREEN (not a window/tab). Please try again.");
        screenStream.getTracks().forEach(track => track.stop());
        return;
      }

      const webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });

      if (!webcamPinnedRef.current) {
        const webcam = document.createElement("video");
        webcam.autoplay = true;
        webcam.muted = true;
        webcam.style.position = "fixed";
        webcam.style.bottom = "10px";
        webcam.style.left = "10px";
        webcam.style.width = "120px";
        webcam.style.height = "90px";
        webcam.style.border = "2px solid #ccc";
        webcam.style.zIndex = 9999;
        document.body.appendChild(webcam);
        webcam.srcObject = webcamStream;
        webcamPinnedRef.current = webcam;
      }

      const screenVideo = document.createElement("video");
      screenVideo.style.display = "none";
      document.body.appendChild(screenVideo);
      screenVideo.srcObject = screenStream;
      await screenVideo.play();

      const webcamVideo = document.createElement("video");
      webcamVideo.style.display = "none";
      document.body.appendChild(webcamVideo);
      webcamVideo.srcObject = webcamStream;
      console.log("📸 webcamStream settings:", webcamStream.getVideoTracks()[0].getSettings());
      await webcamVideo.play();

      setInterval(() => {
        const screenCanvas = document.createElement("canvas");
        screenCanvas.width = screenVideo.videoWidth;
        screenCanvas.height = screenVideo.videoHeight;
        screenCanvas.getContext("2d").drawImage(screenVideo, 0, 0);
        screenCanvas.toBlob((blob) => {
          const file = new File([blob], "screen.jpg", { type: "image/jpeg" });
          upload(file, "screen", null, "periodic");
        });

        const faceCanvas = document.createElement("canvas");
        faceCanvas.width = webcamVideo.videoWidth;
        faceCanvas.height = webcamVideo.videoHeight;
        faceCanvas.getContext("2d").drawImage(webcamVideo, 0, 0);
        faceCanvas.toBlob((blob) => {
          const file = new File([blob], "face.jpg", { type: "image/jpeg" });
          upload(file, "face", null, "periodic");
        });
      }, 60000);

      setInterval(() => {
        if (!webcamStream.active || !screenStream.active) {
          alert("⚠️ Camera or screen sharing was lost. Test will be terminated.");
          router.push("/test/terminated");
        }
      }, 30000);

      screenStream.getVideoTracks()[0].onended = () => {
        alert("⚠️ Screen sharing stopped. Test will be terminated.");
        router.push("/test/terminated");
      };

      setStatus("✅ Proctoring live. Redirecting to test...");
      sessionStorage.setItem("proctoring_ready", "true");
      console.log("✅ Permissions granted. Setting proctoring_ready = true");
      sessionStorage.setItem("screen_share_done", "1");
      sessionStorage.setItem("proctoring_session_done", "1");
      sessionStorage.setItem("test_flow_started", "1");

      setTimeout(() => router.push("/test"), 1000);
    } catch (err) {
      console.error(err);
      sessionStorage.setItem("screen_share_rejected", "1");
      alert("Camera and screen share are required to proceed.");
      router.push("/test/proctoring-setup");
    }
  };

  const upload = async (file, type, idDocTypeId = null, context = "initial") => {
    const formData = new FormData();
    formData.append("candidate_id", candidate_id);
    formData.append("assignment_id", assignment_id);
    formData.append("photo_type", type);
    formData.append("image", file);
    formData.append("context", context);
    if (type === "id" && idDocTypeId) {
      formData.append("id_document_type", idDocTypeId);
    }
    await fetch(`${API_BASE_URL}/api/proctoring/upload-photo/`, {
      method: "POST",
      body: formData,
    });
  };

  return (
    <div style={{ padding: "1rem", maxWidth: "600px", margin: "0 auto" }}>
      <h2>🎥 Proctoring Session Start</h2>
      <p style={{ fontSize: "0.9rem" }}>{status}</p>
    </div>
  );
}
