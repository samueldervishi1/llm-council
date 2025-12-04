import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'

const ChatInput = forwardRef(
  ({ value, onChange, onSubmit, disabled, placeholder, centered = false }, ref) => {
    const textareaRef = useRef(null)

    // Expose focus method to parent
    useImperativeHandle(ref, () => ({
      focus: () => {
        textareaRef.current?.focus()
      },
    }))

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

    // Auto-resize textarea based on content
    useEffect(() => {
      const textarea = textareaRef.current
      if (textarea) {
        if (value === '') {
          // Reset to initial height when empty
          textarea.style.height = 'auto'
        } else {
          // Reset height to auto to get the correct scrollHeight
          textarea.style.height = 'auto'
          // Set height to scrollHeight (capped by max-height in CSS)
          textarea.style.height = `${textarea.scrollHeight}px`
        }
      }
    }, [value])

    return (
      <div className={`input-container ${centered ? 'centered' : 'bottom'}`}>
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
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
)

ChatInput.displayName = 'ChatInput'

export default ChatInput
