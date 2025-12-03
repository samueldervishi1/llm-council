import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'

// Color palette for different models
const MODEL_COLORS = {
  'NVIDIA Nemotron 9B': '#76b900',
  'NVIDIA: Nemotron Nano 12B 2 VL': '#76b900',
  'Gemma 3 27B': '#4285f4',
  'GPT OSS 20B': '#10a37f',
  'Grok 4.1 Fast': '#a78bfa',
  'Grok 4.1 Fast (Chairman)': '#a78bfa',
}

function getModelColor(modelName) {
  return MODEL_COLORS[modelName] || '#d4a574'
}

function formatResponseTime(ms) {
  if (!ms) return null
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function Message({ type, content, modelName, disagreement, replyTo, responseTime }) {
  const [copied, setCopied] = useState(false)
  const hasDisagreement = disagreement?.has_disagreement
  const disagreementScore = disagreement?.disagreement_score
  const formattedTime = formatResponseTime(responseTime)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  // Only show copy for model responses
  const showCopy = ['council', 'chairman', 'chat'].includes(type)

  // Chat mode styling
  if (type === 'chat') {
    const color = getModelColor(modelName)
    return (
      <div className="message chat">
        <div className="chat-bubble">
          <div className="chat-header" style={{ color }}>
            <span className="chat-model-name">{modelName}</span>
            {replyTo && <span className="chat-reply-to">replying to @{replyTo}</span>}
            {formattedTime && <span className="response-time">{formattedTime}</span>}
            <button className="copy-btn" onClick={handleCopy} title="Copy response">
              {copied ? (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
            </button>
          </div>
          <div className="chat-content">
            <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>
          </div>
        </div>
        <div className="chat-avatar" style={{ backgroundColor: color }}>
          {modelName?.charAt(0) || 'A'}
        </div>
      </div>
    )
  }

  // Default styling for other message types
  return (
    <div className={`message ${type} ${hasDisagreement ? 'has-disagreement' : ''}`}>
      {modelName && (
        <div className="message-header">
          <span className="model-name">{modelName}</span>
          {hasDisagreement && (
            <span
              className="disagreement-badge"
              title={`Disagreement score: ${(disagreementScore * 100).toFixed(0)}%`}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              Disputed
            </span>
          )}
          {formattedTime && <span className="response-time">{formattedTime}</span>}
          {showCopy && (
            <button className="copy-btn" onClick={handleCopy} title="Copy response">
              {copied ? (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
            </button>
          )}
        </div>
      )}
      <div className="message-content">
        <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>
      </div>
    </div>
  )
}

export default Message
