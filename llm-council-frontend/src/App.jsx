import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  AppLoader,
  TopBar,
  WelcomeScreen,
  ChatMessages,
  Sidebar,
  CommandPalette,
} from './components'
import useCouncil from './hooks/useCouncil'
import useTheme from './hooks/useTheme'
import './App.css'

function App() {
  const { sessionId: urlSessionId } = useParams()
  const navigate = useNavigate()
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
  const {
    question,
    setQuestion,
    messages,
    loading,
    currentStep,
    appLoading,
    hasMessages,
    sessionId,
    sessions,
    sidebarOpen,
    mode,
    setMode,
    availableModels,
    selectedModels,
    toggleModel,
    selectAllModels,
    startCouncil,
    startNewChat,
    loadSession,
    deleteSession,
    renameSession,
    togglePinSession,
    toggleSidebar,
    shareSession,
    exportSession,
  } = useCouncil()

  const { theme, toggleTheme } = useTheme()

  // Handle new chat navigation
  const handleNewChat = () => {
    startNewChat()
    navigate('/')
  }

  // Load session from URL if present
  useEffect(() => {
    if (urlSessionId && urlSessionId !== sessionId && !appLoading) {
      loadSession(urlSessionId)
    }
  }, [urlSessionId, appLoading])

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl+K or Cmd+K for command palette
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen(true)
        return
      }
      // Ctrl+/ or Cmd+/ for command palette (alternative)
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault()
        setIsCommandPaletteOpen(true)
        return
      }
      // Alt+N for new chat
      if (e.altKey && e.key === 'n') {
        e.preventDefault()
        handleNewChat()
        return
      }
      // Ctrl+\ or Cmd+\ for toggle sidebar (like VS Code)
      if ((e.ctrlKey || e.metaKey) && e.key === '\\') {
        e.preventDefault()
        toggleSidebar()
      }
      // Alt+S as alternative for sidebar
      if (e.altKey && e.key === 's') {
        e.preventDefault()
        toggleSidebar()
      }
    }
    // Use capture phase to ensure we get the event before browser
    window.addEventListener('keydown', handleKeyDown, { capture: true })
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true })
  }, [handleNewChat, toggleSidebar])

  if (appLoading) {
    return <AppLoader />
  }

  return (
    <div className="chat-app">
      {sidebarOpen && (
        <>
          <div className="sidebar-overlay" onClick={toggleSidebar} />
          <Sidebar
            sessions={sessions}
            currentSessionId={sessionId}
            onDeleteSession={deleteSession}
            onRenameSession={renameSession}
            onTogglePinSession={togglePinSession}
            onShareSession={shareSession}
            onClose={toggleSidebar}
            onNewChat={() => {
              handleNewChat()
              toggleSidebar()
            }}
          />
        </>
      )}

      <TopBar
        onNewChat={handleNewChat}
        onToggleSidebar={toggleSidebar}
        sessionId={sessionId}
        onShare={shareSession}
        onExport={exportSession}
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      {!hasMessages ? (
        <WelcomeScreen
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={startCouncil}
          loading={loading}
        />
      ) : (
        <ChatMessages
          messages={messages}
          loading={loading}
          currentStep={currentStep}
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={startCouncil}
        />
      )}

      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        sessions={sessions}
        onNewChat={handleNewChat}
        onExport={exportSession}
        currentSessionId={sessionId}
      />
    </div>
  )
}

export default App
