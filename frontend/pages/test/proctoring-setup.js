// /pages/test/proctoring-setup.js

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import { API_BASE_URL } from "@/utils/api";

export default function ProctoringSetup() {
  const router = useRouter();
  const [config, setConfig] = useState(null);
  const [agreed, setAgreed] = useState(false);
  const [facePreview, setFacePreview] = useState(null);
  const [faceWebcamOn, setFaceWebcamOn] = useState(false);
  const faceVideoRef = useRef(null);
  const [idPreview, setIdPreview] = useState(null);
  const [idWebcamOn, setIdWebcamOn] = useState(false);
  const idVideoRef = useRef(null);
  const [idType, setIdType] = useState("");
  const [signaturePreview, setSignaturePreview] = useState(null);
  const [signatureWebcamOn, setSignatureWebcamOn] = useState(false);
  const signatureVideoRef = useRef(null);
  const canvasRef = useRef(null);
  const [status, setStatus] = useState("");

  let candidate_id = null;
  let assignment_id = null;

  if (typeof window !== "undefined") {
    candidate_id = sessionStorage.getItem("candidate_id");
    assignment_id = sessionStorage.getItem("assignment_id");
  }

  useEffect(() => {
    const fetchConfig = async () => {
      if (!assignment_id || !candidate_id) {
        toast.error("Missing session info. Cannot fetch proctoring setup.");
        console.log("➡️ Routing to /test/");
        router.push("/test");
        return;
      }

      try {
        const res = await fetch(`${API_BASE_URL}/api/proctoring/check-ready/?assignment_id=${assignment_id}&candidate_id=${candidate_id}`);
        if (!res.ok) {
          throw new Error("Failed to fetch proctoring config");
        }

        console.log("📍 candidate_id", candidate_id);
        console.log("📍 assignment_id", assignment_id);

        const data = await res.json();
        console.log("📡 FULL proctoring check-ready response:", data);

        if (!data?.enforce_proctoring) {
          console.warn("⚠️ Proctoring not required. Skipping setup.");
          sessionStorage.setItem("proctoring_ready", "true");
          sessionStorage.setItem("proctoring_session_done", "1");
          router.push("/test/section");
          return;
        }

        setConfig({
          ...data.requirements,
          enforce_proctoring: data.enforce_proctoring,
          require_face_photo: data.requirements.require_face_photo_initial,
          require_id_photo: data.requirements.require_id_photo_initial,
          require_signature_photo: data.requirements.require_signature_photo_initial,
        });

        console.log("📡 Proctoring config:", {
          enforce: data.enforce_proctoring,
          ready: data.ready,
          missing: data.missing,
          config: data.requirements
        });

      } catch (err) {
        console.error("❌ Proctoring setup failed:", err);
        toast.error("Could not load proctoring config. Please retry or contact support.");
        console.log("➡️ Routing to /test");

        router.push("/test");
      }
    };

    fetchConfig();
  }, []);

  if (!config) return <p>⏳ Loading proctoring setup...</p>;
  if (!config.enforce_proctoring) return <p>✅ Proctoring not required.</p>;


  const stopWebcam = (videoRef) => {
    const stream = videoRef.current?.srcObject;
    stream?.getTracks().forEach(track => track.stop());
    videoRef.current.srcObject = null;
  };

  const startWebcam = (videoRef) => {
    navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    });
  };

  const capturePhoto = (videoRef, setPreview, stopCamCallback) => {
    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg");
    setPreview(dataUrl);
    stopCamCallback();
  };

  const uploadImage = async (blobOrFile, type, subtype = null) => {
    const blob = blobOrFile instanceof File ? blobOrFile : await (await fetch(blobOrFile)).blob();
    const formData = new FormData();
    formData.append("candidate_id", candidate_id);
    formData.append("assignment_id", assignment_id);
    formData.append("photo_type", type);
    formData.append("image", blob);
    formData.append("context", "initial");
    if (subtype) formData.append("id_document_type", subtype);

    const res = await fetch(`${API_BASE_URL}/api/proctoring/upload-photo/`, {
      method: "POST",
      body: formData,
    });
    const result = await res.json();
    console.log("📸 Uploaded", result);
  };

  const handleSubmit = async () => {
    console.log("📝 Submitting consent with:", {
          agreed,
          facePreview,
          idPreview,
          signaturePreview
        });

    if (config.require_face_photo && !facePreview && !config.allow_file_upload) return alert("Face photo required");
    if (config.allowed_id_documents?.length > 0 && !idPreview && !config.allow_file_upload) return alert("ID photo required");
    if (config.require_signature_photo && !signaturePreview && !config.allow_file_upload) return alert("Signature required");
    if (config.consent_text && !agreed) return alert("Consent required");

    const consentRes = await fetch(`${API_BASE_URL}/api/proctoring/submit-consent/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_id, assignment_id, agreed }),
    });
    if (!consentRes.ok) {
      alert("Failed to submit consent");
      return;
    }

    if (facePreview && !facePreview.startsWith("blob:")) await uploadImage(facePreview, "face");
    if (idPreview && !idPreview.startsWith("blob:")) await uploadImage(idPreview, "id", idType);
    if (signaturePreview && !signaturePreview.startsWith("blob:")) await uploadImage(signaturePreview, "signature");
    console.log("➡️ Routing to /test/proctoring-session");
    router.push("/test/proctoring-session");
  };

  if (!config) return <p>Loading...</p>;

  return (
    <div style={{ padding: "1rem", maxWidth: "600px", margin: "0 auto" }}>
      <h2>📋 Candidate Onboarding</h2>

      {config.consent_text && (
        <div style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
          <div dangerouslySetInnerHTML={{ __html: config.consent_text }} />
          <label>
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} /> I agree to the above terms and consent to be monitored during the test.
          </label>
        </div>
      )}

      <canvas ref={canvasRef} style={{ display: "none" }} />

      {config.require_face_photo && (
        <div style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
          <h4>📸 Face Photo</h4>
          {!faceWebcamOn && !facePreview && <button onClick={() => { startWebcam(faceVideoRef); setFaceWebcamOn(true); }}>🎥 Start Webcam</button>}
          {faceWebcamOn && <video ref={faceVideoRef} style={{ width: "100%", marginBottom: "0.5rem" }} />}
          {!facePreview && faceWebcamOn && <button onClick={() => capturePhoto(faceVideoRef, setFacePreview, () => { stopWebcam(faceVideoRef); setFaceWebcamOn(false); })}>📷 Capture</button>}
          {facePreview && (
            <>
              <img src={facePreview} alt="Face Preview" style={{ width: "100%", marginTop: "0.5rem" }} />
              <button onClick={() => setFacePreview(null)}>🔁 Retake</button>
            </>
          )}
          {config.allow_file_upload && !facePreview && <input type="file" accept="image/*" onChange={e => uploadImage(e.target.files[0], "face")} />}
        </div>
      )}

      {config.allowed_id_documents?.length > 0 && (
        <div style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
          <h4>🪪 ID Document</h4>
          <select value={idType} onChange={e => setIdType(e.target.value)}>
            <option value="">Select ID Type</option>
            {config.allowed_id_documents.map(doc => (
              <option key={doc.id} value={doc.id}>{doc.name}</option>
            ))}
          </select>
          {!idWebcamOn && !idPreview && <button onClick={() => { startWebcam(idVideoRef); setIdWebcamOn(true); }}>🎥 Start Webcam</button>}
          {idWebcamOn && <video ref={idVideoRef} style={{ width: "100%", marginBottom: "0.5rem" }} />}
          {!idPreview && idWebcamOn && <button onClick={() => capturePhoto(idVideoRef, setIdPreview, () => { stopWebcam(idVideoRef); setIdWebcamOn(false); })} disabled={!idType}>📷 Capture</button>}
          {idPreview && (
            <>
              <img src={idPreview} alt="ID Preview" style={{ width: "100%", marginTop: "0.5rem" }} />
              <button onClick={() => setIdPreview(null)}>🔁 Retake</button>
            </>
          )}
          {config.allow_file_upload && !idPreview && (
            <input
              type="file"
              accept="image/*"
              onChange={e => uploadImage(e.target.files[0], "id", idType)}
              disabled={!idType}
            />
          )}
        </div>
      )}

      {config.require_signature_photo && (
        <div style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
          <h4>✍️ Signature</h4>
          {!signatureWebcamOn && !signaturePreview && <button onClick={() => { startWebcam(signatureVideoRef); setSignatureWebcamOn(true); }}>🎥 Start Webcam</button>}
          {signatureWebcamOn && <video ref={signatureVideoRef} style={{ width: "100%", marginBottom: "0.5rem" }} />}
          {!signaturePreview && signatureWebcamOn && <button onClick={() => capturePhoto(signatureVideoRef, setSignaturePreview, () => { stopWebcam(signatureVideoRef); setSignatureWebcamOn(false); })}>📷 Capture</button>}
          {signaturePreview && (
            <>
              <img src={signaturePreview} alt="Signature Preview" style={{ width: "100%", marginTop: "0.5rem" }} />
              <button onClick={() => setSignaturePreview(null)}>🔁 Retake</button>
            </>
          )}
          {config.allow_file_upload && !signaturePreview && <input type="file" accept="image/*" onChange={e => uploadImage(e.target.files[0], "signature")} />}
        </div>
      )}

      <button onClick={handleSubmit} style={{ marginTop: "1rem" }}>🚀 Submit and Proceed</button>
      <p style={{ color: "blue" }}>{status}</p>
    </div>
  );
}
