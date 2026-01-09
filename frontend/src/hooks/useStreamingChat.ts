/**
 * Custom hook for streaming chat with SSE (Server-Sent Events)
 */

import { useState, useCallback, useRef } from 'react'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
  error?: string
  progress?: string
}

interface UseStreamingChatReturn {
  messages: Message[]
  isStreaming: boolean
  error: string | null
  sendMessage: (query: string, docPath?: string) => void
  clearMessages: () => void
}

export function useStreamingChat(): UseStreamingChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const sendMessage = useCallback(
    (query: string, docPath: string = '/') => {
      // Guard: Don't allow new messages while streaming
      if (isStreaming) {
        console.warn('Already streaming a response')
        return
      }

      // Guard: Empty query
      if (!query.trim()) {
        setError('Query cannot be empty')
        return
      }

      // Add user message
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: query,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMessage])
      setError(null)
      setIsStreaming(true)

      // Create assistant message placeholder
      const assistantMessageId = `assistant-${Date.now()}`
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      }

      setMessages((prev) => [...prev, assistantMessage])

      // Build SSE URL
      const params = new URLSearchParams({
        query: query,
        doc_path: docPath,
      })
      const sseUrl = `/api/chat?${params.toString()}`

      // Create EventSource for SSE
      const eventSource = new EventSource(sseUrl)
      eventSourceRef.current = eventSource

      // Handle incoming messages (tokens)
      eventSource.onmessage = (event) => {
        const token = event.data

        // Check for completion signal
        if (token === '__DONE__') {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, isStreaming: false, progress: undefined } : msg
            )
          )
          setIsStreaming(false)
          eventSource.close()
          return
        }

        // Check for error signal
        if (token.startsWith('__ERROR__:')) {
          const errorMsg = token.replace('__ERROR__:', '').trim()
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, error: errorMsg, isStreaming: false } : msg
            )
          )
          setError(errorMsg)
          setIsStreaming(false)
          eventSource.close()
          return
        }

        // Check for status/progress signal
        if (token.startsWith('__STATUS__:')) {
          const progressMsg = token.replace('__STATUS__:', '').trim()
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, progress: progressMsg } : msg
            )
          )
          return
        }

        // Append token to assistant message (and clear progress)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId ? { ...msg, content: msg.content + token, progress: undefined } : msg
          )
          )
      }

      // Handle errors and stream completion
      eventSource.onerror = (err) => {
        console.error('SSE error:', err)

        // Check if this is a normal completion (readyState === CLOSED after receiving all data)
        // or an actual error (connection failed)
        if (eventSource.readyState === EventSource.CLOSED) {
          // Normal completion - stream ended gracefully
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
            )
          )
        } else {
          // Actual error - connection failed
          setError('Connection error. Please try again.')
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, isStreaming: false, error: 'Connection error' }
                : msg
            )
          )
        }

        setIsStreaming(false)
        eventSource.close()
      }
    },
    [isStreaming]
  )

  const clearMessages = useCallback(() => {
    // Close any active stream
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    setMessages([])
    setError(null)
    setIsStreaming(false)
  }, [])

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    clearMessages,
  }
}
