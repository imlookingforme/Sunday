import React, { useState, useEffect, useRef } from 'react';

interface Message {
  role: 'user' | 'sunday';
  text: string;
  timestamp: number;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  useEffect(() => {
    // Connect to SSE for real-time responses
    const eventSource = new EventSource('http://localhost:8000/api/events');
    
    eventSource.addEventListener('orb_state_change', (event) => {
      const data = JSON.parse(event.data);
      // Could update UI based on Sunday's state
    });
    
    setIsConnected(true);
    
    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, []);
  
  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const userMessage: Message = {
      role: 'user',
      text: input,
      timestamp: Date.now()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    
    // Send to backend
    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      });
      
      const data = await response.json();
      
      if (data.response) {
        const sundayMessage: Message = {
          role: 'sunday',
          text: data.response,
          timestamp: Date.now()
        };
        setMessages(prev => [...prev, sundayMessage]);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };
  
  return (
    <div className="chat-container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="chat-header" style={{ padding: '15px', borderBottom: '1px solid #333', background: '#1a1a1a' }}>
        <h3 style={{ margin: 0, color: '#4a90e2' }}>Sunday Chat</h3>
        <div style={{ fontSize: '12px', color: isConnected ? '#7ed321' : '#ff5252' }}>
          {isConnected ? '● Connected' : '○ Disconnected'}
        </div>
      </div>
      
      <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: '15px', background: '#0a0a0a' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#666', marginTop: '50px' }}>
            Start a conversation with Sunday
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`message ${msg.role}`}
            style={{
              marginBottom: '15px',
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
            }}
          >
            <div
              style={{
                maxWidth: '70%',
                padding: '10px 15px',
                borderRadius: '8px',
                background: msg.role === 'user' ? '#4a90e2' : '#333',
                color: 'white'
              }}
            >
              <div style={{ fontSize: '14px' }}>{msg.text}</div>
              <div style={{ fontSize: '10px', opacity: 0.7, marginTop: '5px' }}>
                {new Date(msg.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input" style={{ padding: '15px', borderTop: '1px solid #333', background: '#1a1a1a' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message..."
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '4px',
              border: '1px solid #333',
              background: '#0a0a0a',
              color: 'white'
            }}
          />
          <button
            onClick={sendMessage}
            style={{
              padding: '10px 20px',
              background: '#4a90e2',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
