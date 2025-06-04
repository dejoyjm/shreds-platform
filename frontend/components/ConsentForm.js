// /components/ConsentForm.js
export default function ConsentForm({ consentText, agreed, setAgreed }) {
  return (
    <div className="mb-4">
      <p className="text-sm mb-2">{consentText}</p>
      <label className="flex items-center space-x-2">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
        />
        <span>I agree to the terms above</span>
      </label>
    </div>
  );
}