function ChatInput({ value, onChange, onSubmit, disabled, placeholder, centered = false }) {
  const handleKeyDown = (e) => {
    // Ctrl+Enter or Cmd+Enter to send
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      if (value.trim() && !disabled) {
        onSubmit()
      }
    }
    // Regular Enter creates new line (default behavior)
  }

  return (
    <div className={`input-container ${centered ? 'centered' : 'bottom'}`}>
      <div className="input-wrapper">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          autoFocus={centered}
        />
        <button onClick={onSubmit} disabled={disabled || !value.trim()} title="Send (Ctrl+Enter)">
          <span className="send-icon">↑</span>
        </button>
      </div>
      <div className="input-hints">
        <span>Ctrl+Enter to send</span>
        <span>Alt+N new chat</span>
        <span>Ctrl+\ sidebar</span>
      </div>
    </div>
  )
}

export default ChatInput
