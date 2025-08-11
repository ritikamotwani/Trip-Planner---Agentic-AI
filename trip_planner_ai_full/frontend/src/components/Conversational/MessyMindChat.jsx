import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ChatMessage from './ChatMessage';
import './chat.css';

axios.defaults.withCredentials = true;

export default function MessyMindChat() {
  const [messages, setMessages] = useState([
    { role: 'system', content: 'You are Wanderlust, a friendly travel assistant helping users plan amazing trips.' },
    { role: 'assistant', content: 'Hey there! Ready to plan your next adventure? 🗺️' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [responseId, setResponseId] = useState(null);
  const boxRef = useRef(null);

  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight;
  }, [messages]);

  const sendMessage = async () => {
    console.log(input, "input");
    const text = input.trim();
    if (!text) return;

    const userMsg = { role: 'user', content: text };
    let updatedMessages = [...messages, userMsg];
    if (responseId) {
      updatedMessages = [userMsg];
    }
    setMessages([...messages, userMsg]);
    console.log(messages, "messages");
    setInput('');
    setLoading(true);

    try {
      const session_id = document.cookie.match(/(^|;) *session_id=([^;]+)/)?.[2] || '';
      console.log(messages, "messages", updatedMessages);
      const res = await axios.post('http://localhost:8000/chat', {
        session_id,
        messages: updatedMessages,
        previous_response_id: responseId
      });
      console.log(res, res.data)
      setResponseId(res.data.response_id);
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Oops, something went wrong.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-wrapper">
      <div className="chat-container">
        <div className="chat-box" ref={boxRef}>
          {messages.map((msg, idx) => (
            <ChatMessage key={idx} role={msg.role} content={msg.content} />
          ))}
          {loading && <ChatMessage role="assistant" content="Typing..." />}
        </div>

        <div className="chat-input-wrapper">
          <input
            className="chat-input"
            placeholder="Type your travel question..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            disabled={loading}
          />
          <button className="chat-send" onClick={sendMessage} disabled={loading}>
            {loading ? '...' : 'Send'}
          </button>
        </div>
      </div>

      <div className="chat-side-panel">
        <div className="chat-side-overlay">
          Ritika @ Crater Lake National Park
        </div>
      </div>
    </div>
  );
}
