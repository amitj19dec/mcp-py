/**
 * ToolCatalog Component
 * Displays aggregated tools, prompts, and resources from all servers
 * Provides search and filtering capabilities
 */
import React, { useState, useEffect } from 'react';
import { Wrench, Search, Filter, MessageSquare, FileText, ExternalLink } from 'lucide-react';
import { api } from '../services/api';

function ToolCatalog() {
  const [catalog, setCatalog] = useState({ tools: [], prompts: [], resources: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('tools');
  const [selectedServer, setSelectedServer] = useState('all');

  useEffect(() => {
    loadCatalog();
  }, []);

  const loadCatalog = async () => {
    try {
      const response = await api.getToolCatalog();
      setCatalog(response);
      setError(null);
    } catch (err) {
      console.error('Failed to load tool catalog:', err);
      setError('Failed to load tool catalog');
    } finally {
      setLoading(false);
    }
  };

  // Get unique servers for filtering
  const getUniqueServers = () => {
    const servers = new Set();
    [...catalog.tools, ...catalog.prompts, ...catalog.resources].forEach(item => {
      servers.add(item.source_server);
    });
    return Array.from(servers).sort();
  };

  // Filter items based on search and server selection
  const filterItems = (items) => {
    return items.filter(item => {
      const matchesSearch = !searchTerm || 
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.description && item.description.toLowerCase().includes(searchTerm.toLowerCase()));
      
      const matchesServer = selectedServer === 'all' || item.source_server === selectedServer;
      
      return matchesSearch && matchesServer;
    });
  };

  const filteredTools = filterItems(catalog.tools || []);
  const filteredPrompts = filterItems(catalog.prompts || []);
  const filteredResources = filterItems(catalog.resources || []);

  const tabs = [
    { id: 'tools', label: 'Tools', count: filteredTools.length, icon: Wrench },
    { id: 'prompts', label: 'Prompts', count: filteredPrompts.length, icon: MessageSquare },
    { id: 'resources', label: 'Resources', count: filteredResources.length, icon: FileText }
  ];

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-2 text-gray-600">Loading catalog...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Catalog</h3>
        <p className="text-red-700">{error}</p>
        <button
          onClick={loadCatalog}
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
        <h2 className="text-2xl font-bold text-gray-900">Tool Catalog</h2>
        <p className="text-gray-600">Browse available tools, prompts, and resources</p>
      </div>

      {/* Search and filters */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <input
              type="text"
              placeholder="Search tools, prompts, and resources..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Server filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <select
              value={selectedServer}
              onChange={(e) => setSelectedServer(e.target.value)}
              className="pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Servers</option>
              {getUniqueServers().map(server => (
                <option key={server} value={server}>{server}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map(({ id, label, count, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
              <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded-full text-xs">
                {count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div>
        {activeTab === 'tools' && <ToolsList tools={filteredTools} />}
        {activeTab === 'prompts' && <PromptsList prompts={filteredPrompts} />}
        {activeTab === 'resources' && <ResourcesList resources={filteredResources} />}
      </div>
    </div>
  );
}

// Tools list component
function ToolsList({ tools }) {
  if (tools.length === 0) {
    return (
      <div className="text-center py-8">
        <Wrench className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No tools found</h3>
        <p className="text-gray-600">Try adjusting your search or filter criteria</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {tools.map((tool, index) => (
        <ToolCard key={`${tool.source_server}-${tool.name}-${index}`} tool={tool} />
      ))}
    </div>
  );
}

// Tool card component
function ToolCard({ tool }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <Wrench className="h-5 w-5 text-blue-600" />
          <h3 className="font-medium text-gray-900 text-sm">{tool.name}</h3>
        </div>
        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
          {tool.namespace}
        </span>
      </div>

      <p className="text-sm text-gray-600 mb-3">
        {tool.description || 'No description available'}
      </p>

      <div className="text-xs text-gray-500 mb-3">
        Source: {tool.source_server}
      </div>

      {tool.input_schema && (
        <div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {showDetails ? 'Hide' : 'Show'} Parameters
          </button>
          
          {showDetails && tool.input_schema && (
            <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
              <pre className="whitespace-pre-wrap">
                {JSON.stringify(tool.input_schema, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Prompts list component
function PromptsList({ prompts }) {
  if (prompts.length === 0) {
    return (
      <div className="text-center py-8">
        <MessageSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No prompts found</h3>
        <p className="text-gray-600">Try adjusting your search or filter criteria</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {prompts.map((prompt, index) => (
        <PromptCard key={`${prompt.source_server}-${prompt.name}-${index}`} prompt={prompt} />
      ))}
    </div>
  );
}

// Prompt card component
function PromptCard({ prompt }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <MessageSquare className="h-5 w-5 text-purple-600" />
          <h3 className="font-medium text-gray-900 text-sm">{prompt.name}</h3>
        </div>
        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
          {prompt.namespace}
        </span>
      </div>

      <p className="text-sm text-gray-600 mb-3">
        {prompt.description || 'No description available'}
      </p>

      <div className="text-xs text-gray-500 mb-3">
        Source: {prompt.source_server}
      </div>

      {prompt.arguments && prompt.arguments.length > 0 && (
        <div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm text-purple-600 hover:text-purple-700"
          >
            {showDetails ? 'Hide' : 'Show'} Arguments
          </button>
          
          {showDetails && (
            <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
              <pre className="whitespace-pre-wrap">
                {JSON.stringify(prompt.arguments, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Resources list component
function ResourcesList({ resources }) {
  if (resources.length === 0) {
    return (
      <div className="text-center py-8">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No resources found</h3>
        <p className="text-gray-600">Try adjusting your search or filter criteria</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {resources.map((resource, index) => (
        <ResourceCard key={`${resource.source_server}-${resource.name}-${index}`} resource={resource} />
      ))}
    </div>
  );
}

// Resource card component
function ResourceCard({ resource }) {
  return (
    <div className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <FileText className="h-5 w-5 text-green-600" />
          <h3 className="font-medium text-gray-900 text-sm">{resource.name}</h3>
        </div>
        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
          {resource.namespace}
        </span>
      </div>

      <p className="text-sm text-gray-600 mb-3">
        {resource.description || 'No description available'}
      </p>

      <div className="text-xs text-gray-500 space-y-1">
        <div>Source: {resource.source_server}</div>
        {resource.uri && (
          <div className="flex items-center space-x-1">
            <span>URI:</span>
            <a
              href={resource.uri}
              target="_blank"
              rel="noopener noreferrer"
              className="text-green-600 hover:text-green-700 flex items-center space-x-1"
            >
              <span className="font-mono">{resource.uri}</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        )}
        {resource.mime_type && (
          <div>Type: <span className="font-mono">{resource.mime_type}</span></div>
        )}
      </div>
    </div>
  );
}

export default ToolCatalog;