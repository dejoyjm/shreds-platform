import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { API_BASE_URL } from '../utils/api';

export default function Dashboard() {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    console.log("Token being sent:", token); // 🔍 DEBUG

    const fetchMessage = async () => {
      try {
            const res = await fetch(`${API_BASE_URL}/api/hello/`, {
              method: 'GET',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`, // ✅ Must be there
              },
            });


        const data = await res.json();

        if (res.ok) {
          setMessage(data.message);
        } else {
          setMessage('Unauthorized or error');
          router.push('/login');
        }
      } catch (err) {
        setMessage('Something went wrong');
        router.push('/login');
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchMessage();
    } else {
      router.push('/login');
    }
  }, [router]);

  if (loading) return null;

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
