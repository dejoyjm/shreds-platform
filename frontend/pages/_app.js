// pages/_app.js
import '../src/styles/globals.css'

export default function App({ Component, pageProps }) {
  return <Component {...pageProps} />
}

// frontend/pages/_app.js
import { Toaster } from 'react-hot-toast';

function MyApp({ Component, pageProps }) {
  return (
    <>
      <Component {...pageProps} />
      <Toaster position="top-center" />
    </>
  );
}

export default MyApp;

