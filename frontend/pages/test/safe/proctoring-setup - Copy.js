// FULLY REWRITTEN VERSION – updated to use per-section webcam preview and capture flow

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/router";
import { API_BASE_URL } from "@/utils/api";

export default function ProctoringSetup() {
  const router = useRouter();
  const [consentText, setConsentText] = useState("");
  const [requireIDPhoto, setRequireIDPhoto] = useState(false);
  const [allowedIDDocs, setAllowedIDDocs] = useState([]);
  const [requireFace, setRequireFace] = useState(false);
  const [requireSignature, setRequireSignature] = useState(false);
  const [allowFileUpload, setAllowFileUpload] = useState(true);
  const [agreed, setAgreed] = useState(false);
  const [facePreview, setFacePreview] = useState(null);
  const [idPreview, setIdPreview] = useState(null);
  const [signaturePreview, setSignaturePreview] = useState(null);
  const [idType, setIdType] = useState("");
  const [status, setStatus] = useState("");


  const faceVideoRef = useRef(null);
  const idVideoRef = useRef(null);
  const signatureVideoRef = useRef(null);
  const canvasRef = useRef(null);
  const webcamPinnedRef = useRef(null);

  const [faceWebcamOn, setFaceWebcamOn] = useState(false);
  const [idWebcamOn, setIdWebcamOn] = useState(false);
  const [signatureWebcamOn, setSignatureWebcamOn] = useState(false);

    const [candidate_id, setCandidateId] = useState(null);
    const [assignment_id, setAssignmentId] = useState(null);

    useEffect(() => {
      if (typeof window !== "undefined") {
        const cid = sessionStorage.getItem("candidate_id");
        const aid = sessionStorage.getItem("assignment_id");
        setCandidateId(cid);
        setAssignmentId(aid);
      }
    }, []);

    useEffect(() => {
      if (!candidate_id || !assignment_id) return;

      fetch(`${API_BASE_URL}/api/proctoring/check-ready/?assignment_id=${assignment_id}&candidate_id=${candidate_id}`)
        .then(async res => {
          const text = await res.text();
          try {
            const data = JSON.parse(text);
            const requirements = data.requirements || {};

            setConsentText(requirements.consent_text || "");
            setRequireFace(requirements.require_face_photo_initial || false);
            setRequireSignature(requirements.require_signature_photo_initial || false);
            setRequireIDPhoto(requirements.require_id_photo_initial || false);
            setAllowedIDDocs(requirements.allowed_id_documents || []);
            setAllowFileUpload(requirements.allow_file_upload_fallback ?? true);
          } catch (e) {
            console.error("❌ Not valid JSON", text);
            throw new Error("Invalid JSON");
          }
        })
        .catch(err => {
          console.error("Error fetching proctoring config", err);
          setStatus("❌ Failed to fetch proctoring config");
        });
    }, [candidate_id, assignment_id]);




  const startWebcam = async (ref) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (ref.current) {
        ref.current.srcObject = stream;
        ref.current.play();
      }
    } catch (err) {
      console.error("Webcam access denied", err);
    }
  };

  const capturePhoto = (ref, setPreview) => {
    const canvas = canvasRef.current;
    const video = ref.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const imageUrl = canvas.toDataURL("image/jpeg");
    setPreview(imageUrl);
  };

  const confirmUpload = async (type, idDocType = null, clearPreview) => {
    canvasRef.current.toBlob(async (blob) => {
      const file = new File([blob], `${type}.jpg`, { type: "image/jpeg" });
      await upload(file, type, idDocType);
      let ref;
      let setWebcamOn;
      if (type === "face") {
        ref = faceVideoRef;
        setWebcamOn = setFaceWebcamOn;
      } else if (type === "id") {
        ref = idVideoRef;
        setWebcamOn = setIdWebcamOn;
      } else if (type === "signature") {
        ref = signatureVideoRef;
        setWebcamOn = setSignatureWebcamOn;
      }

      if (ref?.current?.srcObject) {
        ref.current.srcObject.getTracks().forEach(track => track.stop());
        ref.current.srcObject = null;
        setWebcamOn(false);
      }
    });
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
    const res = await fetch(`${API_BASE_URL}/api/proctoring/upload-photo/`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error || "Upload failed");
  };

  const startScreenAndPeriodicCapture = async (screenStream) => {
    try {
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

// 🪄 Attempt to auto-hide Chrome's screen-sharing banner (note: may be blocked by browser security)
try {
  const tracks = screenStream.getVideoTracks();
  tracks.forEach(track => {
    if (typeof track.applyConstraints === "function") {
      track.applyConstraints({ advanced: [{ displaySurface: "monitor" }] });
    }
  });
} catch (e) {
  console.warn("Auto-hide constraints not supported", e);
}

await screenVideo.play();

      const webcamVideo = document.createElement("video");
      webcamVideo.style.display = "none";
      document.body.appendChild(webcamVideo);
      webcamVideo.srcObject = webcamStream;
      await webcamVideo.play();

      const interval = setInterval(() => {
        const canvas = document.createElement("canvas");
        canvas.width = screenVideo.videoWidth;
        canvas.height = screenVideo.videoHeight;
        canvas.getContext("2d").drawImage(screenVideo, 0, 0);
        canvas.toBlob(blob => {
          const file = new File([blob], "screen.jpg", { type: "image/jpeg" });
          upload(file, "screen", null, "periodic");
        });

        const faceCanvas = document.createElement("canvas");
        faceCanvas.width = webcamVideo.videoWidth;
        faceCanvas.height = webcamVideo.videoHeight;
        faceCanvas.getContext("2d").drawImage(webcamVideo, 0, 0);
        faceCanvas.toBlob(blob => {
          const faceFile = new File([blob], "face.jpg", { type: "image/jpeg" });
          upload(faceFile, "face", null, "periodic");
        });
      }, 60000);

      screenStream.getVideoTracks()[0].onended = () => {
        clearInterval(interval);
        alert("⚠️ Screen sharing was stopped. Test will be terminated.");
        router.push("/test/terminated");
      };
    } catch (err) {
      console.error("Failed to start screen/webcam", err);
      alert("Camera and screen sharing required to proceed.");
    }
  };

  const handleSubmit = async () => {
    try {
      if (!agreed) {
        setStatus("⚠️ You must agree to the terms");
        return;
      }
      setStatus("🔍 Checking screen share permissions...");

      const screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: "monitor",
          logicalSurface: true,
          cursor: "always"
        }
      });
      const displaySurface = screenStream.getVideoTracks()[0].getSettings().displaySurface;
      if (displaySurface !== "monitor") {
        alert("❌ You must share your ENTIRE SCREEN (not just a tab or window). Please try again.");
        screenStream.getTracks().forEach(track => track.stop());
        return;
      }

      setStatus("📩 Submitting consent...");
      const res = await fetch(`${API_BASE_URL}/api/proctoring/submit-consent/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assignment_id, candidate_id, agreed: true }),
      });
      if (res.status === 409) {
        console.warn("Consent already exists, continuing...");
      }

      await startScreenAndPeriodicCapture(screenStream);

      setStatus("✅ All set! Redirecting...");
      router.push("/test");
    } catch (err) {
      console.error(err);
      setStatus("❌ Error during submission");
    }
  };

  return (
    <div style={{ padding: "1rem", maxWidth: "600px", margin: "0 auto" }}>
      <h2>📋 Candidate Onboarding</h2>
      <div style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
      <div dangerouslySetInnerHTML={{ __html: consentText }} />


      <label>
        <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} /> I agree to the above terms and consent to be monitored during the test.
      </label>
      </div>
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {requireFace && (
        <div style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
          <h4>📸 Face Photo</h4>
          {!faceWebcamOn && <button onClick={() => { startWebcam(faceVideoRef); setFaceWebcamOn(true); }}>🎥 Start Webcam</button>}
          {faceWebcamOn && <video ref={faceVideoRef} style={{ width: "100%", marginBottom: "0.5rem" }} />}
          {!facePreview && faceWebcamOn && <button onClick={() => capturePhoto(faceVideoRef, setFacePreview)}>📷 Capture</button>}
          {facePreview && (
            <>
              <img src={facePreview} alt="Face Preview" style={{ width: "100%", marginTop: "0.5rem" }} />
              <button onClick={() => confirmUpload("face", null, setFacePreview)}>✅ Confirm</button>
              <button onClick={() => setFacePreview(null)}>🔁 Retake</button>
            </>
          )}
          {allowFileUpload && !facePreview && <input type="file" accept="image/*" onChange={e => upload(e.target.files[0], "face")} />}
        </div>
      )}

      {allowedIDDocs.length > 0 && (
        <div style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
          <h4>🪪 ID Document</h4>
          <select value={idType} onChange={e => setIdType(e.target.value)}>
            <option value="">Select ID Type</option>
            {allowedIDDocs.map(doc => (
              <option key={doc.id} value={doc.id}>{doc.name}</option>
            ))}
          </select>
          {!idWebcamOn && <button onClick={() => { startWebcam(idVideoRef); setIdWebcamOn(true); }}>🎥 Start Webcam</button>}
          {idWebcamOn && <video ref={idVideoRef} style={{ width: "100%", marginBottom: "0.5rem" }} />}
          {!idPreview && idWebcamOn && <button onClick={() => capturePhoto(idVideoRef, setIdPreview)} disabled={!idType}>📷 Capture</button>}
          {idPreview && (
            <>
              <img src={idPreview} alt="ID Preview" style={{ width: "100%", marginTop: "0.5rem" }} />
              <button onClick={() => confirmUpload("id", idType, setIdPreview)}>✅ Confirm</button>
              <button onClick={() => setIdPreview(null)}>🔁 Retake</button>
            </>
          )}
          {allowFileUpload && !idPreview && <input type="file" accept="image/*" onChange={e => upload(e.target.files[0], "id", idType)} />}
        </div>
      )}

      {requireSignature && (
        <div style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
          <h4>✍️ Signature</h4>
          {!signatureWebcamOn && <button onClick={() => { startWebcam(signatureVideoRef); setSignatureWebcamOn(true); }}>🎥 Start Webcam</button>}
          {signatureWebcamOn && <video ref={signatureVideoRef} style={{ width: "100%", marginBottom: "0.5rem" }} />}
          {!signaturePreview && signatureWebcamOn && <button onClick={() => capturePhoto(signatureVideoRef, setSignaturePreview)}>📷 Capture</button>}
          {signaturePreview && (
            <>
              <img src={signaturePreview} alt="Signature Preview" style={{ width: "100%", marginTop: "0.5rem" }} />
              <button onClick={() => confirmUpload("signature", null, setSignaturePreview)}>✅ Confirm</button>
              <button onClick={() => setSignaturePreview(null)}>🔁 Retake</button>
            </>
          )}
          {allowFileUpload && !signaturePreview && <input type="file" accept="image/*" onChange={e => upload(e.target.files[0], "signature")} />}
        </div>
      )}

      <button onClick={handleSubmit} style={{ marginTop: "1rem" }}>🚀 Submit and Proceed</button>
      <p style={{ color: "blue" }}>{status}</p>
    </div>
  );
}
