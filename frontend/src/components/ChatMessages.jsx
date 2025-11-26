import { useEffect, useRef } from 'react'
import Message from './Message'
import LoadingIndicator from './LoadingIndicator'
import ChatInput from './ChatInput'

function ChatMessages({ messages, loading, currentStep, question, onQuestionChange, onSubmit }) {
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  return (
    <>
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <Message key={idx} type={msg.type} content={msg.content} modelName={msg.modelName} />
        ))}

        {loading && <LoadingIndicator statusText={currentStep} />}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        value={question}
        onChange={onQuestionChange}
        onSubmit={onSubmit}
        disabled={loading}
        placeholder="Ask the council another question..."
      />
    </>
  )
}

export default ChatMessages
