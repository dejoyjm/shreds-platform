import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

export default function Dashboard() {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);  // ⬅️ New
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
    } else {
      fetchMessage(token);
    }
  }, []);

  const fetchMessage = async (token) => {
    try {
      const res = await fetch('http://localhost:8000/api/hello/', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await res.json();
      setMessage(data.message);
    } catch (err) {
      console.error('Auth failed:', err);
      router.push('/login');
    } finally {
      setLoading(false);  // ⬅️ Now safe to show content
    }
  };

  if (loading) return null;  // ⬅️ Don't show anything until auth check completes

  return (
    <div className="max-w-xl mx-auto mt-20 p-6 shadow rounded bg-white">
      <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
      <p>{message}</p>

      <button
        onClick={() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          router.push('/login');
        }}
        className="mt-4 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
      >
        Logout
      </button>
    </div>
  );
}
