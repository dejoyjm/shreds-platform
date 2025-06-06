import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import { API_BASE_URL } from "@/utils/api";
import PermissionChecker from "@/components/PermissionChecker";
import PeriodicCapture from "@/components/PeriodicCapture";
import { useProctoring } from "@/components/ProctoringContext";

export default function ProctoringSession() {
  const router = useRouter();
  const webcamPinnedRef = useRef(null);
  const [screenStream, setScreenStreamState] = useState(null);
  const [proctoringConfig, setProctoringConfig] = useState(null);
  const [status, setStatus] = useState("Initializing proctoring...");
  const [sessionToken, setSessionToken] = useState(null);
  const [proceeding, setProceeding] = useState(false);
  const [flags, setFlags] = useState({ camera: false, screen: false, fullscreen: false });
  const [sessionReady, setSessionReady] = useState(false);
  const [startCheck, setStartCheck] = useState(false);
  const hasHandledRef = useRef(false);
  const permissionRef = useRef(null); // ✅ THIS FIXES YOUR ERROR


  const {
    setCameraStream,
    setScreenStream,
    setSessionToken: setCtxSessionToken,
    setBaseFrequency,
    setViolationBoostFactor,
  } = useProctoring();

  let candidate_id = null;
  let assignment_id = null;

  if (typeof window !== "undefined") {
    candidate_id = sessionStorage.getItem("candidate_id");
    assignment_id = sessionStorage.getItem("assignment_id");
  }

  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = sessionStorage.getItem("proctoring_session_token");
    if (token) {
      setSessionToken(token);
      setCtxSessionToken(token);
      setSessionReady(true);
      setStatus("Proctoring session resumed.");
    } else if (candidate_id && assignment_id) {
      fetch(`${API_BASE_URL}/api/proctoring/start-session/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_id, assignment_id }),
      })
        .then(res => res.json())
        .then(data => {
          if (data.session_token) {
            sessionStorage.setItem("proctoring_session_token", data.session_token);
            setSessionToken(data.session_token);
            setCtxSessionToken(data.session_token);
            setSessionReady(true);
            setStatus("Proctoring session started.");
          } else {
            console.error("❌ Failed to retrieve session token:", data);
            setStatus("Failed to initialize session.");
          }
        })
        .catch(err => {
          console.error("🔴 Error fetching session token:", err);
          setStatus("Failed to initialize session.");
        });
    }
  }, []);

  useEffect(() => {
    const fetchConfig = async () => {
      if (!candidate_id || !assignment_id) return;
      try {
        const res = await fetch(`${API_BASE_URL}/api/proctoring/check-ready/?assignment_id=${assignment_id}&candidate_id=${candidate_id}`);
        const data = await res.json();
        console.log("📡 Proctoring config received", data);
        if (!data?.enforce_proctoring) {
          if (typeof window !== "undefined") {
            sessionStorage.setItem("proctoring_ready", "true");
            sessionStorage.setItem("proctoring_session_done", "1");
          }
          router.push("/test");
          return;
        }
        setProctoringConfig(data.requirements || {});
        const freq = Number(data?.requirements?.periodic_screen_capture_sec || 60);
        const boost = Number(data?.requirements?.violation_boost_factor || 1);
        setBaseFrequency(freq);
        setViolationBoostFactor(boost);
        console.log("🧠 Context set from proctoring-session:", { freq, boost });
      } catch (err) {
        console.error("❌ Failed to fetch proctoring config", err);
      }
    };
    fetchConfig();
  }, []);

  const sendStatusUpdate = async (flagsToSend) => {
    if (!sessionToken) return;
    try {
      await fetch(`${API_BASE_URL}/api/proctoring/update-session-status/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_token: sessionToken,
          camera_streaming_ok: flagsToSend.camera,
          screen_sharing_ok: flagsToSend.screen,
          fullscreen_mode: flagsToSend.fullscreen,
        }),
      });
    } catch (err) {
      console.warn("🔴 Failed to update status", err);
    }
  };

  const handlePermissionCheck = async (newFlags) => {
    if (hasHandledRef.current) return;
    hasHandledRef.current = true;

    const { camera, screen, fullscreen, cameraStream, screenStream } = newFlags;
    setFlags({ camera, screen, fullscreen });
    sendStatusUpdate({ camera, screen, fullscreen });

    if (cameraStream && webcamPinnedRef.current === null) {
      const webcam = document.createElement("video");
      webcam.id = "proctoring";
      webcam.autoplay = true;
      webcam.muted = true;
      webcam.srcObject = cameraStream;
      webcam.style.position = "fixed";
      webcam.style.bottom = "10px";
      webcam.style.left = "10px";
      webcam.style.width = "120px";
      webcam.style.height = "90px";
      webcam.style.border = "2px solid #ccc";
      webcam.style.zIndex = 9999;
      document.body.appendChild(webcam);
      webcamPinnedRef.current = webcam;
    }

    if (cameraStream) setCameraStream(cameraStream);
    if (screenStream) {
      setScreenStream(screenStream);
      setScreenStreamState(screenStream);
    }
  };

  useEffect(() => {
    if (!sessionToken) return;
    const interval = setInterval(() => {
      const fullscreen = document.fullscreenElement !== null;
      sendStatusUpdate({ camera: true, screen: true, fullscreen });
    }, 15000);
    return () => clearInterval(interval);
  }, [sessionToken]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (flags.camera && flags.screen && sessionToken && !proceeding) {
      if (sessionStorage.getItem("redirected_to_test")) return;
      sessionStorage.setItem("redirected_to_test", "1");
      setProceeding(true);
      setStatus("✅ All checks passed. Redirecting to test...");
      sessionStorage.setItem("proctoring_ready", "true");
      sessionStorage.setItem("proctoring_session_done", "1");
      router.push("/test");
    }
  }, [flags, sessionToken, proceeding]);

  if (!proctoringConfig) return <p>Loading proctoring setup...</p>;

  return (
    <div style={{ padding: "1rem", maxWidth: "600px", margin: "0 auto" }}>
      <h2>🎥 Proctoring Session Running</h2>
      <p className="text-sm text-gray-600">{status}</p>
      <p style={{ fontSize: "0.75rem", color: "#666" }}>Session Token: {sessionToken}</p>

    {sessionReady && proctoringConfig && sessionToken && (
      <button
        onClick={() => {
          if (permissionRef.current) {
            permissionRef.current.checkPermissions();
          }
        }}
        style={{ marginTop: "1rem", padding: "0.75rem 1.5rem", backgroundColor: "#10b981", color: "white", border: "none", borderRadius: "6px" }}
      >
        ✅ Start Proctoring Checks
      </button>
    )}

    <PermissionChecker ref={permissionRef} onUpdate={handlePermissionCheck} />


      {screenStream &&
        proctoringConfig?.periodic_screen_capture_sec &&
        proctoringConfig?.violation_boost_factor && (
          <PeriodicCapture
            sessionToken={sessionToken}
            candidateId={candidate_id}
            assignmentId={assignment_id}
            screenStream={screenStream}
          />
        )}
    </div>
  );
}
