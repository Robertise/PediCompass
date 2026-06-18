import { useState } from 'react'
import ChatWindow from '../components/Chat/ChatWindow'
import ReasoningTrace from '../components/Chat/ReasoningTrace'

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  
  // Extract reasoning trace from the latest agent message
  const latestTrace = [...messages].reverse().find(m => m.role === 'agent' && m.content?.reasoning_trace)?.content?.reasoning_trace

  return (
    <>
      <ChatWindow messages={messages} setMessages={setMessages} />
      <ReasoningTrace trace={latestTrace} />
    </>
  )
}
