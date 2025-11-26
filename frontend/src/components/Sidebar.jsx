function Sidebar({ sessions, currentSessionId, onSelectSession, onDeleteSession, onClose, onNewChat }) {
  const formatDate = (dateString) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    const now = new Date()
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    return date.toLocaleDateString()
  }

  const truncateQuestion = (question, maxLength = 40) => {
    if (question.length <= maxLength) return question
    return question.substring(0, maxLength) + '...'
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Chat History</h2>
        <button className="sidebar-close" onClick={onClose}>
          &times;
        </button>
      </div>

      <button className="sidebar-new-chat" onClick={onNewChat}>
        + New Chat
      </button>

      <div className="sidebar-sessions">
        {sessions.length === 0 ? (
          <p className="sidebar-empty">No chat history yet</p>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`sidebar-session ${session.id === currentSessionId ? 'active' : ''}`}
              onClick={() => onSelectSession(session.id)}
            >
              <div className="session-info">
                <span className="session-question">{truncateQuestion(session.question)}</span>
                <span className="session-date">{formatDate(session.created_at)}</span>
              </div>
              <button
                className="session-delete"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteSession(session.id)
                }}
              >
                &times;
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default Sidebar
