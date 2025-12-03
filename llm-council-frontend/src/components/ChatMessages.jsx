import { useEffect, useRef } from 'react'
import Message from './Message'
import VotingVisualization from './VotingVisualization'
import LoadingIndicator from './LoadingIndicator'
import ChatInput from './ChatInput'

function ChatMessages({
  messages,
  loading,
  currentStep,
  question,
  onQuestionChange,
  onSubmit,
  readOnly = false,
}) {
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
        {messages.map((msg, idx) => {
          if (msg.type === 'voting') {
            return (
              <VotingVisualization
                key={idx}
                peerReviews={msg.peerReviews}
                responses={msg.responses}
                disagreementAnalysis={msg.disagreementAnalysis}
              />
            )
          }
          return (
            <Message
              key={idx}
              type={msg.type}
              content={msg.content}
              modelName={msg.modelName}
              disagreement={msg.disagreement}
              replyTo={msg.replyTo}
              responseTime={msg.responseTime}
            />
          )
        })}

        {loading && <LoadingIndicator statusText={currentStep} />}

        <div ref={messagesEndRef} />
      </div>

      {!readOnly && (
        <ChatInput
          value={question}
          onChange={onQuestionChange}
          onSubmit={onSubmit}
          disabled={loading}
          placeholder="Ask the council another question..."
        />
      )}
    </>
  )
}

export default ChatMessages
