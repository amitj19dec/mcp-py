import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/')
      .then(res => res.json())
      .then(data => {
        setSummary(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load summary:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="loading">Loading MCP servers...</div>;
  }

  return (
    <div>
      {summary && (
        <div className="stats">
          <div className="stat">
            <div className="stat-number">{summary.servers_loaded}</div>
            <div className="stat-label">Servers</div>
          </div>
          <div className="stat">
            <div className="stat-number">{summary.total_tools}</div>
            <div className="stat-label">Tools</div>
          </div>
          <div className="stat">
            <div className="stat-number">{summary.total_prompts}</div>
            <div className="stat-label">Prompts</div>
          </div>
          <div className="stat">
            <div className="stat-number">{summary.total_resources}</div>
            <div className="stat-label">Resources</div>
          </div>
        </div>
      )}

      <div className="nav-grid">
        <Link to="/servers" className="nav-card">
          <h3>🖥️ MCP Servers</h3>
          <p>View connected servers and their status</p>
        </Link>

        <Link to="/tools" className="nav-card">
          <h3>🔧 Tools</h3>
          <p>Browse all available tools from all servers</p>
        </Link>

        <Link to="/prompts" className="nav-card">
          <h3>💬 Prompts</h3>
          <p>View all available prompts and templates</p>
        </Link>

        <Link to="/resources" className="nav-card">
          <h3>📁 Resources</h3>
          <p>Access all shared resources and data</p>
        </Link>
      </div>

      <div className="card">
        <h3>🤖 AI Chat Interface</h3>
        <p>
          Chat with AI that can automatically use any of the connected MCP tools. 
          Just ask naturally and watch the AI discover and use the right tools for your request.
        </p>
        <div style={{ marginTop: '16px' }}>
          <Link to="/chat" className="button">
            Start Chat Session
          </Link>
        </div>
      </div>

      {summary && summary.chat_available === false && (
        <div className="card" style={{ border: '1px solid #fbbf24', background: '#fffbeb' }}>
          <h3>⚠️ Chat Configuration Needed</h3>
          <p>
            Azure OpenAI is not configured. Add your credentials to .env file to enable chat functionality.
          </p>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
