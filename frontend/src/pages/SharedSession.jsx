import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { API_BASE, FRONTEND_VERSION } from '../config/api'
import { ChatMessages } from '../components'
import '../App.css'

function SharedSession() {
  const { shareToken } = useParams()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sessionTitle, setSessionTitle] = useState('')

  // Convert a round to messages (same as useCouncil)
  const roundToMessages = (round) => {
    const msgs = []

    // Build disagreement lookup by model_id
    const disagreementMap = {}
    if (round.disagreement_analysis) {
      for (const analysis of round.disagreement_analysis) {
        disagreementMap[analysis.model_id] = analysis
      }
    }

    msgs.push({
      type: 'user',
      content: round.question,
      timestamp: new Date(),
    })

    if (round.responses && round.responses.length > 0) {
      msgs.push({
        type: 'system',
        content: 'Gathering responses from the council...',
        timestamp: new Date(),
      })

      for (const resp of round.responses) {
        if (resp.error) {
          msgs.push({
            type: 'error',
            content: `Error: ${resp.error}`,
            modelName: resp.model_name,
            timestamp: new Date(),
          })
        } else {
          msgs.push({
            type: 'council',
            content: resp.response,
            modelName: resp.model_name,
            timestamp: new Date(),
            disagreement: disagreementMap[resp.model_id] || null,
          })
        }
      }

      // Add voting visualization after responses if we have peer reviews
      if (round.peer_reviews && round.peer_reviews.length > 0) {
        msgs.push({
          type: 'voting',
          peerReviews: round.peer_reviews,
          responses: round.responses,
          disagreementAnalysis: round.disagreement_analysis,
          timestamp: new Date(),
        })
      }
    }

    if (round.final_synthesis) {
      msgs.push({
        type: 'system',
        content: 'Chairman Grok is reviewing all responses...',
        timestamp: new Date(),
      })
      msgs.push({
        type: 'chairman',
        content: round.final_synthesis,
        modelName: 'Grok 4.1 Fast (Chairman)',
        timestamp: new Date(),
      })
    }

    return msgs
  }

  useEffect(() => {
    const loadSharedSession = async () => {
      try {
        setLoading(true)
        const res = await axios.get(`${API_BASE}/shared/${shareToken}`)
        const session = res.data.session

        setSessionTitle(session.title || 'Shared Session')

        const loadedMessages = []
        if (session.rounds && session.rounds.length > 0) {
          for (const round of session.rounds) {
            loadedMessages.push(...roundToMessages(round))
          }
        }

        setMessages(loadedMessages)
      } catch (err) {
        console.error('Error loading shared session:', err)
        setError('This shared session is not available or has been revoked.')
      } finally {
        setLoading(false)
      }
    }

    loadSharedSession()
  }, [shareToken])

  if (loading) {
    return (
      <div className="app-loader">
        <h1>LLM Council</h1>
        <div className="loader-spinner"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="shared-error">
        <h1>Session Not Found</h1>
        <p>{error}</p>
        <Link to="/" className="shared-home-link">
          Go to LLM Council
        </Link>
      </div>
    )
  }

  return (
    <div className="chat-app shared-view">
      <div className="top-bar shared-top-bar">
        <div className="shared-badge">
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
          Shared Session
        </div>
        <Link to="/" className="new-chat-btn">
          Open LLM Council
        </Link>
      </div>

      <ChatMessages
        messages={messages}
        loading={false}
        currentStep=""
        question=""
        onQuestionChange={() => {}}
        onSubmit={() => {}}
        readOnly={true}
      />

      <div className="shared-footer">
        <span>v{FRONTEND_VERSION}</span>
        <span>|</span>
        <a href="https://llm-council-docs.netlify.app/" target="_blank" rel="noopener noreferrer">
          Documentation
        </a>
      </div>
    </div>
  )
}

export default SharedSession
