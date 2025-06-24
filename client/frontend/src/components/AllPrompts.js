import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function AllPrompts() {
  const navigate = useNavigate();
  const [allPrompts, setAllPrompts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/prompts')
      .then(res => res.json())
      .then(data => {
        setAllPrompts(data.prompts || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load prompts:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="loading">Loading prompts...</div>;
  }

  return (
    <div>
      <button className="back-button" onClick={() => navigate('/')}>
        ← Back to Dashboard
      </button>

      <h2>All Prompts ({allPrompts.length})</h2>

      <div className="grid grid-2">
        {allPrompts.map(prompt => (
          <div key={`${prompt.server}-${prompt.name}`} className="card">
            <div style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <h3 style={{ margin: 0 }}>{prompt.name}</h3>
                <span style={{ 
                  background: '#f3f4f6', 
                  color: '#374151', 
                  padding: '2px 6px', 
                  borderRadius: '4px', 
                  fontSize: '12px' 
                }}>
                  {prompt.server}
                </span>
              </div>
              <p style={{ color: '#6b7280', fontSize: '14px', margin: 0 }}>
                {prompt.description || 'No description available'}
              </p>
            </div>

            {prompt.arguments && prompt.arguments.length > 0 && (
              <div style={{ marginTop: '12px', fontSize: '12px', color: '#6b7280' }}>
                <strong>Arguments:</strong> {prompt.arguments.map(arg => arg.name).join(', ')}
              </div>
            )}
          </div>
        ))}
      </div>

      {allPrompts.length === 0 && (
        <div className="card">
          <h3>No Prompts Available</h3>
          <p>No prompts are currently available from any connected servers.</p>
        </div>
      )}
    </div>
  );
}

export default AllPrompts;
