import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { LoadingState } from './components/ui/StatePanel';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const AboutPage = lazy(() => import('./pages/AboutPage'));

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingState label="Loading workspace..." />}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="about" element={<AboutPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
