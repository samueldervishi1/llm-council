import ChatInput from './ChatInput'

function WelcomeScreen({ question, onQuestionChange, onSubmit, loading }) {
  return (
    <div className="welcome-screen">
      <div className="welcome-content">
        <h1>LLM Council</h1>
        <p>Ask multiple AI models and get a synthesized answer</p>
      </div>
      <ChatInput
        value={question}
        onChange={onQuestionChange}
        onSubmit={onSubmit}
        disabled={loading}
        placeholder="How can we help you today?"
        centered
      />
    </div>
  )
}

export default WelcomeScreen
