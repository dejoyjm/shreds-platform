import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import { useAntiCheat } from "../../utils/useAntiCheat";
import { API_BASE_URL } from "@/utils/api";

export default function StartSessionPage() {
  const router = useRouter();
  useAntiCheat();

  const [email, setEmail] = useState("acmathai@shredsindia.org");
  const [mobile, setMobile] = useState("9446571534");
  const [secret1, setSecret1] = useState("Test_Key_1");
  const [secret2, setSecret2] = useState("Test_Key_2");

  const [candidateId, setCandidateId] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [selectedTest, setSelectedTest] = useState(null);
  const [agreedToRules, setAgreedToRules] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const verifyAndProceed = async (candidate, assignment) => {
    sessionStorage.setItem("candidate_id", candidate);
    sessionStorage.setItem("assignment_id", assignment);
    sessionStorage.setItem("test_flow_started", "1");

    try {
      const check = await fetch(
        `${API_BASE_URL}/api/proctoring/check-ready/?assignment_id=${assignment}&candidate_id=${candidate}`
      );
      const text = await check.text();
      let checkRes;
      try {
        checkRes = JSON.parse(text);
      } catch (err) {
        console.error("❌ Not a JSON response", text);
        setStatusMsg("Server error during readiness check.");
        return;
      }

      console.log("🎯 Proctoring readiness response:", checkRes);

      if (!checkRes.enforce_proctoring) {
        sessionStorage.setItem("proctoring_ready", "true");
        sessionStorage.setItem("proctoring_session_done", "1");
        return;
      }

      if (!checkRes.ready) {
        sessionStorage.removeItem("proctoring_session_done");
        router.push("/test/proctoring-setup");
      } else {
        const alreadyReady = sessionStorage.getItem("proctoring_ready");
        if (!alreadyReady) {
          sessionStorage.setItem("proctoring_ready", "true");
          sessionStorage.setItem("proctoring_session_done", "1");
          router.push("/test/proctoring-session");
        }
      }
    } catch (err) {
      console.error("Check-ready failed", err);
      setStatusMsg("Error checking proctoring readiness.");
    }
  };

  const handleVerify = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/verify-secrets/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, mobile, secret1, secret2 }),
      });

      const data = await res.json();
      if (!res.ok) {
        setStatusMsg(data?.error || "Verification failed");
        return;
      }

      setCandidateId(data.candidate_id);
      setAssignments(data.assignments || []);

      sessionStorage.setItem("email", email);
      sessionStorage.setItem("mobile", mobile);
      sessionStorage.setItem("secret1", secret1);
      sessionStorage.setItem("secret2", secret2);

      if (data.assignments.length > 0) {
        const proctoringDone = sessionStorage.getItem("proctoring_session_done");
        if (proctoringDone !== "1") {
          await verifyAndProceed(data.candidate_id, data.assignments[0].assignment_id);
          return;
        }
      }

      setStatusMsg("No assignments available.");
    } catch (err) {
      console.error("Verify failed", err);
      setStatusMsg("Error verifying candidate.");
    }
  };

  useEffect(() => {
    const candidate = sessionStorage.getItem("candidate_id");
    const assignment = sessionStorage.getItem("assignment_id");
    const flowStarted = sessionStorage.getItem("test_flow_started");
    const proctoringDone = sessionStorage.getItem("proctoring_session_done");

    if (candidate && assignment && flowStarted && proctoringDone !== "1") {
      verifyAndProceed(candidate, assignment);
    }
  }, []);

  const handleStart = async () => {
    if (!selectedTest) return alert("Select a test first");
    if (!agreedToRules) return alert("Please agree to the exam rules first.");

    const ready = sessionStorage.getItem("proctoring_ready");
    if (ready !== "true") {
      alert("Proctoring not yet completed. Please finish setup.");
      return;
    }

    const now = new Date();
    const validFrom = new Date(selectedTest.valid_from);
    const validTo = new Date(selectedTest.valid_to);

    if (now < validFrom) return alert("Test has not opened yet.");
    if (now > validTo) return alert("Test window is closed.");

    sessionStorage.removeItem("violationCount");
    await document.documentElement.requestFullscreen();

    const res = await fetch(`${API_BASE_URL}/api/start-session/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate: candidateId, test: selectedTest.test_id }),
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data?.error || "Could not start session");
      return;
    }

    localStorage.setItem("sessionData", JSON.stringify({
      candidate_id: candidateId,
      test_id: selectedTest.test_id,
      session_id: data.session_id,
      section_id: data.section_id,
      section_name: data.section_name,
      attempt_number: data.attempt_number,
      section_start_time: data.section_start_time,
    }));

    localStorage.removeItem("testCompleted");
    sessionStorage.removeItem("violationCount");

    document.documentElement.requestFullscreen().catch((err) => {
      console.warn("Fullscreen failed", err);
    });

    router.push("/test/section");
  };

  return (
    <div style={{ padding: "1rem", maxWidth: "600px", margin: "0 auto" }}>
      <h2>🎓 Candidate Login</h2>

      <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} /><br />
      <input type="text" placeholder="Mobile" value={mobile} onChange={e => setMobile(e.target.value)} /><br />
      <input type="text" placeholder="Secret Code 1" value={secret1} onChange={e => setSecret1(e.target.value)} /><br />
      <input type="text" placeholder="Secret Code 2" value={secret2} onChange={e => setSecret2(e.target.value)} /><br />

      <button onClick={handleVerify}>🔐 Verify</button>

      {statusMsg && <p style={{ color: "blue" }}>{statusMsg}</p>}

      <div style={{ marginTop: "1rem" }}>
        <h4>📋 Select Available Test</h4>

        {assignments.length > 0 ? (
          <div style={{ marginTop: "1rem" }}>
            {assignments.map((test, idx) => (
              <div key={idx} style={{ border: "1px solid #ccc", marginBottom: "1rem", padding: "1rem" }}>
                <strong>{test.test_name}</strong>
                <p>Window: {new Date(test.valid_from).toLocaleString()} - {new Date(test.valid_to).toLocaleString()}</p>
                <p>Attempts: {test.attempts_used}/{test.max_attempts}</p>
                {test.can_start ? (
                  <button onClick={() => setSelectedTest(test)}>✔️ Select</button>
                ) : (
                  <span style={{ color: "gray" }}>⛔ Cannot start: {test.status}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: "gray", fontStyle: "italic", marginTop: "0.5rem" }}>
            You don&apos;t have any currently valid test assignments.<br />
            Your test window might have expired or the next one isn&apos;t open yet.<br />
            Please check back later or contact your coordinator.
          </p>
        )}
      </div>

      {selectedTest && (
        <div style={{ backgroundColor: "#fef9c3", padding: "1rem", marginTop: "1rem" }}>
          <h4>🧪 Selected Test Info</h4>
          <p>Sections: {selectedTest.sections.length}</p>
          <p>Total Questions: {selectedTest.total_questions}</p>
          <p>Window: {new Date(selectedTest.valid_from).toLocaleString()} - {new Date(selectedTest.valid_to).toLocaleString()}</p>

          <ul>
            {selectedTest.sections.map((sec, i) => (
              <li key={i}>📘 {sec.section_name} — {sec.duration_minutes} min</li>
            ))}
          </ul>

          <label>
            <input
              type="checkbox"
              checked={agreedToRules}
              onChange={e => setAgreedToRules(e.target.checked)}
            />{" "}
            I agree to the exam rules.
          </label><br />

          <button onClick={handleStart} style={{ marginTop: "0.5rem" }}>▶️ Start Test</button>
        </div>
      )}
    </div>
  );
}
