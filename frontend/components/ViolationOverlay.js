import { useEffect, useState } from "react";
import { useProctoring } from "./ProctoringContext";

export default function ViolationOverlay() {
  const { violations, antiCheatLevel } = useProctoring();
  const [visible, setVisible] = useState(false);
  const [latest, setLatest] = useState(null);

  useEffect(() => {
    if (violations.length > 0) {
      const last = violations[violations.length - 1];
      setLatest(last);
      setVisible(true);

      const timeout = setTimeout(() => setVisible(false), 4000); // hide after 4s
      return () => clearTimeout(timeout);
    }
  }, [violations]);

  if (!visible || antiCheatLevel === "low") return null;

  return (
    <div style={{
      position: "fixed",
      top: "20px",
      right: "20px",
      backgroundColor: "rgba(255,0,0,0.9)",
      color: "white",
      padding: "1rem",
      borderRadius: "8px",
      zIndex: 10000,
      fontWeight: "bold",
      animation: "blink 1s linear infinite alternate"
    }}>
      ⚠️ {latest?.type?.toUpperCase() || "Violation"} Detected
    </div>
  );
}
