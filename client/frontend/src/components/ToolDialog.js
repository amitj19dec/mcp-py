import React, { useState } from 'react';

function ToolDialog({ tool, serverName, onClose }) {
  const [arguments_, setArguments] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleArgumentChange = (paramName, value) => {
    setArguments(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  const executeTool = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/tools/call', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          server_name: serverName,
          tool_name: tool.name,
          arguments: arguments_
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        setResult(data.result);
      } else {
        setError(data.error || 'Tool execution failed');
      }
    } catch (err) {
      setError('Failed to execute tool');
    }

    setLoading(false);
  };

  const renderParameterInput = (paramName, paramSchema) => {
    const paramType = paramSchema.type || 'string';
    const isRequired = tool.input_schema?.required?.includes(paramName) || false;

    return (
      <div key={paramName} style={{ marginBottom: '16px' }}>
        <label style={{ 
          display: 'block', 
          marginBottom: '4px', 
          fontSize: '14px',
          fontWeight: '500'
        }}>
          {paramSchema.title || paramName}
          {isRequired && <span style={{ color: '#dc2626' }}>*</span>}
        </label>
        
        {paramType === 'number' ? (
          <input
            type="number"
            value={arguments_[paramName] || ''}
            onChange={(e) => handleArgumentChange(paramName, parseFloat(e.target.value) || 0)}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: '1px solid #e1e5e9',
              borderRadius: '6px',
              fontSize: '14px'
            }}
          />
        ) : (
          <input
            type="text"
            value={arguments_[paramName] || ''}
            onChange={(e) => handleArgumentChange(paramName, e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: '1px solid #e1e5e9',
              borderRadius: '6px',
              fontSize: '14px'
            }}
          />
        )}
        
        {paramSchema.description && (
          <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
            {paramSchema.description}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
          <h2>Test Tool: {tool.name}</h2>
          <button 
            onClick={onClose}
            style={{ 
              background: 'none', 
              border: 'none', 
              fontSize: '20px', 
              cursor: 'pointer',
              color: '#6b7280'
            }}
          >
            ×
          </button>
        </div>

        <div style={{ marginBottom: '16px', color: '#6b7280', fontSize: '14px' }}>
          <strong>Server:</strong> {serverName}
        </div>

        <div style={{ marginBottom: '16px', color: '#6b7280', fontSize: '14px' }}>
          {tool.description}
        </div>

        {tool.input_schema?.properties && (
          <div style={{ marginBottom: '24px' }}>
            <h3>Parameters</h3>
            {Object.entries(tool.input_schema.properties).map(([paramName, paramSchema]) =>
              renderParameterInput(paramName, paramSchema)
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
          <button 
            className="button"
            onClick={executeTool}
            disabled={loading}
          >
            {loading ? 'Executing...' : 'Execute Tool'}
          </button>
          <button 
            className="button secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        {error && (
          <div style={{ 
            background: '#fef2f2', 
            border: '1px solid #fecaca', 
            borderRadius: '6px', 
            padding: '12px',
            marginBottom: '16px'
          }}>
            <div style={{ color: '#dc2626', fontWeight: '500' }}>Error</div>
            <div style={{ color: '#dc2626', fontSize: '14px' }}>{error}</div>
          </div>
        )}

        {result && (
          <div style={{ 
            background: '#f0fdf4', 
            border: '1px solid #bbf7d0', 
            borderRadius: '6px', 
            padding: '12px' 
          }}>
            <div style={{ color: '#166534', fontWeight: '500', marginBottom: '8px' }}>Result</div>
            <pre style={{ 
              color: '#166534', 
              fontSize: '14px', 
              margin: 0,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default ToolDialog;
