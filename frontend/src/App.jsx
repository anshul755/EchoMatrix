import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import { LoadingState } from './components/ui/StatePanel';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const SearchPage = lazy(() => import('./pages/SearchPage'));
const TrendsPage = lazy(() => import('./pages/TrendsPage'));
const TopicsPage = lazy(() => import('./pages/TopicsPage'));
const AboutPage = lazy(() => import('./pages/AboutPage'));

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingState label="Loading workspace..." />}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route element={<MainLayout />}>
            <Route path="search" element={<SearchPage />} />
            <Route path="trends" element={<TrendsPage />} />
            <Route path="timeseries" element={<TrendsPage />} />
            <Route path="topics" element={<TopicsPage />} />
            <Route path="about" element={<AboutPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
