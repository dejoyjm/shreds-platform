import { useEffect, useState } from "react";
import { useRouter } from "next/router";

export default function SectionPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [sectionData, setSectionData] = useState(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(null);
  const [responses, setResponses] = useState({});
  const [autoSubmitted, setAutoSubmitted] = useState(false);
  const [showSummary, setShowSummary] = useState(false);

  const session = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("sessionData")) : null;

  const handleSubmit = async (auto = false) => {
    const saveEndpoint = "/api/save-responses/";
    const questions = sectionData.questions;
    const payload = questions.map((q) => ({
      question: q.id,
      answer: ["A", "B", "C", "D"][responses[q.id]],
    })).filter(r => r.answer !== undefined);

    try {
      const saveRes = await fetch(`http://localhost:8000${saveEndpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate: session.candidate_id,
          test: session.test_id,
          attempt_number: session.attempt_number,
          responses: payload,
          section_id: sectionData.section_id,
          section_complete: !auto,
          auto: auto
        }),
      });

      if (!saveRes.ok) {
        throw new Error(`Failed to save answers: ${saveRes.status}`);
      }

      const saveJson = await saveRes.json();

      if (saveJson.status === "completed") {
        alert("✅ Section saved and test completed.");
        router.push("/test");
        return;
      }

      const resumeRes = await fetch("http://localhost:8000/api/resume-section/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate: session.candidate_id,
          test: session.test_id,
          attempt_number: session.attempt_number,
        }),
      });

      if (!resumeRes.ok) {
        console.error("❌ Resume failed with status", resumeRes.status);
        alert("Section saved but failed to load next section.");
        router.push("/test");
        return;
      }

      const nextData = await resumeRes.json();

      if (nextData.status === "completed") {
        alert("✅ Section saved and test completed.");
        router.push("/test");
      } else {
        alert(auto ? "⏰ Time up. Section auto-submitted. Moving to next section..." : "✅ Section saved. Loading next section...");
        localStorage.setItem("sessionData", JSON.stringify({
          candidate_id: session.candidate_id,
          test_id: session.test_id,
          attempt_number: session.attempt_number,
        }));
        localStorage.removeItem("savedResponses");
        localStorage.removeItem("currentQuestionIndex");
        window.location.reload();
      }
    } catch (error) {
      console.error("❌ Submission or resume failed", error);
      alert("Something went wrong while saving or resuming. Please try again.");
    }
  };

  const handleManualSubmit = () => {
    setShowSummary(true);
  };

  const confirmSubmit = () => {
    setShowSummary(false);
    handleSubmit(false);
  };

  useEffect(() => {

    // ✅ Check if test was already completed — short-circuit if true
    if (localStorage.getItem("testCompleted") === "true") {
      console.log("🛑 Test already completed. Skipping resume.");
      alert("✅ You have already completed the test. Redirecting...");
      router.push("/test"); // or another summary page
      return;
    }

    // ✅ Restore cached responses and index if available
   const cached = localStorage.getItem("savedResponses");
    if (cached) {
      setResponses(JSON.parse(cached));
    }
    const savedIndex = localStorage.getItem("currentQuestionIndex");
    if (savedIndex) {
      setCurrentQuestionIndex(parseInt(savedIndex));
    }
  }, []);

  useEffect(() => {

    // ✅ Skip resume-section fetch if test is already completed
    if (localStorage.getItem("testCompleted") === "true") {
      console.log("🛑 Test already completed. Skipping resume fetch.");
      alert("✅ You have already completed the test. Redirecting...");
      router.push("/test"); // or another summary page
      return;
  }
    if (!session) {
      alert("No active session found");
      router.push("/test");
      return;
    }

    fetch("http://localhost:8000/api/resume-section/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate: session.candidate_id,
        test: session.test_id,
        attempt_number: session.attempt_number,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Resume failed: ${res.status}`);
        return res.json();
      })
        .then((data) => {
          if (data.status === "completed") {
            alert("✅ Section saved and test completed. You may now close this window.");
            // 🛑 Prevent infinite reload/resume
            localStorage.removeItem("sessionData");
            localStorage.removeItem("savedResponses");
            localStorage.removeItem("currentQuestionIndex");
              // Set a flag so no further resume request is made
          localStorage.setItem("testCompleted", "true");
          setLoading(false);

            //router.push("/test");
            return;
          }

          setSectionData({ ...data, questions: data.questions || [] });
          setTimeLeft(data.time_left_seconds);
          console.log("📦 Received time_left_seconds:", data.time_left_seconds);
        })


      .catch((err) => {
        console.error("Resume section failed:", err);
        alert("Something went wrong while loading section.");
        router.push("/test");
      })
      .finally(() => setLoading(false));
  }, [router]);


  useEffect(() => {
    if (timeLeft === null || autoSubmitted) return;

    if (timeLeft <= 0) {
      console.warn("⏰ Triggering auto-submit because timeLeft <= 0");
      setAutoSubmitted(true);
      handleSubmit(true);
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, autoSubmitted]);

  useEffect(() => {
    localStorage.setItem("currentQuestionIndex", currentQuestionIndex.toString());
  }, [currentQuestionIndex]);

  if (loading) return <div>Loading section...</div>;
  if (!sectionData || !Array.isArray(sectionData.questions) || sectionData.questions.length === 0)
    return <div>No questions available in this section.</div>;

  const question = sectionData.questions[currentQuestionIndex];

  const handleOptionSelect = (qId, optionIndex) => {
    const updatedResponses = {
      ...responses,
      [qId]: optionIndex,
    };
    setResponses(updatedResponses);
    localStorage.setItem("savedResponses", JSON.stringify(updatedResponses));

    fetch("http://localhost:8000/api/save-response/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate: session.candidate_id,
        test: session.test_id,
        attempt_number: session.attempt_number,
        question: qId,
        answer: ["A", "B", "C", "D"][optionIndex],
      }),
    });
  };

  return (
    <div style={{ padding: "1rem", maxWidth: "800px", margin: "0 auto" }}>
      <h2 style={{ fontSize: "20px", fontWeight: "bold" }}>
        🧪 Section: {sectionData.section_name}
      </h2>
      <p>
        ⏳ Time Left: {Math.floor(timeLeft / 60)}m {timeLeft % 60}s
      </p>
      <hr style={{ margin: "1rem 0" }} />

      <div>
        <p>
          <strong>Q{currentQuestionIndex + 1}:</strong> {question.text}
        </p>
        <ul style={{ listStyle: "none", paddingLeft: 0 }}>
          {Array.isArray(question.options) ? (
            question.options.map((opt, idx) => (
              <li key={idx} style={{ marginBottom: "0.5rem" }}>
                <label>
                  <input
                    type="radio"
                    name={`q${question.id}`}
                    value={opt}
                    checked={responses[question.id] === idx}
                    onChange={() => handleOptionSelect(question.id, idx)}
                    style={{ marginRight: "0.5rem" }}
                  />
                  <strong>{String.fromCharCode(65 + idx)}.</strong> {opt}
                </label>
              </li>
            ))
          ) : (
            <p style={{ color: "red" }}>❗ Invalid or missing options</p>
          )}
        </ul>
      </div>

      <div style={{ marginTop: "1rem" }}>
        <button
          onClick={() => setCurrentQuestionIndex((i) => Math.max(0, i - 1))}
          disabled={currentQuestionIndex === 0}
        >
          ⬅️ Previous
        </button>

        <button
          onClick={() =>
            setCurrentQuestionIndex((i) =>
              Math.min(sectionData.questions.length - 1, i + 1)
            )
          }
          style={{ marginLeft: "1rem" }}
          disabled={currentQuestionIndex === sectionData.questions.length - 1}
        >
          Next ➡️
        </button>
      </div>

      <div style={{ marginTop: "2rem" }}>
        <button
          onClick={handleManualSubmit}
          style={{ backgroundColor: "#10b981", color: "white", padding: "0.5rem 1rem", border: "none", borderRadius: "4px" }}
        >
          ✅ Submit Section
        </button>
      </div>

      {showSummary && (
        <div style={{ marginTop: "2rem", border: "1px solid #ccc", padding: "1rem", backgroundColor: "#f9f9f9" }}>
          <h3>🧾 Section Summary</h3>
          <p>✅ Answered: {Object.keys(responses).length}</p>
          <p>❓ Unanswered: {sectionData.questions.length - Object.keys(responses).length}</p>
          <p>⏳ Time Left: {Math.floor(timeLeft / 60)}m {timeLeft % 60}s</p>
          <p style={{ color: "red" }}>⚠️ You will not be able to return to this section after submission.</p>
          <button onClick={confirmSubmit} style={{ marginTop: "1rem", backgroundColor: "#ef4444", color: "white", padding: "0.5rem 1rem", border: "none", borderRadius: "4px" }}>
            ✅ Confirm Submit Section
          </button>
        </div>
      )}
    </div>
  );
}
