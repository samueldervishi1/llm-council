import { useState } from 'react'
import { FRONTEND_VERSION } from '../config/api'

function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
  onShareSession,
  onClose,
  onNewChat,
}) {
  const [shareModal, setShareModal] = useState({ open: false, url: '', loading: false })
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
    if (!question) return 'Empty session'
    if (question.length <= maxLength) return question
    return question.substring(0, maxLength) + '...'
  }

  const handleShare = async (e, sessionId) => {
    e.stopPropagation()
    setShareModal({ open: true, url: '', loading: true })
    try {
      const data = await onShareSession(sessionId)
      // Build frontend share URL
      const frontendUrl = `${window.location.origin}/shared/${data.share_token}`
      setShareModal({ open: true, url: frontendUrl, loading: false })
    } catch (error) {
      setShareModal({ open: false, url: '', loading: false })
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(shareModal.url)
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
                <span className="session-question">
                  {truncateQuestion(session.title || session.question)}
                </span>
                <div className="session-meta">
                  <span className="session-date">{formatDate(session.created_at)}</span>
                  {session.round_count > 1 && (
                    <span className="session-rounds">{session.round_count} rounds</span>
                  )}
                </div>
              </div>
              <div className="session-actions">
                <button
                  className="session-share"
                  onClick={(e) => handleShare(e, session.id)}
                  title="Share session"
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                    <polyline points="16 6 12 2 8 6" />
                    <line x1="12" y1="2" x2="12" y2="15" />
                  </svg>
                </button>
                <button
                  className="session-delete"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteSession(session.id)
                  }}
                  title="Delete session"
                >
                  &times;
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <a
        href="https://llm-council-docs.netlify.app/"
        target="_blank"
        rel="noopener noreferrer"
        className="sidebar-version"
      >
        v{FRONTEND_VERSION}
      </a>

      {shareModal.open && (
        <div
          className="share-modal-overlay"
          onClick={() => setShareModal({ open: false, url: '', loading: false })}
        >
          <div className="share-modal" onClick={(e) => e.stopPropagation()}>
            <div className="share-modal-header">
              <h3>Share Session</h3>
              <button onClick={() => setShareModal({ open: false, url: '', loading: false })}>
                &times;
              </button>
            </div>
            <div className="share-modal-content">
              {shareModal.loading ? (
                <p>Generating share link...</p>
              ) : (
                <>
                  <p>Anyone with this link can view this session:</p>
                  <div className="share-url-container">
                    <input type="text" value={shareModal.url} readOnly />
                    <button onClick={copyToClipboard}>Copy</button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Sidebar
