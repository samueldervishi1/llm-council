import { useState } from 'react'

function TopBar({ onNewChat, onToggleSidebar, sessionId, onShare, onExport }) {
  const [shareModal, setShareModal] = useState({ open: false, url: '', loading: false })
  const [copied, setCopied] = useState(false)

  const handleShare = async () => {
    if (!sessionId || !onShare) return
    setShareModal({ open: true, url: '', loading: true })
    try {
      const data = await onShare(sessionId)
      const frontendUrl = `${window.location.origin}/shared/${data.share_token}`
      setShareModal({ open: true, url: frontendUrl, loading: false })
    } catch (error) {
      setShareModal({ open: false, url: '', loading: false })
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(shareModal.url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExport = () => {
    if (onExport) onExport()
  }

  return (
    <>
      <div className="top-bar">
        <div className="top-bar-left">
          <button className="menu-btn" onClick={onToggleSidebar}>
            &#9776;
          </button>
          <button className="new-chat-btn" onClick={onNewChat}>
            + New Chat
          </button>
        </div>

        {sessionId && (
          <div className="top-bar-right">
            <button className="top-bar-action" onClick={handleExport} title="Export to Markdown">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export
            </button>
            <button className="top-bar-action" onClick={handleShare} title="Share session">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                <polyline points="16 6 12 2 8 6" />
                <line x1="12" y1="2" x2="12" y2="15" />
              </svg>
              Share
            </button>
          </div>
        )}
      </div>

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
                    <button onClick={copyToClipboard}>{copied ? 'Copied!' : 'Copy'}</button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default TopBar
