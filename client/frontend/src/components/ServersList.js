import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

function ServersList() {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch('/servers')
      .then(res => res.json())
      .then(data => {
        setServers(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load servers:', err);
        setLoading(false);
      });
  }, []);

  const handleReload = async () => {
    setLoading(true);
    try {
      await fetch('/config/reload', { method: 'POST' });
      // Reload the servers list
      const response = await fetch('/servers');
      const data = await response.json();
      setServers(data);
    } catch (err) {
      console.error('Failed to reload:', err);
    }
    setLoading(false);
  };

  if (loading) {
    return <div className="loading">Loading servers...</div>;
  }

  return (
    <div>
      <button className="back-button" onClick={() => navigate('/')}>
        ← Back to Dashboard
      </button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>MCP Servers</h2>
        <button className="button" onClick={handleReload}>
          Reload Servers
        </button>
      </div>

      <div className="grid grid-2">
        {servers.map(server => (
          <div key={server.name} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <h3>{server.name}</h3>
              <span className={`status ${server.status}`}>
                {server.status === 'connected' ? '✅' : '❌'} {server.status}
              </span>
            </div>
            
            <p style={{ color: '#6b7280', marginBottom: '12px' }}>
              {server.description}
            </p>

            <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', fontSize: '14px' }}>
              <span><strong>{server.tools.length}</strong> tools</span>
              <span><strong>{server.prompts.length}</strong> prompts</span>
              <span><strong>{server.resources.length}</strong> resources</span>
            </div>

            <Link 
              to={`/servers/${server.name}`} 
              className="button"
              style={{ textDecoration: 'none', display: 'inline-block' }}
            >
              View Details
            </Link>
          </div>
        ))}
      </div>

      {servers.length === 0 && (
        <div className="card">
          <h3>No Servers Connected</h3>
          <p>
            No MCP servers are currently connected. Check your configuration file 
            and ensure the servers are running.
          </p>
        </div>
      )}
    </div>
  );
}

export default ServersList;
