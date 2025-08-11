import React from 'react';
import './chat.css';

const ChatMessage = ({ role, content }) => {
  const isUser = role === 'user';
  return (
    <div className={`chat-message ${isUser ? 'user' : 'assistant'}`}>
      <div className="chat-bubble">{content}</div>
    </div>
  );
};

export default ChatMessage;
