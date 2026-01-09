/**
 * Component for rendering a single message with streaming support
 */

import { Message } from '../hooks/useStreamingChat'

interface MessageStreamProps {
  message: Message
}

export function MessageStream({ message }: MessageStreamProps) {
  const isUser = message.role === 'user'

  return (
    <div
      style={{
        ...styles.messageContainer,
        ...(isUser ? styles.userMessage : styles.assistantMessage),
      }}
    >
      {/* Role label */}
      <div style={styles.roleLabel}>
        {isUser ? 'You' : 'Assistant'}
        {message.isStreaming && <span style={styles.streamingIndicator}> ●</span>}
      </div>

      {/* Progress indicator */}
      {message.progress && (
        <div style={styles.progress}>
          {message.progress}
        </div>
      )}

      {/* Message content */}
      <div style={styles.content}>
        {message.content || (message.isStreaming && !message.progress ? 'Thinking...' : '')}
      </div>

      {/* Error display */}
      {message.error && (
        <div style={styles.error}>
          <strong>Error:</strong> {message.error}
        </div>
      )}

      {/* Timestamp */}
      <div style={styles.timestamp}>{message.timestamp.toLocaleTimeString()}</div>
    </div>
  )
}

const styles = {
  messageContainer: {
    marginBottom: '16px',
    padding: '16px',
    borderRadius: '8px',
    maxWidth: '80%',
  },
  userMessage: {
    marginLeft: 'auto',
    backgroundColor: '#dbeafe',
    borderLeft: '4px solid #2563eb',
  },
  assistantMessage: {
    marginRight: 'auto',
    backgroundColor: '#f3f4f6',
    borderLeft: '4px solid #9ca3af',
  },
  roleLabel: {
    fontSize: '12px',
    fontWeight: 'bold' as const,
    textTransform: 'uppercase' as const,
    color: '#6b7280',
    marginBottom: '8px',
  },
  streamingIndicator: {
    color: '#2563eb',
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  content: {
    fontSize: '16px',
    lineHeight: '1.6',
    color: '#1f2937',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
  },
  error: {
    marginTop: '8px',
    padding: '8px 12px',
    backgroundColor: '#fee2e2',
    border: '1px solid #ef4444',
    borderRadius: '4px',
    fontSize: '14px',
    color: '#991b1b',
  },
  timestamp: {
    marginTop: '8px',
    fontSize: '12px',
    color: '#9ca3af',
  },
  progress: {
    fontSize: '14px',
    fontStyle: 'italic' as const,
    color: '#2563eb',
    marginBottom: '8px',
    padding: '6px 10px',
    backgroundColor: '#dbeafe',
    borderRadius: '4px',
  },
}
