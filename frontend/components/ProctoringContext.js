import { createContext, useContext, useState } from "react";

const ProctoringContext = createContext();

export function ProctoringProvider({ children }) {
  const [screenStream, setScreenStream] = useState(null);
  const [cameraStream, setCameraStream] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [violations, setViolations] = useState([]);
  const [antiCheatLevel, setAntiCheatLevel] = useState("low");

  // 🆕 Frequency settings for periodic capture
  const [baseFrequency, setBaseFrequency] = useState(30); // default 30 seconds
  const [violationBoostFactor, setViolationBoostFactor] = useState(2); // default multiplier

  const reportViolation = (type, details = null) => {
    setViolations((prev) => [...prev, { type, details, timestamp: Date.now() }]);
    console.warn("⚠️ Violation recorded:", { type, details });
  };

  return (
    <ProctoringContext.Provider
      value={{
        screenStream,
        setScreenStream,
        cameraStream,
        setCameraStream,
        sessionToken,
        setSessionToken,
        antiCheatLevel,
        setAntiCheatLevel,
        violations,
        reportViolation,
        baseFrequency,
        setBaseFrequency,
        violationBoostFactor,
        setViolationBoostFactor,
      }}
    >
      {children}
    </ProctoringContext.Provider>
  );
}

export function useProctoring() {
  const context = useContext(ProctoringContext);
  if (!context) {
    throw new Error("useProctoring must be used within a ProctoringProvider");
  }
  return context;
}
