import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function ChatInterface() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatStatus, setChatStatus] = useState(null);

  useEffect(() => {
    // Check if chat is available
    fetch('/chat/status')
      .then(res => res.json())
      .then(data => setChatStatus(data))
      .catch(err => console.error('Failed to check chat status:', err));
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { type: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input }),
      });

      const data = await response.json();
      
      if (response.ok) {
        const aiMessage = { 
          type: 'ai', 
          content: data.response,
          toolCalls: data.tool_calls_made || []
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        const errorMessage = { 
          type: 'ai', 
          content: `Error: ${data.detail || 'Failed to process message'}` 
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (err) {
      const errorMessage = { 
        type: 'ai', 
        content: 'Error: Failed to connect to chat service' 
      };
      setMessages(prev => [...prev, errorMessage]);
    }

    setLoading(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div>
      <button className="back-button" onClick={() => navigate('/')}>
        ← Back to Dashboard
      </button>

      <div style={{ marginBottom: '16px' }}>
        <h2>AI Chat Interface</h2>
        <p style={{ color: '#6b7280' }}>
          Chat with AI that can automatically discover and use MCP tools. 
          Try asking for calculations, or any task that might use the connected tools.
        </p>
        
        {chatStatus && !chatStatus.chat_available && (
          <div className="card" style={{ border: '1px solid #fbbf24', background: '#fffbeb' }}>
            <h3>⚠️ Chat Not Available</h3>
            <p>
              Azure OpenAI is not configured. Please add your credentials to the .env file 
              and restart the backend to enable chat functionality.
            </p>
          </div>
        )}

        {chatStatus && chatStatus.chat_available && (
          <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '16px' }}>
            ✅ Chat enabled with {chatStatus.tools_available} tools available
          </div>
        )}
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', color: '#6b7280', marginTop: '50px' }}>
              <h3>Welcome to MCP Chat! 🤖</h3>
              <p>Try asking something like:</p>
              <ul style={{ textAlign: 'left', display: 'inline-block' }}>
                <li>"Calculate 15 * 23 + 45"</li>
                <li>"What's 100 divided by 8?"</li>
                <li>"Multiply 25 by 16"</li>
              </ul>
            </div>
          )}
          
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.type}`}>
              <div>{message.content}</div>
              {message.toolCalls && message.toolCalls.length > 0 && (
                <div style={{ 
                  marginTop: '8px', 
                  fontSize: '12px', 
                  opacity: 0.7,
                  borderTop: '1px solid rgba(255,255,255,0.2)',
                  paddingTop: '8px'
                }}>
                  Used tools: {message.toolCalls.map(call => `${call.server}.${call.tool}`).join(', ')}
                </div>
              )}
            </div>
          ))}
          
          {loading && (
            <div className="message ai loading">
              AI is thinking and checking available tools...
            </div>
          )}
        </div>

        <div className="chat-input">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              chatStatus?.chat_available 
                ? "Type your message here..." 
                : "Chat not available - check Azure OpenAI configuration"
            }
            disabled={!chatStatus?.chat_available || loading}
          />
          <button 
            className="button"
            onClick={sendMessage}
            disabled={!input.trim() || loading || !chatStatus?.chat_available}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;
