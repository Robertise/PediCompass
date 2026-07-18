import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import MessageBubble from './MessageBubble'
import ConversationStarter from './ConversationStarter'
import { chatApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import { useAppStore, GUEST_PROFILE_ID } from '../../store/appStore'

export default function ChatWindow({ messages, setMessages }) {
  const { user } = useAuthStore()
  const { selectedProfileId, setIsChatActive } = useAppStore()
  // Map sentinel "guest" → null so the backend receives a real profile_id or null
  const apiProfileId = (!selectedProfileId || selectedProfileId === GUEST_PROFILE_ID)
    ? null
    : selectedProfileId
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    if (textareaRef.current && input === '') {
      textareaRef.current.style.height = ''
    }
  }, [input])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    setIsChatActive(messages.length > 0)
  }, [messages.length, setIsChatActive])

  const startSession = async () => {
    try {
      const res = await chatApi.createSession(apiProfileId)
      setSessionId(res.data.session_id)
      return res.data.session_id
    } catch (err) {
      console.error('Failed to create session', err)
      return null
    }
  }

  // textToSend  — what gets sent to the backend (may contain a token prefix)
  // displayText — what is shown in the user bubble (defaults to textToSend)
  const handleSendWithText = async (textToSend, displayText) => {
    if (!textToSend.trim() || loading) return

    const bubbleText = (displayText || textToSend).trim()
    const payloadText = textToSend.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: bubbleText }])
    setLoading(true)

    let currentSessionId = sessionId
    if (!currentSessionId) {
      currentSessionId = await startSession()
      if (!currentSessionId) {
        setMessages(prev => [...prev, { role: 'agent', content: { type: 'error', reason: 'Failed to connect to server.' } }])
        setLoading(false)
        return
      }
    }

    try {
      const res = await chatApi.sendMessage(currentSessionId, payloadText, apiProfileId)
      setMessages(prev => [...prev, { role: 'agent', content: res.data }])
    } catch (err) {
      console.error(err)
      setMessages(prev => [...prev, { role: 'agent', content: { type: 'error', reason: 'Sorry, I encountered an error processing your request.' } }])
    } finally {
      setLoading(false)
    }
  }

  const handleSend = () => handleSendWithText(input)

  // Called when user clicks a confirmation button (e.g. "I'm asking to learn in general").
  // Sends the prefixed token to backend but shows the clean option text in the user bubble.
  const handleConfirmReply = async (option, tokenPrefix) => {
    if (loading) return  // guard against double-click before re-render

    const prefixedMessage = `${tokenPrefix} ${option}`

    // Show clean label in UI (no token visible to user)
    setMessages(prev => [...prev, { role: 'user', content: option }])
    setLoading(true)

    let currentSessionId = sessionId
    if (!currentSessionId) {
      currentSessionId = await startSession()
      if (!currentSessionId) {
        setMessages(prev => [...prev, { role: 'agent', content: { type: 'error', reason: 'Failed to connect to server.' } }])
        setLoading(false)
        return
      }
    }

    try {
      const res = await chatApi.sendMessage(currentSessionId, prefixedMessage, apiProfileId)
      setMessages(prev => [...prev, { role: 'agent', content: res.data }])
    } catch (err) {
      console.error(err)
      setMessages(prev => [...prev, { role: 'agent', content: { type: 'error', reason: 'Sorry, I encountered an error processing your request.' } }])
    } finally {
      setLoading(false)
    }
  }

  // payload     — what gets sent to backend (may contain token prefix from ConversationStarter)
  // displayText — clean label shown in user bubble (optional, defaults to payload)
  const handleQuickReply = async (payload, displayText) => {
    if (!displayText) setInput(payload)
    await handleSendWithText(payload, displayText)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <main className="flex-1 flex flex-col h-full bg-transparent relative">
      {messages.length > 0 && (
        <div className="flex-1 relative overflow-y-auto py-md lg:py-lg px-4 md:px-8 space-y-lg">
          {messages.map((msg, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="w-full"
            >
              <MessageBubble
                role={msg.role}
                content={msg.content}
                onQuickReply={handleQuickReply}
                onConfirmReply={handleConfirmReply}
                isLastMessage={idx === messages.length - 1}
                loading={loading}
              />
            </motion.div>
          ))}

          {loading && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="max-w-[52rem] mx-auto w-full flex justify-start items-center py-xs"
            >
              <div className="flex items-center gap-3 text-on-surface-variant font-body-md text-left">
                <div className="flex gap-1 items-center">
                  <span className="w-2 h-2 rounded-full bg-primary opacity-60 animate-bounce" style={{ animationDelay: '0s' }}></span>
                  <span className="w-2 h-2 rounded-full bg-primary opacity-60 animate-bounce" style={{ animationDelay: '0.15s' }}></span>
                  <span className="w-2 h-2 rounded-full bg-primary opacity-60 animate-bounce" style={{ animationDelay: '0.3s' }}></span>
                </div>
                <span className="animate-pulse text-sm">Thinking...</span>
              </div>
            </motion.div>
          )}
          <div ref={messagesEndRef} className="h-20"></div> {/* padding bottom */}
        </div>
      )}

      {/* Input Area */}
      <motion.div 
        layout
        transition={{ type: "spring", bounce: 0.05, duration: 0.5 }}
        className={`px-4 md:px-8 w-full ${messages.length === 0 ? 'm-auto' : 'py-md sticky bottom-0 z-10'}`}
      >
        {messages.length > 0 && (
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/90 to-transparent pointer-events-none" />
        )}
        <div className="max-w-[52rem] mx-auto flex flex-col items-center relative z-10">
          
          {/* Empty state text positioned absolute above the input */}
          {messages.length === 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="absolute bottom-full mb-7 flex flex-col items-center justify-center text-on-surface-variant w-full max-w-[38rem] text-center gap-md"
            >
              <img src="/logo_light.png" alt="PediCompass Logo" className="w-[50px] h-[50px] object-contain opacity-40 grayscale-[20%] dark:hidden block" />
              <img src="/logo_dark.png" alt="PediCompass Logo" className="w-[50px] h-[50px] object-contain opacity-40 grayscale-[20%] hidden dark:block" />
              <h2 className="text-headline-md font-headline-md text-on-surface">How can I help you today?</h2>
              <ConversationStarter onSelect={handleQuickReply} />
            </motion.div>
          )}

          <div className="flex items-end w-full bg-surface dark:bg-surface-container-high rounded-[26px] px-[8px] py-xs focus-within:border-primary/50 transition-all shadow-[0_0_15px_1px_rgba(0,0,0,0.1)] dark:shadow-soft-dark pl-4">
            <textarea
              ref={textareaRef}
              className="flex-1 bg-transparent border-none focus:ring-0 text-body-md font-body-md text-on-surface placeholder:text-outline py-sm px-sm resize-none"
              placeholder={selectedProfileId ? 'Ask a follow-up question or describe symptoms...' : 'Describe your child\'s symptoms (select a profile above for personalized guidance)...'}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              onInput={(e) => { e.target.style.height = ''; e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'; }}
            />
            <button 
              className="w-10 h-10 mb-xs shrink-0 rounded-full bg-primary flex items-center justify-center text-on-primary hover:bg-primary-fixed-variant transition-colors shadow-sm disabled:opacity-30 disabled:hover:bg-primary"
              onClick={handleSend}
              disabled={!input.trim() || loading}
            >
              <span className="material-symbols-outlined text-[20px]">send</span>
            </button>
          </div>
          
          {messages.length > 0 && (
            <div className="text-center mt-sm text-[11px] text-on-surface-variant flex items-center justify-center gap-xs">
              <span className="material-symbols-outlined text-[14px]">lock</span> Your information is private and secure. Not a medical diagnosis.
            </div>
          )}
        </div>
      </motion.div>
    </main>
  )
}
