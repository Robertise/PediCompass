import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import MessageBubble from './MessageBubble'
import ConversationStarter from './ConversationStarter'
import StaleProfileBanner from '../Profiles/StaleProfileBanner'
import { chatApi, profileApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import { useAppStore, GUEST_PROFILE_ID } from '../../store/appStore'

export default function ChatWindow({ messages, setMessages, selectedMessageIndex, onSelectMessage }) {
  const { user } = useAuthStore()
  const {
    selectedProfileId,
    setIsChatActive,
    setShowProfileModal,
    setEditingProfile,
    dismissedStaleReminders,
    dismissStaleReminder,
  } = useAppStore()
  // Map sentinel "guest" → null so the backend receives a real profile_id or null
  const apiProfileId = (!selectedProfileId || selectedProfileId === GUEST_PROFILE_ID)
    ? null
    : selectedProfileId
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [activeProfile, setActiveProfile] = useState(null)
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const textareaRef = useRef(null)
  const activeSourceRef = useRef(null)

  useEffect(() => {
    async function checkProfileStaleness() {
      if (!user || !selectedProfileId || selectedProfileId === GUEST_PROFILE_ID) {
        setActiveProfile(null)
        return
      }
      try {
        const res = await profileApi.list()
        const found = res.data.find(p => p.profile_id === selectedProfileId)
        setActiveProfile(found || null)
      } catch {
        setActiveProfile(null)
      }
    }
    checkProfileStaleness()
    window.addEventListener('profilesUpdated', checkProfileStaleness)
    return () => window.removeEventListener('profilesUpdated', checkProfileStaleness)
  }, [user, selectedProfileId])

  let daysStale = 0
  let isStale = false
  if (activeProfile && activeProfile.last_updated) {
    const lastUpdatedDate = new Date(activeProfile.last_updated)
    const now = new Date()
    daysStale = Math.floor((now - lastUpdatedDate) / (1000 * 60 * 60 * 24))
    isStale = daysStale >= 30
  }

  const showStaleBanner = isStale && !dismissedStaleReminders[selectedProfileId]

  const handleUpdateWeightNow = () => {
    if (activeProfile) {
      setEditingProfile(activeProfile)
      setShowProfileModal(true)
    }
  }

  const handleDismissStaleBanner = () => {
    if (selectedProfileId) {
      dismissStaleReminder(selectedProfileId)
    }
  }

  useEffect(() => {
    return () => {
      if (activeSourceRef.current) {
        activeSourceRef.current.close()
      }
    }
  }, [])

  useEffect(() => {
    if (textareaRef.current && input === '') {
      textareaRef.current.style.height = ''
    }
  }, [input])

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
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

  const { setShowAuthModal } = useAppStore()

  // textToSend  — what gets sent to the backend (may contain a token prefix)
  // displayText — what is shown in the user bubble (defaults to textToSend)
  const handleSendWithText = async (textToSend, displayText) => {
    if (!textToSend.trim() || loading) return

    // Block unauthenticated users — open login modal instead
    if (!user) {
      setShowAuthModal(true)
      return
    }

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

    // Step 1: Register message to get request_id
    let requestId
    try {
      const res = await chatApi.registerMessage(currentSessionId, payloadText, apiProfileId)
      requestId = res.data.request_id
    } catch (err) {
      console.error('Failed to register message:', err)
      setMessages(prev => [...prev, {
        role: 'agent',
        content: { type: 'error', reason: 'Failed to send message. Please try again.' }
      }])
      setLoading(false)
      return
    }

    // Add streaming placeholder with a stable id.
    // NOTE: placeholder does NOT need reasoning_trace field — ChatPage.jsx
    // auto-select condition now checks for type==='streaming' directly.
    const streamingMsgId = `streaming_${Date.now()}`
    setMessages(prev => [...prev, {
      role: 'agent',
      id: streamingMsgId,
      content: { type: 'streaming', trace: {}, latencies: {}, lastMessage: null },
    }])

    // Step 2: Open SSE stream
    const { token } = useAuthStore.getState()
    const source = chatApi.openStream(requestId, token)
    activeSourceRef.current = source

    let liveLatencies = {}

    source.onmessage = (event) => {
      const sseEvent = JSON.parse(event.data)

      if (sseEvent.event === 'heartbeat') return  // No-op — just keeps ALB alive

      if (sseEvent.event === 'stage_update') {
        // Accumulate completed stage trace data and latencies.
        // Only update on status==='done' events (not 'running' events).
        const newTrace = {}

        if (sseEvent.stage && sseEvent.status === 'done') {
          if (sseEvent.data) newTrace[sseEvent.stage] = sseEvent.data
          if (sseEvent.latency_ms != null) {
            liveLatencies = { ...liveLatencies, [sseEvent.stage]: sseEvent.latency_ms }
          }
        }

        setMessages(prev => prev.map(m =>
          m.id === streamingMsgId
            ? {
                ...m,
                content: {
                  type: 'streaming',
                  trace: {
                    ...(m.content.trace || {}),
                    ...newTrace,
                    latencies: liveLatencies,
                  },
                  latencies: liveLatencies,
                  lastMessage: sseEvent.message ?? m.content.lastMessage,
                }
              }
            : m
        ))
      }

      if (sseEvent.event === 'final_response') {
        // Replace streaming placeholder with real response.
        // Attach accumulated latencies into reasoning_trace for display in sidebar.
        const finalContent = {
          ...sseEvent.data,
          reasoning_trace: {
            ...(sseEvent.data.reasoning_trace || {}),
            latencies: liveLatencies,
          },
        }
        setMessages(prev => prev.map(m =>
          m.id === streamingMsgId
            ? { ...m, id: undefined, content: finalContent }
            : m
        ))
      }

      if (sseEvent.event === 'error') {
        setMessages(prev => prev.map(m =>
          m.id === streamingMsgId
            ? { ...m, id: undefined, content: { type: 'error', reason: sseEvent.message } }
            : m
        ))
        source.close()
        activeSourceRef.current = null
        setLoading(false)
      }

      if (sseEvent.event === 'done') {
        source.close()
        activeSourceRef.current = null
        setLoading(false)
      }
    }

    source.onerror = () => {
      setMessages(prev => prev.map(m =>
        m.id === streamingMsgId
          ? { ...m, id: undefined, content: { type: 'error', reason: 'Connection lost. Please try again.' } }
          : m
      ))
      source.close()
      activeSourceRef.current = null
      setLoading(false)
    }
  }

  const handleSend = () => handleSendWithText(input)

  // Called when user clicks a confirmation button (e.g. "I'm asking to learn in general").
  // Sends the prefixed token to backend but shows the clean option text in the user bubble.
  const handleConfirmReply = async (option, tokenPrefix) => {
    if (loading) return  // guard against double-click before re-render
    const prefixedMessage = `${tokenPrefix} ${option}`
    await handleSendWithText(prefixedMessage, option)
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
    <main className="flex-1 flex flex-col min-h-0 bg-transparent relative">
      {showStaleBanner && (
        <div className="px-4 md:px-8 pt-md shrink-0">
          <StaleProfileBanner
            profile={activeProfile}
            daysStale={daysStale}
            onUpdateWeight={handleUpdateWeightNow}
            onDismiss={handleDismissStaleBanner}
          />
        </div>
      )}

      {/* Messages list — scrolls independently when messages exist */}
      {messages.length > 0 && (
        <div ref={messagesContainerRef} className="flex-1 min-h-0 overflow-y-auto py-md lg:py-lg px-4 md:px-8 space-y-lg">
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
                isSelected={idx === selectedMessageIndex}
                onSelectTrace={() => onSelectMessage(idx)}
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
          <div ref={messagesEndRef} className="h-20"></div>
        </div>
      )}

      {/* Input Area — centered with m-auto on desktop when no messages, fixed at bottom when messages exist */}
      <div className={`px-4 md:px-8 w-full relative ${messages.length === 0 ? 'my-auto pb-[12vh] md:pb-0 md:m-auto shrink-0' : 'py-3 md:py-md shrink-0'}`}>
        {messages.length > 0 && (
          <div className="absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-transparent to-background pointer-events-none -translate-y-full" />
        )}

        <div className="max-w-[52rem] mx-auto flex flex-col items-center relative">
          {/* Empty state — logo + title + suggestions above input box */}
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="w-full flex flex-col items-center text-center gap-xs sm:gap-md mb-4 md:mb-0 md:absolute md:bottom-full md:mb-7 px-1 sm:px-0 md:max-w-[38rem] md:inset-x-0 md:mx-auto"
            >
              <img src="/logo_light.png" alt="Pedix Logo" className="w-[38px] h-[38px] sm:w-[50px] sm:h-[50px] object-contain opacity-40 grayscale-[20%] dark:hidden block" />
              <img src="/logo_dark.png" alt="Pedix Logo" className="w-[38px] h-[38px] sm:w-[50px] sm:h-[50px] object-contain opacity-40 grayscale-[20%] hidden dark:block" />
              <h2 className="text-lg sm:text-headline-md font-headline-md font-bold text-on-surface">How can I help you today?</h2>
              <ConversationStarter onSelect={handleQuickReply} />
            </motion.div>
          )}

          <div className="flex items-end w-full bg-surface dark:bg-surface-container-high rounded-[24px] sm:rounded-[26px] px-2 sm:px-[8px] py-1 sm:py-xs focus-within:border-primary/50 transition-all shadow-[0_0_15px_1px_rgba(0,0,0,0.1)] dark:shadow-soft-dark pl-3 sm:pl-4">
            <textarea
              ref={textareaRef}
              className="flex-1 bg-transparent border-none focus:ring-0 text-sm sm:text-body-md font-body-md text-on-surface placeholder:text-outline py-2 sm:py-sm px-2 sm:px-sm resize-none"
              placeholder={
                window.innerWidth < 640
                  ? (selectedProfileId ? 'Ask a question...' : 'Describe symptoms...')
                  : (selectedProfileId ? 'Ask a follow-up question or describe symptoms...' : 'Describe your child\'s symptoms (select a profile above)...')
              }
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onFocus={() => {
                // Aggressively prevent native scroll-into-view on mobile keyboards.
                // Browsers apply this across multiple animation frames, so we must
                // fight back across multiple frames too.
                window.scrollTo(0, 0)
                document.documentElement.scrollTop = 0
                document.body.scrollTop = 0

                let frameCount = 0
                const lockScroll = () => {
                  window.scrollTo(0, 0)
                  document.documentElement.scrollTop = 0
                  document.body.scrollTop = 0
                  frameCount++
                  if (frameCount < 10) {
                    requestAnimationFrame(lockScroll)
                  } else {
                    scrollToBottom()
                  }
                }
                requestAnimationFrame(lockScroll)
              }}
              onKeyDown={handleKeyDown}
              disabled={loading}
              onInput={(e) => { e.target.style.height = ''; e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'; }}
            />
            <button 
              className="w-9 h-9 sm:w-10 sm:h-10 mb-1 sm:mb-xs shrink-0 rounded-full bg-primary flex items-center justify-center text-on-primary hover:bg-primary-fixed-variant transition-colors shadow-sm disabled:opacity-30 disabled:hover:bg-primary active:scale-95"
              onClick={handleSend}
              disabled={!input.trim() || loading}
            >
              <span className="material-symbols-outlined text-[18px] sm:text-[20px]">send</span>
            </button>
          </div>
          
          {messages.length > 0 && (
            <div className="text-center mt-2 text-[11px] text-on-surface-variant flex items-center justify-center gap-xs">
              <span className="material-symbols-outlined text-[14px]">lock</span> Your information is private and secure. Not a medical diagnosis.
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
