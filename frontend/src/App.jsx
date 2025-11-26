import { AppLoader, TopBar, WelcomeScreen, ChatMessages, Sidebar } from './components'
import useCouncil from './hooks/useCouncil'
import './App.css'

function App() {
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
    startCouncil,
    startNewChat,
    loadSession,
    deleteSession,
    toggleSidebar,
  } = useCouncil()

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
            onSelectSession={loadSession}
            onDeleteSession={deleteSession}
            onClose={toggleSidebar}
            onNewChat={() => {
              startNewChat()
              toggleSidebar()
            }}
          />
        </>
      )}

      <TopBar
        onNewChat={startNewChat}
        onToggleSidebar={toggleSidebar}
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
    </div>
  )
}

export default App
