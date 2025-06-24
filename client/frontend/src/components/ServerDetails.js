import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ToolDialog from './ToolDialog';

function ServerDetails() {
  const { name } = useParams();
  const navigate = useNavigate();
  const [server, setServer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState(null);

  useEffect(() => {
    fetch(`/servers/${name}`)
      .then(res => res.json())
      .then(data => {
        setServer(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load server details:', err);
        setLoading(false);
      });
  }, [name]);

  if (loading) {
    return <div className="loading">Loading server details...</div>;
  }

  if (!server) {
    return (
      <div>
        <button className="back-button" onClick={() => navigate('/servers')}>
          ← Back to Servers
        </button>
        <div className="card">
          <h3>Server Not Found</h3>
          <p>Server "{name}" could not be found.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <button className="back-button" onClick={() => navigate('/servers')}>
        ← Back to Servers
      </button>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
          <div>
            <h2>{server.name}</h2>
            <p style={{ color: '#6b7280', margin: '8px 0' }}>{server.description}</p>
          </div>
          <span className={`status ${server.status}`}>
            {server.status === 'connected' ? '✅' : '❌'} {server.status}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '24px', marginBottom: '24px' }}>
          <div className="stat">
            <div className="stat-number">{server.tools.length}</div>
            <div className="stat-label">Tools</div>
          </div>
          <div className="stat">
            <div className="stat-number">{server.prompts.length}</div>
            <div className="stat-label">Prompts</div>
          </div>
          <div className="stat">
            <div className="stat-number">{server.resources.length}</div>
            <div className="stat-label">Resources</div>
          </div>
        </div>
      </div>

      {server.tools.length > 0 && (
        <div className="card">
          <h3>Tools</h3>
          <div className="grid">
            {server.tools.map(tool => (
              <div key={tool.name} className="card" style={{ margin: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <h4 style={{ margin: '0 0 8px 0' }}>{tool.name}</h4>
                    <p style={{ color: '#6b7280', fontSize: '14px', margin: 0 }}>
                      {tool.description}
                    </p>
                  </div>
                  <button 
                    className="button secondary"
                    onClick={() => setSelectedTool(tool)}
                    style={{ marginLeft: '16px' }}
                  >
                    Test
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {server.prompts.length > 0 && (
        <div className="card">
          <h3>Prompts</h3>
          <div className="grid">
            {server.prompts.map(prompt => (
              <div key={prompt.name} className="card" style={{ margin: 0 }}>
                <h4 style={{ margin: '0 0 8px 0' }}>{prompt.name}</h4>
                <p style={{ color: '#6b7280', fontSize: '14px' }}>
                  {prompt.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {server.resources.length > 0 && (
        <div className="card">
          <h3>Resources</h3>
          <div className="grid">
            {server.resources.map(resource => (
              <div key={resource.uri} className="card" style={{ margin: 0 }}>
                <h4 style={{ margin: '0 0 8px 0' }}>{resource.name}</h4>
                <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '8px' }}>
                  {resource.description}
                </p>
                <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                  <div>URI: {resource.uri}</div>
                  {resource.mime_type && <div>Type: {resource.mime_type}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedTool && (
        <ToolDialog 
          tool={selectedTool} 
          serverName={server.name}
          onClose={() => setSelectedTool(null)} 
        />
      )}
    </div>
  );
}

export default ServerDetails;
