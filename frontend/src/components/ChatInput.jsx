function ChatInput({ value, onChange, onSubmit, disabled, placeholder, centered = false }) {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className={`input-container ${centered ? 'centered' : 'bottom'}`}>
      <div className="input-wrapper">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          autoFocus={centered}
        />
        <button onClick={onSubmit} disabled={disabled || !value.trim()}>
          <span className="send-icon">↑</span>
        </button>
      </div>
    </div>
  )
}

export default ChatInput
