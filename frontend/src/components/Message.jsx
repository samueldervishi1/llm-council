import ReactMarkdown from 'react-markdown'

function Message({ type, content, modelName }) {
  return (
    <div className={`message ${type}`}>
      {modelName && (
        <div className="message-header">
          <span className="model-name">{modelName}</span>
        </div>
      )}
      <div className="message-content">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  )
}

export default Message
