import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ToolDialog from './ToolDialog';

function AllTools() {
  const navigate = useNavigate();
  const [allTools, setAllTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetch('/tools')
      .then(res => res.json())
      .then(data => {
        setAllTools(data.tools || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load tools:', err);
        setLoading(false);
      });
  }, []);

  const filteredTools = allTools.filter(tool => 
    tool.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tool.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tool.server.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="loading">Loading tools...</div>;
  }

  return (
    <div>
      <button className="back-button" onClick={() => navigate('/')}>
        ← Back to Dashboard
      </button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>All Tools ({allTools.length})</h2>
        <input
          type="text"
          placeholder="Search tools..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #e1e5e9',
            borderRadius: '6px',
            fontSize: '14px',
            width: '300px'
          }}
        />
      </div>

      <div className="grid grid-2">
        {filteredTools.map(tool => (
          <div key={`${tool.server}-${tool.name}`} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <h3 style={{ margin: 0 }}>{tool.name}</h3>
                  <span style={{ 
                    background: '#f3f4f6', 
                    color: '#374151', 
                    padding: '2px 6px', 
                    borderRadius: '4px', 
                    fontSize: '12px' 
                  }}>
                    {tool.server}
                  </span>
                </div>
                <p style={{ color: '#6b7280', fontSize: '14px', margin: 0 }}>
                  {tool.description}
                </p>
              </div>
              <button 
                className="button secondary"
                onClick={() => setSelectedTool({ ...tool, serverName: tool.server })}
                style={{ marginLeft: '16px' }}
              >
                Test
              </button>
            </div>

            {tool.input_schema && tool.input_schema.properties && (
              <div style={{ marginTop: '12px', fontSize: '12px', color: '#6b7280' }}>
                <strong>Parameters:</strong> {Object.keys(tool.input_schema.properties).join(', ')}
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredTools.length === 0 && allTools.length > 0 && (
        <div className="card">
          <h3>No Tools Found</h3>
          <p>No tools match your search criteria. Try a different search term.</p>
        </div>
      )}

      {allTools.length === 0 && (
        <div className="card">
          <h3>No Tools Available</h3>
          <p>No tools are currently available from any connected servers.</p>
        </div>
      )}

      {selectedTool && (
        <ToolDialog 
          tool={selectedTool} 
          serverName={selectedTool.serverName}
          onClose={() => setSelectedTool(null)} 
        />
      )}
    </div>
  );
}

export default AllTools;
