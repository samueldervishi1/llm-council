import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import SharedSession from './pages/SharedSession.jsx'
import { ErrorBoundary } from './components'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/sessions/:sessionId" element={<App />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/shared/:shareToken" element={<SharedSession />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>
)
