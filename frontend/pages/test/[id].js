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

  if (error) return <p className="text-red-500 p-6">{error}</p>;
  if (!testData) return <p className="p-6">Loading test...</p>;

    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="border-b pb-4 mb-6">
          <h1 className="text-3xl font-bold text-gray-800">{testData.test.name}</h1>
          <p className="text-gray-600 mt-2">{testData.test.description}</p>
        </div>

        <form className="space-y-6">
          {testData.questions.map((q, index) => {
            const options = Array.isArray(q.options)
              ? q.options
              : JSON.parse(q.options || "[]");

            return (
              <div key={q.id} className="p-4 border rounded shadow-sm">
                <p className="font-medium mb-3 text-gray-800">
                  {index + 1}. {q.text}
                </p>
                <div className="space-y-1">
                  {options.map((opt, idx) => (
                    <label key={idx} className="block text-gray-700">
                      <input
                        type="radio"
                        name={`q-${q.id}`}
                        value={opt}
                        checked={answers[q.id] === opt}
                        onChange={() => handleSelect(q.id, opt)}
                        className="mr-2"
                      />
                      {opt}
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </form>

        {!submitted ? (
          <button
            onClick={handleSubmit}
            className="mt-6 bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition"
          >
            Submit Test
          </button>
        ) : (
          <div className="mt-6 p-4 bg-green-100 border border-green-400 rounded">
            <p className="text-green-800 font-semibold">
              Test Submitted! Your score: {score} / {testData.questions.length}
            </p>
          </div>
        )}
      </div>
    );

}
