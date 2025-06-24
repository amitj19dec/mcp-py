import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function AllResources() {
  const navigate = useNavigate();
  const [allResources, setAllResources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/resources')
      .then(res => res.json())
      .then(data => {
        setAllResources(data.resources || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load resources:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="loading">Loading resources...</div>;
  }

  return (
    <div>
      <button className="back-button" onClick={() => navigate('/')}>
        ← Back to Dashboard
      </button>

      <h2>All Resources ({allResources.length})</h2>

      <div className="grid grid-2">
        {allResources.map(resource => (
          <div key={`${resource.server}-${resource.uri}`} className="card">
            <div style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <h3 style={{ margin: 0 }}>{resource.name}</h3>
                <span style={{ 
                  background: '#f3f4f6', 
                  color: '#374151', 
                  padding: '2px 6px', 
                  borderRadius: '4px', 
                  fontSize: '12px' 
                }}>
                  {resource.server}
                </span>
              </div>
              <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '8px' }}>
                {resource.description || 'No description available'}
              </p>
              <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                <div><strong>URI:</strong> {resource.uri}</div>
                {resource.mime_type && <div><strong>Type:</strong> {resource.mime_type}</div>}
              </div>
            </div>
          </div>
        ))}
      </div>

      {allResources.length === 0 && (
        <div className="card">
          <h3>No Resources Available</h3>
          <p>No resources are currently available from any connected servers.</p>
        </div>
      )}
    </div>
  );
}

export default AllResources;
