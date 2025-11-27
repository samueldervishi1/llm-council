import ReactMarkdown from 'react-markdown'

function Message({ type, content, modelName, disagreement }) {
  const hasDisagreement = disagreement?.has_disagreement
  const disagreementScore = disagreement?.disagreement_score

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
        </div>
      )}
      <div className="message-content">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  )
}

export default Message
