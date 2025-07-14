/**
 * ServerList Component
 * Displays backend MCP servers and their status
 * Allows adding and removing servers
 */
import React, { useState, useEffect } from 'react';
import { Server, Plus, Trash2, RefreshCw, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';
import { api, getStatusColor, getStatusIcon, formatTimestamp } from '../services/api';

function ServerList() {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadServers();
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadServers, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadServers = async () => {
    try {
      const response = await api.getServers();
      setServers(response.servers || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load servers:', err);
      setError('Failed to load servers');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadServers();
  };

  const handleRemoveServer = async (serverId) => {
    if (!window.confirm(`Are you sure you want to remove server "${serverId}"?`)) {
      return;
    }

    try {
      await api.removeServer(serverId);
      await loadServers(); // Refresh the list
    } catch (err) {
      console.error('Failed to remove server:', err);
      alert('Failed to remove server: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-2 text-gray-600">Loading servers...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Backend Servers</h2>
          <p className="text-gray-600">Manage MCP server connections</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            <span>Add Server</span>
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-1 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      )}

      {/* Add server form */}
      {showAddForm && (
        <AddServerForm
          onClose={() => setShowAddForm(false)}
          onSuccess={loadServers}
        />
      )}

      {/* Servers grid */}
      {servers.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {servers.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              onRemove={handleRemoveServer}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Server className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No servers configured</h3>
          <p className="text-gray-600 mb-4">Add your first MCP server to get started</p>
          <button
            onClick={() => setShowAddForm(true)}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            <span>Add Server</span>
          </button>
        </div>
      )}
    </div>
  );
}

// Server card component
function ServerCard({ server, onRemove }) {
  const statusColor = getStatusColor(server.status);
  const statusIcon = getStatusIcon(server.status);

  const getStatusIndicator = (status) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'connecting':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center space-x-3">
          <Server className="h-6 w-6 text-gray-400" />
          <div>
            <h3 className="text-lg font-medium text-gray-900">{server.name}</h3>
            <p className="text-sm text-gray-500">{server.namespace}</p>
          </div>
        </div>
        <button
          onClick={() => onRemove(server.id)}
          className="text-red-600 hover:text-red-700 p-1"
          title="Remove server"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Status */}
      <div className="flex items-center space-x-2 mb-3">
        {getStatusIndicator(server.status)}
        <span className={`text-sm font-medium ${statusColor.split(' ')[0]}`}>
          {server.status.charAt(0).toUpperCase() + server.status.slice(1)}
        </span>
      </div>

      {/* Endpoint */}
      <div className="mb-3">
        <div className="text-sm text-gray-600">Endpoint:</div>
        <div className="text-sm font-mono text-gray-900 bg-gray-50 px-2 py-1 rounded">
          {server.endpoint}
        </div>
      </div>

      {/* Capabilities */}
      <div className="grid grid-cols-3 gap-4 mb-3">
        <div className="text-center">
          <div className="text-lg font-bold text-blue-600">{server.tool_count}</div>
          <div className="text-xs text-gray-500">Tools</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-purple-600">{server.prompt_count}</div>
          <div className="text-xs text-gray-500">Prompts</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-green-600">{server.resource_count}</div>
          <div className="text-xs text-gray-500">Resources</div>
        </div>
      </div>

      {/* Connection info */}
      <div className="text-xs text-gray-500 space-y-1">
        {server.last_connected && (
          <div>Last connected: {formatTimestamp(server.last_connected)}</div>
        )}
        {server.last_error && (
          <div className="text-red-600">Error: {server.last_error}</div>
        )}
      </div>
    </div>
  );
}

// Add server form component
function AddServerForm({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    endpoint: '',
    namespace: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.addServer(formData);
      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to add server:', err);
      setError(err.response?.data?.detail || 'Failed to add server');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-gray-900">Add New Server</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          <XCircle className="h-5 w-5" />
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Server Name
          </label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., CRM Server"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Endpoint URL
          </label>
          <input
            type="url"
            name="endpoint"
            value={formData.endpoint}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="http://server:8080"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Namespace
          </label>
          <input
            type="text"
            name="namespace"
            value={formData.namespace}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., crm"
          />
          <p className="text-xs text-gray-500 mt-1">
            Used to prefix tool names (e.g., crm.get_customer)
          </p>
        </div>

        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Adding...' : 'Add Server'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default ServerList;