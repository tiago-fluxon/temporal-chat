/**
 * Main chat interface component
 */

import React, { useState, useRef, useEffect } from 'react'
import { useStreamingChat } from '../hooks/useStreamingChat'
import { MessageStream } from './MessageStream'

const STORAGE_KEY = 'docChat:docPath'

export function ChatInterface() {
  const { messages, isStreaming, error, sendMessage, clearMessages } = useStreamingChat()
  const [query, setQuery] = useState('')
  const [docPath, setDocPath] = useState(() => {
    // Load from localStorage on mount
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored || '/'
    } catch {
      return '/'
    }
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Persist docPath to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, docPath)
    } catch (err) {
      console.error('Failed to save docPath to localStorage:', err)
    }
  }, [docPath])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Guard: Empty query
    if (!query.trim()) {
      return
    }

    sendMessage(query, docPath)
    setQuery('')
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>Document Chat</h1>
        <p style={styles.subtitle}>Ask questions about files on your Desktop (mounted at startup)</p>
      </div>

      {/* Messages */}
      <div style={styles.messagesContainer}>
        {messages.length === 0 && (
          <div style={styles.emptyState}>
            <p>No messages yet. Ask a question about your documents!</p>
          </div>
        )}

        {messages.map((message) => (
          <MessageStream key={message.id} message={message} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Error display */}
      {error && (
        <div style={styles.errorBanner}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} style={styles.form}>
        <div style={styles.inputGroup}>
          <label style={styles.label}>
            Folder Path (relative to Desktop):
            <input
              type="text"
              value={docPath}
              onChange={(e) => setDocPath(e.target.value)}
              placeholder="/ for Desktop, or folder name"
              style={styles.pathInput}
            />
          </label>
        </div>

        <div style={styles.queryInputGroup}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about your documents..."
            disabled={isStreaming}
            style={{
              ...styles.queryInput,
              ...(isStreaming ? styles.inputDisabled : {}),
            }}
          />
          <button
            type="submit"
            disabled={isStreaming || !query.trim()}
            style={{
              ...styles.submitButton,
              ...(isStreaming || !query.trim() ? styles.buttonDisabled : {}),
            }}
          >
            {isStreaming ? 'Streaming...' : 'Send'}
          </button>
        </div>

        {messages.length > 0 && (
          <button
            type="button"
            onClick={clearMessages}
            disabled={isStreaming}
            style={styles.clearButton}
          >
            Clear Chat
          </button>
        )}
      </form>
    </div>
  )
}

// Inline styles (minimal, functional)
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100vh',
    maxWidth: '900px',
    margin: '0 auto',
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: '20px',
    backgroundColor: '#2563eb',
    color: 'white',
    textAlign: 'center' as const,
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '24px',
    fontWeight: 'bold',
  },
  subtitle: {
    margin: 0,
    fontSize: '14px',
    opacity: 0.9,
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '20px',
    backgroundColor: 'white',
  },
  emptyState: {
    textAlign: 'center' as const,
    color: '#666',
    padding: '40px 20px',
  },
  errorBanner: {
    padding: '12px 20px',
    backgroundColor: '#fee2e2',
    border: '1px solid #ef4444',
    color: '#991b1b',
    fontSize: '14px',
  },
  form: {
    padding: '20px',
    backgroundColor: 'white',
    borderTop: '1px solid #e5e7eb',
  },
  inputGroup: {
    marginBottom: '12px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: '500',
    marginBottom: '6px',
    color: '#374151',
  },
  pathInput: {
    width: '100%',
    padding: '8px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    marginTop: '4px',
  },
  queryInputGroup: {
    display: 'flex',
    gap: '8px',
  },
  queryInput: {
    flex: 1,
    padding: '12px 16px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '16px',
  },
  inputDisabled: {
    backgroundColor: '#f3f4f6',
    cursor: 'not-allowed',
  },
  submitButton: {
    padding: '12px 24px',
    backgroundColor: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  buttonDisabled: {
    backgroundColor: '#9ca3af',
    cursor: 'not-allowed',
  },
  clearButton: {
    marginTop: '12px',
    padding: '8px 16px',
    backgroundColor: '#ef4444',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
  },
}
