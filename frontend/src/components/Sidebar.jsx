import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Pin, Edit2, Share2, X, Search as SearchIcon, Settings as SettingsIcon } from 'lucide-react'

function Sidebar({
  sessions,
  currentSessionId,
  onDeleteSession,
  onRenameSession,
  onTogglePinSession,
  onShareSession,
  onClose,
  onNewChat,
}) {
  const [shareModal, setShareModal] = useState({ open: false, url: '', loading: false })
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const searchInputRef = useRef(null)
  const editInputRef = useRef(null)
  const location = useLocation()

  // Filter sessions based on search query
  const filteredSessions = sessions.filter((session) => {
    if (!searchQuery.trim()) return true
    const query = searchQuery.toLowerCase()
    const title = (session.title || '').toLowerCase()
    const question = (session.question || '').toLowerCase()
    return title.includes(query) || question.includes(query)
  })

  // Separate pinned and unpinned sessions
  const pinnedSessions = filteredSessions.filter((s) => s.is_pinned)
  const recentSessions = filteredSessions.filter((s) => !s.is_pinned)

  // Ctrl+F to focus search (only when sidebar is open)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault()
        e.stopPropagation()
        searchInputRef.current?.focus()
      }
      // Escape to clear search
      if (e.key === 'Escape' && searchQuery) {
        setSearchQuery('')
      }
    }
    // Use capture phase to intercept before browser
    window.addEventListener('keydown', handleKeyDown, { capture: true })
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true })
  }, [searchQuery])
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
    e.preventDefault()
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

  const startEditing = (e, session) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingId(session.id)
    setEditTitle(session.title || session.question?.substring(0, 50) || '')
    // Focus the input after render
    setTimeout(() => editInputRef.current?.focus(), 0)
  }

  const saveEdit = async (e) => {
    e?.preventDefault()
    e?.stopPropagation()
    if (editingId && editTitle.trim()) {
      await onRenameSession(editingId, editTitle.trim())
    }
    setEditingId(null)
    setEditTitle('')
  }

  const cancelEdit = (e) => {
    e?.preventDefault()
    e?.stopPropagation()
    setEditingId(null)
    setEditTitle('')
  }

  const handleEditKeyDown = (e) => {
    if (e.key === 'Enter') {
      saveEdit(e)
    } else if (e.key === 'Escape') {
      cancelEdit(e)
    }
  }

  const handlePin = async (e, sessionId) => {
    e.preventDefault()
    e.stopPropagation()
    await onTogglePinSession(sessionId)
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>
          Chat History <span className="session-count">({sessions.length})</span>
        </h2>
        <button className="sidebar-close" onClick={onClose}>
          <X size={20} />
        </button>
      </div>

      <button className="sidebar-new-chat" onClick={onNewChat}>
        + New Chat
      </button>

      <div className="sidebar-search">
        <SearchIcon size={14} />
        <input
          ref={searchInputRef}
          type="text"
          placeholder="Search chats... (Ctrl+F)"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button className="search-clear" onClick={() => setSearchQuery('')}>
            <X size={14} />
          </button>
        )}
      </div>

      <div className="sidebar-sessions">
        {filteredSessions.length === 0 ? (
          <p className="sidebar-empty">
            {searchQuery ? `No results for '${searchQuery}'` : 'No chat history yet'}
          </p>
        ) : (
          <>
            {pinnedSessions.length > 0 && (
              <>
                <div className="sidebar-section-header">
                  <Pin size={12} fill="currentColor" />
                  <span>Pinned</span>
                </div>
                {pinnedSessions.map((session) => (
                  <Link
                    key={session.id}
                    to={`/sessions/${session.id}`}
                    className={`sidebar-session ${session.id === currentSessionId ? 'active' : ''} pinned`}
                    onClick={(e) => {
                      if (editingId === session.id) {
                        e.preventDefault()
                      } else {
                        onClose()
                      }
                    }}
                  >
                    <div className="session-info">
                      {editingId === session.id ? (
                        <input
                          ref={editInputRef}
                          type="text"
                          className="session-edit-input"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={handleEditKeyDown}
                          onBlur={saveEdit}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <span className="session-question">
                          {truncateQuestion(session.title || session.question)}
                        </span>
                      )}
                      <div className="session-meta">
                        <span className="session-date">{formatDate(session.created_at)}</span>
                        {session.round_count > 1 && (
                          <span className="session-rounds">{session.round_count} rounds</span>
                        )}
                      </div>
                    </div>
                    <div className="session-actions">
                      <button
                        className="session-pin active"
                        onClick={(e) => handlePin(e, session.id)}
                        title="Unpin session"
                      >
                        <Pin size={14} fill="currentColor" />
                      </button>
                      <button
                        className="session-edit"
                        onClick={(e) => startEditing(e, session)}
                        title="Rename session"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        className="session-share"
                        onClick={(e) => handleShare(e, session.id)}
                        title="Share session"
                      >
                        <Share2 size={14} />
                      </button>
                      <button
                        className="session-delete"
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          onDeleteSession(session.id)
                        }}
                        title="Delete session"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  </Link>
                ))}
              </>
            )}

            {recentSessions.length > 0 && (
              <>
                {pinnedSessions.length > 0 && (
                  <div className="sidebar-section-header">
                    <span>Recent</span>
                  </div>
                )}
                {recentSessions.map((session) => (
                  <Link
                    key={session.id}
                    to={`/sessions/${session.id}`}
                    className={`sidebar-session ${session.id === currentSessionId ? 'active' : ''} ${session.is_pinned ? 'pinned' : ''}`}
                    onClick={(e) => {
                      if (editingId === session.id) {
                        e.preventDefault()
                      } else {
                        onClose()
                      }
                    }}
                  >
                    <div className="session-info">
                      {editingId === session.id ? (
                        <input
                          ref={editInputRef}
                          type="text"
                          className="session-edit-input"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={handleEditKeyDown}
                          onBlur={saveEdit}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <span className="session-question">
                          {session.is_pinned && (
                            <span className="pin-icon">
                              <Pin size={12} fill="currentColor" />
                            </span>
                          )}
                          {truncateQuestion(session.title || session.question)}
                        </span>
                      )}
                      <div className="session-meta">
                        <span className="session-date">{formatDate(session.created_at)}</span>
                        {session.round_count > 1 && (
                          <span className="session-rounds">{session.round_count} rounds</span>
                        )}
                      </div>
                    </div>
                    <div className="session-actions">
                      <button
                        className={`session-pin ${session.is_pinned ? 'active' : ''}`}
                        onClick={(e) => handlePin(e, session.id)}
                        title={session.is_pinned ? 'Unpin session' : 'Pin session'}
                      >
                        <Pin size={14} fill={session.is_pinned ? 'currentColor' : 'none'} />
                      </button>
                      <button
                        className="session-edit"
                        onClick={(e) => startEditing(e, session)}
                        title="Rename session"
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
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
                          e.preventDefault()
                          e.stopPropagation()
                          onDeleteSession(session.id)
                        }}
                        title="Delete session"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  </Link>
                ))}
              </>
            )}
          </>
        )}
      </div>

      <Link
        to="/settings"
        className={`sidebar-settings ${location.pathname === '/settings' ? 'active' : ''}`}
        onClick={onClose}
      >
        <SettingsIcon size={16} />
        Settings
      </Link>

      {shareModal.open && (
        <div
          className="share-modal-overlay"
          onClick={() => setShareModal({ open: false, url: '', loading: false })}
        >
          <div className="share-modal" onClick={(e) => e.stopPropagation()}>
            <div className="share-modal-header">
              <h3>Share Session</h3>
              <button onClick={() => setShareModal({ open: false, url: '', loading: false })}>
                <X size={20} />
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
