import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { API_BASE } from '../config/api'

function useCouncil() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState('')
  const [appLoading, setAppLoading] = useState(true)
  const [sessionId, setSessionId] = useState(null)
  const [sessions, setSessions] = useState([])
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setAppLoading(false)
    }, 2000)
    return () => clearTimeout(timer)
  }, [])

  const fetchSessions = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/sessions`)
      setSessions(res.data.sessions)
    } catch (error) {
      console.error('Error fetching sessions:', error)
    }
  }, [])

  useEffect(() => {
    if (!appLoading) {
      fetchSessions()
    }
  }, [appLoading, fetchSessions])

  const addMessage = (type, content, modelName = null) => {
    setMessages((prev) => [...prev, { type, content, modelName, timestamp: new Date() }])
  }

  // Convert a round to messages
  const roundToMessages = (round) => {
    const msgs = []

    // Build disagreement lookup by model_id
    const disagreementMap = {}
    if (round.disagreement_analysis) {
      for (const analysis of round.disagreement_analysis) {
        disagreementMap[analysis.model_id] = analysis
      }
    }

    // User question
    msgs.push({
      type: 'user',
      content: round.question,
      timestamp: new Date(),
    })

    // Council responses
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

    // Chairman's synthesis
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

  const loadSession = async (id) => {
    try {
      setLoading(true)
      setCurrentStep('Loading session...')
      const res = await axios.get(`${API_BASE}/session/${id}`)
      const session = res.data.session

      setSessionId(session.id)
      const loadedMessages = []

      // Load all rounds
      if (session.rounds && session.rounds.length > 0) {
        for (const round of session.rounds) {
          loadedMessages.push(...roundToMessages(round))
        }
      }

      setMessages(loadedMessages)
      setSidebarOpen(false)
    } catch (error) {
      console.error('Error loading session:', error)
    } finally {
      setLoading(false)
      setCurrentStep('')
    }
  }

  const deleteSession = async (id) => {
    try {
      await axios.delete(`${API_BASE}/session/${id}`)
      await fetchSessions()
      if (sessionId === id) {
        startNewChat()
      }
    } catch (error) {
      console.error('Error deleting session:', error)
    }
  }

  const shareSession = async (id) => {
    try {
      const res = await axios.post(`${API_BASE}/session/${id}/share`)
      return res.data
    } catch (error) {
      console.error('Error sharing session:', error)
      throw error
    }
  }

  const unshareSession = async (id) => {
    try {
      await axios.delete(`${API_BASE}/session/${id}/share`)
    } catch (error) {
      console.error('Error unsharing session:', error)
      throw error
    }
  }

  const getShareInfo = async (id) => {
    try {
      const res = await axios.get(`${API_BASE}/session/${id}/share-info`)
      return res.data
    } catch (error) {
      console.error('Error getting share info:', error)
      throw error
    }
  }

  const loadSharedSession = async (shareToken) => {
    try {
      setLoading(true)
      setCurrentStep('Loading shared session...')
      const res = await axios.get(`${API_BASE}/shared/${shareToken}`)
      const session = res.data.session

      const loadedMessages = []
      if (session.rounds && session.rounds.length > 0) {
        for (const round of session.rounds) {
          loadedMessages.push(...roundToMessages(round))
        }
      }

      setMessages(loadedMessages)
      setSessionId(null) // Read-only mode
      return session
    } catch (error) {
      console.error('Error loading shared session:', error)
      throw error
    } finally {
      setLoading(false)
      setCurrentStep('')
    }
  }

  const startCouncil = async () => {
    if (!question.trim()) return

    const userQuestion = question
    setQuestion('')
    setLoading(true)

    addMessage('user', userQuestion)

    try {
      let currentSessionId = sessionId

      // If we have an existing session, continue it; otherwise create new
      if (currentSessionId) {
        setCurrentStep('Continuing conversation...')
        await axios.post(`${API_BASE}/session/${currentSessionId}/continue`, {
          question: userQuestion,
        })
      } else {
        setCurrentStep('Creating session...')
        const createRes = await axios.post(`${API_BASE}/query`, { question: userQuestion })
        currentSessionId = createRes.data.session.id
        setSessionId(currentSessionId)
      }

      setCurrentStep('Council is thinking...')
      addMessage('system', 'Gathering responses from the council...')

      const responsesRes = await axios.post(`${API_BASE}/session/${currentSessionId}/responses`)
      const session = responsesRes.data.session
      const currentRound = session.rounds[session.rounds.length - 1]

      for (const resp of currentRound.responses) {
        if (resp.error) {
          addMessage('error', `Error: ${resp.error}`, resp.model_name)
        } else {
          addMessage('council', resp.response, resp.model_name)
        }
      }

      setCurrentStep('Council is reviewing...')
      await axios.post(`${API_BASE}/session/${currentSessionId}/reviews`)

      setCurrentStep('Chairman Grok is deciding...')
      addMessage('system', 'Chairman Grok is reviewing all responses...')

      const synthesisRes = await axios.post(`${API_BASE}/session/${currentSessionId}/synthesize`)
      const finalSession = synthesisRes.data.session
      const finalRound = finalSession.rounds[finalSession.rounds.length - 1]

      addMessage('chairman', finalRound.final_synthesis, 'Grok 4.1 Fast (Chairman)')

      // Refresh sessions list
      await fetchSessions()
    } catch (error) {
      console.error('Error:', error)
      addMessage('error', error.response?.data?.detail || error.message)
    } finally {
      setLoading(false)
      setCurrentStep('')
    }
  }

  const startNewChat = () => {
    setMessages([])
    setQuestion('')
    setLoading(false)
    setCurrentStep('')
    setSessionId(null)
  }

  const toggleSidebar = () => {
    setSidebarOpen((prev) => !prev)
  }

  const exportSession = async () => {
    if (!sessionId) return

    try {
      const res = await axios.get(`${API_BASE}/session/${sessionId}`)
      const session = res.data.session

      let markdown = `# LLM Council Session\n\n`
      markdown += `**Title:** ${session.title || 'Untitled'}\n\n`
      markdown += `---\n\n`

      for (let i = 0; i < session.rounds.length; i++) {
        const round = session.rounds[i]
        markdown += `## Round ${i + 1}\n\n`
        markdown += `### Question\n\n${round.question}\n\n`

        if (round.responses && round.responses.length > 0) {
          markdown += `### Council Responses\n\n`
          for (const resp of round.responses) {
            if (!resp.error) {
              markdown += `#### ${resp.model_name}\n\n${resp.response}\n\n`
            }
          }
        }

        if (round.final_synthesis) {
          markdown += `### Chairman's Synthesis\n\n${round.final_synthesis}\n\n`
        }

        markdown += `---\n\n`
      }

      markdown += `\n*Exported from LLM Council*`

      // Create and download file
      const blob = new Blob([markdown], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `llm-council-${session.title?.slice(0, 30).replace(/[^a-z0-9]/gi, '-') || sessionId}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error exporting session:', error)
    }
  }

  const hasMessages = messages.length > 0

  return {
    question,
    setQuestion,
    messages,
    loading,
    currentStep,
    appLoading,
    hasMessages,
    sessionId,
    sessions,
    sidebarOpen,
    startCouncil,
    startNewChat,
    loadSession,
    deleteSession,
    toggleSidebar,
    fetchSessions,
    shareSession,
    unshareSession,
    getShareInfo,
    loadSharedSession,
    exportSession,
  }
}

export default useCouncil
