/**
 * ToolTester Component
 * Allows manual testing of tools through the gateway
 * Provides dynamic parameter input and response display
 */
import React, { useState, useEffect } from 'react';
import { Play, Code, Copy, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { api } from '../services/api';

function ToolTester() {
  const [tools, setTools] = useState([]);
  const [selectedTool, setSelectedTool] = useState(null);
  const [parameters, setParameters] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      const response = await api.getToolCatalog();
      setTools(response.tools || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load tools:', err);
      setError('Failed to load tools');
    } finally {
      setCatalogLoading(false);
    }
  };

  const handleToolSelect = (toolName) => {
    const tool = tools.find(t => t.name === toolName);
    setSelectedTool(tool);
    setParameters({});
    setResult(null);
  };

  const handleParameterChange = (paramName, value) => {
    setParameters(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  const handleExecute = async () => {
    if (!selectedTool) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await api.executeTool(selectedTool.name, parameters);
      setResult({
        success: response.success,
        content: response.result,
        isError: response.isError,
        timestamp: new Date().toISOString()
      });
    } catch (err) {
      console.error('Tool execution failed:', err);
      setResult({
        success: false,
        content: [{
          type: 'text',
          text: `Error: ${err.message}`
        }],
        isError: true,
        timestamp: new Date().toISOString()
      });
    } finally {
      setLoading(false);
    }
  };

  const copyResult = () => {
    if (result?.content) {
      navigator.clipboard.writeText(JSON.stringify(result.content, null, 2));
    }
  };

  if (catalogLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-2 text-gray-600">Loading tools...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Tools</h3>
        <p className="text-red-700">{error}</p>
        <button
          onClick={loadTools}
          className="mt-4 px-4 py-2 bg-red-100 text-red-800 rounded hover:bg-red-200"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Tool Tester</h2>
        <p className="text-gray-600">Test tool execution through the gateway</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tool selection and parameters */}
        <div className="space-y-6">
          {/* Tool selection */}
          <div className="bg-white rounded-lg border p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Select Tool</h3>
            
            {tools.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No tools available. Make sure your backend servers are connected.
              </div>
            ) : (
              <select
                value={selectedTool?.name || ''}
                onChange={(e) => handleToolSelect(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Choose a tool to test...</option>
                {tools.map((tool) => (
                  <option key={tool.name} value={tool.name}>
                    {tool.name} - {tool.description || 'No description'}
                  </option>
                ))}
              </select>
            )}

            {selectedTool && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-sm font-medium text-gray-700">Selected:</span>
                  <code className="text-sm bg-white px-2 py-1 rounded border">
                    {selectedTool.name}
                  </code>
                </div>
                <p className="text-sm text-gray-600">{selectedTool.description}</p>
                <div className="mt-2 text-xs text-gray-500">
                  Source: {selectedTool.source_server} | Namespace: {selectedTool.namespace}
                </div>
              </div>
            )}
          </div>

          {/* Parameters input */}
          {selectedTool && (
            <ParametersInput
              tool={selectedTool}
              parameters={parameters}
              onParameterChange={handleParameterChange}
            />
          )}

          {/* Execute button */}
          {selectedTool && (
            <div className="bg-white rounded-lg border p-6">
              <button
                onClick={handleExecute}
                disabled={loading}
                className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader className="h-5 w-5 animate-spin" />
                    <span>Executing...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5" />
                    <span>Execute Tool</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Results */}
        <div className="space-y-6">
          <ResultDisplay result={result} onCopy={copyResult} />
        </div>
      </div>
    </div>
  );
}

// Parameters input component
function ParametersInput({ tool, parameters, onParameterChange }) {
  const [jsonMode, setJsonMode] = useState(false);
  const [jsonText, setJsonText] = useState('{}');

  // Parse schema to get parameter fields
  const getParameterFields = () => {
    if (!tool.input_schema?.properties) return [];
    
    return Object.entries(tool.input_schema.properties).map(([name, schema]) => ({
      name,
      type: schema.type || 'string',
      description: schema.description || '',
      required: tool.input_schema.required?.includes(name) || false,
      enum: schema.enum || null,
      default: schema.default
    }));
  };

  const fields = getParameterFields();

  const handleJsonToggle = () => {
    if (jsonMode) {
      // Switching from JSON to form mode
      try {
        const parsed = JSON.parse(jsonText);
        Object.entries(parsed).forEach(([key, value]) => {
          onParameterChange(key, value);
        });
      } catch (err) {
        console.error('Invalid JSON:', err);
      }
    } else {
      // Switching from form to JSON mode
      setJsonText(JSON.stringify(parameters, null, 2));
    }
    setJsonMode(!jsonMode);
  };

  const handleJsonChange = (value) => {
    setJsonText(value);
    try {
      const parsed = JSON.parse(value);
      Object.entries(parsed).forEach(([key, val]) => {
        onParameterChange(key, val);
      });
    } catch (err) {
      // Invalid JSON, don't update parameters
    }
  };

  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-gray-900">Parameters</h3>
        <button
          onClick={handleJsonToggle}
          className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700"
        >
          <Code className="h-4 w-4" />
          <span>{jsonMode ? 'Form Mode' : 'JSON Mode'}</span>
        </button>
      </div>

      {jsonMode ? (
        <div>
          <textarea
            value={jsonText}
            onChange={(e) => handleJsonChange(e.target.value)}
            rows={8}
            className="w-full p-3 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter parameters as JSON..."
          />
        </div>
      ) : fields.length > 0 ? (
        <div className="space-y-4">
          {fields.map((field) => (
            <ParameterField
              key={field.name}
              field={field}
              value={parameters[field.name] || ''}
              onChange={(value) => onParameterChange(field.name, value)}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <Code className="h-8 w-8 mx-auto mb-2 text-gray-400" />
          <p>No parameter schema available</p>
          <p className="text-sm">Use JSON mode to enter parameters</p>
        </div>
      )}
    </div>
  );
}

// Individual parameter field component
function ParameterField({ field, value, onChange }) {
  const handleChange = (e) => {
    let newValue = e.target.value;
    
    // Convert value based on type
    if (field.type === 'number' || field.type === 'integer') {
      newValue = newValue === '' ? '' : Number(newValue);
    } else if (field.type === 'boolean') {
      newValue = e.target.checked;
    }
    
    onChange(newValue);
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {field.name}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {field.description && (
        <p className="text-xs text-gray-500 mb-2">{field.description}</p>
      )}
      
      {field.enum ? (
        <select
          value={value}
          onChange={handleChange}
          className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Select...</option>
          {field.enum.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      ) : field.type === 'boolean' ? (
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={value || false}
            onChange={handleChange}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Enable</span>
        </label>
      ) : field.type === 'number' || field.type === 'integer' ? (
        <input
          type="number"
          value={value}
          onChange={handleChange}
          step={field.type === 'integer' ? '1' : 'any'}
          className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={handleChange}
          className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          placeholder={field.default ? `Default: ${field.default}` : ''}
        />
      )}
    </div>
  );
}

// Result display component
function ResultDisplay({ result, onCopy }) {
  if (!result) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Results</h3>
        <div className="text-center py-8 text-gray-500">
          <Code className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p>No results yet</p>
          <p className="text-sm">Execute a tool to see results here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-gray-900">Results</h3>
        <div className="flex items-center space-x-2">
          {result.success ? (
            <div className="flex items-center space-x-1 text-green-600">
              <CheckCircle className="h-4 w-4" />
              <span className="text-sm">Success</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1 text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span className="text-sm">Error</span>
            </div>
          )}
          <button
            onClick={onCopy}
            className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-700"
          >
            <Copy className="h-4 w-4" />
            <span>Copy</span>
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* Timestamp */}
        <div className="text-xs text-gray-500">
          Executed at: {new Date(result.timestamp).toLocaleString()}
        </div>

        {/* Content */}
        <div className="border rounded-lg">
          {result.content && result.content.length > 0 ? (
            <div className="space-y-2">
              {result.content.map((item, index) => (
                <ContentItem key={index} item={item} />
              ))}
            </div>
          ) : (
            <div className="p-4 text-gray-500 text-center">No content returned</div>
          )}
        </div>

        {/* Raw JSON */}
        <details className="border rounded-lg">
          <summary className="p-3 bg-gray-50 cursor-pointer text-sm font-medium text-gray-700">
            Raw JSON Response
          </summary>
          <div className="p-3 border-t">
            <pre className="text-xs overflow-x-auto">
              {JSON.stringify(result.content, null, 2)}
            </pre>
          </div>
        </details>
      </div>
    </div>
  );
}

// Content item component
function ContentItem({ item }) {
  if (item.type === 'text') {
    return (
      <div className="p-4 bg-gray-50 rounded-lg">
        <div className="text-xs text-gray-500 mb-2">Text Content</div>
        <div className="whitespace-pre-wrap text-sm">{item.text}</div>
      </div>
    );
  }

  if (item.type === 'image') {
    return (
      <div className="p-4 bg-gray-50 rounded-lg">
        <div className="text-xs text-gray-500 mb-2">Image Content</div>
        {item.data ? (
          <img
            src={`data:${item.mimeType || 'image/png'};base64,${item.data}`}
            alt="Result"
            className="max-w-full h-auto rounded"
          />
        ) : item.url ? (
          <img src={item.url} alt="Result" className="max-w-full h-auto rounded" />
        ) : (
          <div className="text-gray-500">Image data not available</div>
        )}
      </div>
    );
  }

  // Generic content type
  return (
    <div className="p-4 bg-gray-50 rounded-lg">
      <div className="text-xs text-gray-500 mb-2">
        {item.type ? `${item.type} Content` : 'Unknown Content Type'}
      </div>
      <pre className="text-xs overflow-x-auto">
        {JSON.stringify(item, null, 2)}
      </pre>
    </div>
  );
}

export default ToolTester;