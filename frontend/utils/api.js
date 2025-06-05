export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function logViolation(type, metadata = {}, severity = 1) {
  const assignment_id = sessionStorage.getItem("assignment_id");
  if (!assignment_id) {
    console.warn("⚠️ assignment_id not found in sessionStorage.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/proctoring/log-violation/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        assignment_id: parseInt(assignment_id),
        type,
        severity,
        metadata,
      }),
    });

    if (!res.ok) {
      const errData = await res.json();
      console.warn("❌ Failed to log violation:", errData);
    } else {
      console.log(`📌 Violation '${type}' logged`);

      // 🚨 Dispatch local event so PeriodicCapture can react
      window.dispatchEvent(
        new CustomEvent("proctoringViolation", {
          detail: { type, severity, timestamp: new Date() },
        })
      );
    }
  } catch (err) {
    console.error("🚨 Error logging violation:", err);
  }
}
