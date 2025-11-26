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

  const loadSession = async (id) => {
    try {
      setLoading(true)
      setCurrentStep('Loading session...')
      const res = await axios.get(`${API_BASE}/session/${id}`)
      const session = res.data.session

      setSessionId(session.id)
      const loadedMessages = []

      // Add the original question as user message
      loadedMessages.push({
        type: 'user',
        content: session.question,
        timestamp: new Date()
      })

      // Add council responses
      if (session.responses && session.responses.length > 0) {
        loadedMessages.push({
          type: 'system',
          content: 'Gathering responses from the council...',
          timestamp: new Date()
        })

        for (const resp of session.responses) {
          if (resp.error) {
            loadedMessages.push({
              type: 'error',
              content: `Error: ${resp.error}`,
              modelName: resp.model_name,
              timestamp: new Date()
            })
          } else {
            loadedMessages.push({
              type: 'council',
              content: resp.response,
              modelName: resp.model_name,
              timestamp: new Date()
            })
          }
        }
      }

      // Add chairman's synthesis
      if (session.final_synthesis) {
        loadedMessages.push({
          type: 'system',
          content: 'Chairman Grok is reviewing all responses...',
          timestamp: new Date()
        })
        loadedMessages.push({
          type: 'chairman',
          content: session.final_synthesis,
          modelName: 'Grok 4.1 Fast (Chairman)',
          timestamp: new Date()
        })
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

  const startCouncil = async () => {
    if (!question.trim()) return

    const userQuestion = question
    setQuestion('')
    setLoading(true)

    addMessage('user', userQuestion)

    try {
      setCurrentStep('Creating session...')
      const createRes = await axios.post(`${API_BASE}/query`, { question: userQuestion })
      const newSessionId = createRes.data.session.id
      setSessionId(newSessionId)

      setCurrentStep('Council is thinking...')
      addMessage('system', 'Gathering responses from the council...')

      const responsesRes = await axios.post(`${API_BASE}/session/${newSessionId}/responses`)
      const responses = responsesRes.data.session.responses

      for (const resp of responses) {
        if (resp.error) {
          addMessage('error', `Error: ${resp.error}`, resp.model_name)
        } else {
          addMessage('council', resp.response, resp.model_name)
        }
      }

      setCurrentStep('Council is reviewing...')
      await axios.post(`${API_BASE}/session/${newSessionId}/reviews`)

      setCurrentStep('Chairman Grok is deciding...')
      addMessage('system', 'Chairman Grok is reviewing all responses...')

      const synthesisRes = await axios.post(`${API_BASE}/session/${newSessionId}/synthesize`)

      addMessage('chairman', synthesisRes.data.session.final_synthesis, 'Grok 4.1 Fast (Chairman)')

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
  }
}

export default useCouncil
