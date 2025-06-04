// /components/PhotoCapture.js
import { useRef, useState } from "react";

export default function PhotoCapture({ onCapture, label }) {
  const videoRef = useRef(null);
  const [imageData, setImageData] = useState(null);

  const capture = () => {
    const canvas = document.createElement("canvas");
    const video = videoRef.current;
    if (!video) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg");
    setImageData(dataUrl);
    onCapture(dataUrl);
  };

  return (
    <div className="mb-4">
      <p>{label}</p>
      {imageData ? (
        <img src={imageData} alt="Captured" className="mb-2" />
      ) : (
        <video ref={videoRef} autoPlay playsInline width={320} height={240} />
      )}
      <div className="space-x-2">
        <button onClick={capture} className="px-2 py-1 bg-blue-500 text-white rounded">
          Capture
        </button>
        <button onClick={() => setImageData(null)} className="px-2 py-1 bg-gray-300 rounded">
          Retake
        </button>
      </div>
    </div>
  );
}