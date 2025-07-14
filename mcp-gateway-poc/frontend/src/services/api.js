/**
 * API Client for MCP Gateway Backend
 * Handles all HTTP requests to the FastAPI backend
 */
import axios from 'axios';

// API base configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const UI_TOKEN = process.env.REACT_APP_UI_TOKEN || 'ui-dev-token-456';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${UI_TOKEN}`
  },
  timeout: 10000
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    
    // Handle common errors
    if (error.response?.status === 401) {
      console.error('Authentication failed - check UI token');
    } else if (error.response?.status >= 500) {
      console.error('Server error - check backend status');
    }
    
    return Promise.reject(error);
  }
);

// API Methods
export const api = {
  // Gateway status and health
  async getGatewayStatus() {
    const response = await apiClient.get('/api/status');
    return response.data;
  },

  async getHealth() {
    const response = await apiClient.get('/api/health');
    return response.data;
  },

  // Backend servers management
  async getServers() {
    const response = await apiClient.get('/api/servers');
    return response.data;
  },

  async addServer(serverData) {
    const response = await apiClient.post('/api/servers', serverData);
    return response.data;
  },

  async removeServer(serverId) {
    const response = await apiClient.delete(`/api/servers/${serverId}`);
    return response.data;
  },

  async getServerStatus(serverId) {
    const response = await apiClient.get(`/api/servers/${serverId}`);
    return response.data;
  },

  // Tools and capabilities
  async getToolCatalog() {
    const response = await apiClient.get('/api/tools');
    return response.data;
  },

  async executeTool(toolName, parameters = {}) {
    const response = await apiClient.post('/api/tools/execute', {
      tool_name: toolName,
      arguments: parameters
    });
    return response.data;
  },

  // Activity monitoring
  async getActivityLog(limit = 100) {
    const response = await apiClient.get(`/api/activity?limit=${limit}`);
    return response.data;
  }
};

// Helper functions
export const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString();
};

export const getStatusColor = (status) => {
  switch (status) {
    case 'connected':
      return 'text-green-600 bg-green-100';
    case 'disconnected':
      return 'text-gray-600 bg-gray-100';
    case 'error':
      return 'text-red-600 bg-red-100';
    case 'connecting':
      return 'text-yellow-600 bg-yellow-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

export const getStatusIcon = (status) => {
  switch (status) {
    case 'connected':
      return '●';
    case 'disconnected':
      return '○';
    case 'error':
      return '✕';
    case 'connecting':
      return '◐';
    default:
      return '?';
  }
};

export default api;