import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

export default function TakeTest() {
  const router = useRouter();
  const { id } = router.query;
  const [testData, setTestData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [score, setScore] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (id) {
      axios
        .get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/test/${id}/`)
        .then((res) => setTestData(res.data))
        .catch((err) => {
          console.error("Error fetching test:", err);
          setError("Could not load test.");
        });
    }
  }, [id]);

  const handleSelect = (questionId, value) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = async () => {
    try {
      const payload = {
        test_id: parseInt(id),
        candidate: {
          name: "John Doe",
          email: "johndoe@example.com",
        },
        responses: Object.entries(answers).map(([qid, ans]) => ({
          question_id: parseInt(qid),
          answer: ans,
        })),
      };

      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/submit/`,
        payload
      );
      setScore(res.data.report.score);
      setSubmitted(true);
    } catch (err) {
      console.error("Error submitting test:", err);
      setError("Submission failed. Please try again.");
    }
  };

  if (error) return <p style={{ color: 'red', padding: '1rem' }}>{error}</p>;
  if (!testData) return <p style={{ padding: '1rem' }}>Loading test...</p>;

  return (
    <div style={{ padding: '1rem', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ borderBottom: '1px solid #ccc', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.8rem', margin: 0 }}>{testData.test.name}</h1>
        <p style={{ color: '#555' }}>{testData.test.description}</p>
      </div>

      <form>
        {testData.questions.map((q, index) => {
          const options = Array.isArray(q.options)
            ? q.options
            : JSON.parse(q.options || "[]");

          return (
            <div
              key={q.id}
              style={{
                padding: '1rem',
                border: '1px solid #ddd',
                borderRadius: '6px',
                marginBottom: '1.5rem',
                boxShadow: '0 1px 4px rgba(0, 0, 0, 0.06)',
              }}
            >
              <p style={{ fontWeight: 'bold' }}>
                {index + 1}. {q.text}
              </p>
              {options.map((opt, idx) => (
                <label key={idx} style={{ display: 'block', margin: '0.5rem 0' }}>
                  <input
                    type="radio"
                    name={`q-${q.id}`}
                    value={opt}
                    checked={answers[q.id] === opt}
                    onChange={() => handleSelect(q.id, opt)}
                    style={{ marginRight: '0.5rem' }}
                  />
                  {opt}
                </label>
              ))}
            </div>
          );
        })}
      </form>

      {!submitted ? (
        <button
          onClick={handleSubmit}
          type="button"
          style={{
            padding: '0.6rem 1.5rem',
            backgroundColor: '#0070f3',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Submit Test
        </button>
      ) : (
        <div
          style={{
            marginTop: '1.5rem',
            padding: '1rem',
            backgroundColor: '#e6ffed',
            border: '1px solid #b2f5ea',
            borderRadius: '6px',
          }}
        >
          <p style={{ color: '#276749', fontWeight: 'bold' }}>
            Test Submitted! Your score: {score} / {testData.questions.length}
          </p>
        </div>
      )}
    </div>
  );
}
