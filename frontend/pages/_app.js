// /pages/_app.js
import '../src/styles/globals.css';
import { Toaster } from 'react-hot-toast';
import { ProctoringProvider } from '@/components/ProctoringContext';

function MyApp({ Component, pageProps }) {
  return (
    <ProctoringProvider>
      <Component {...pageProps} />
      <Toaster position="top-center" />
    </ProctoringProvider>
  );
}

export default MyApp;
