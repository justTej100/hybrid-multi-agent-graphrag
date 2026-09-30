import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import AdminPage from './pages/AdminPage';
import FlashcardsPage from './pages/FlashcardsPage';
import GraphPage from './pages/GraphPage';
import HomePage from './pages/HomePage';
import LibraryPage from './pages/LibraryPage';
import LoginPage from './pages/LoginPage';
import QuizPage from './pages/QuizPage';
import StudyPage from './pages/StudyPage';

function screen(page: ReactNode) {
  return (
    <ProtectedRoute>
      <Layout>{page}</Layout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={screen(<HomePage />)} />
      <Route path="/library" element={screen(<LibraryPage />)} />
      <Route path="/study" element={screen(<StudyPage />)} />
      <Route path="/quiz" element={screen(<QuizPage />)} />
      <Route path="/flashcards" element={screen(<FlashcardsPage />)} />
      <Route path="/graph" element={screen(<GraphPage />)} />
      <Route path="/admin" element={screen(<AdminPage />)} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
