/**
 * Main App Component for MCP Gateway UI
 * Provides navigation, routing, and layout structure
 */
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Server, Wrench, Activity, Home, AlertCircle, CheckCircle } from 'lucide-react';

import ServerList from './components/ServerList';
import ToolCatalog from './components/ToolCatalog';
import ToolTester from './components/ToolTester';
import ActivityLog from './components/ActivityLog';
import { api } from './services/api';

// Future flags configuration for React Router v7 compatibility
const routerConfig = {
  future: {
    v7_startTransition: true,
    v7_relativeSplatPath: true
  }
};

function App() {
  const [gatewayStatus, setGatewayStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load gateway status on startup
  useEffect(() => {
    loadGatewayStatus();
    
    // Refresh status every 30 seconds
    const interval = setInterval(loadGatewayStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadGatewayStatus = async () => {
    try {
      const status = await api.getGatewayStatus();
      setGatewayStatus(status);
      setError(null);
    } catch (err) {
      console.error('Failed to load gateway status:', err);
      setError('Failed to connect to gateway backend');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Router future={routerConfig.future}>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and title */}
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Server className="h-8 w-8 text-blue-600" />
                  <h1 className="text-xl font-bold text-gray-900">MCP Gateway</h1>
                </div>
                
                {/* Status indicator */}
                <div className="flex items-center space-x-2">
                  {isLoading ? (
                    <div className="flex items-center text-gray-500">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-500"></div>
                      <span className="ml-2 text-sm">Loading...</span>
                    </div>
                  ) : error ? (
                    <div className="flex items-center text-red-600">
                      <AlertCircle className="h-4 w-4" />
                      <span className="ml-2 text-sm">Connection Error</span>
                    </div>
                  ) : gatewayStatus ? (
                    <div className="flex items-center text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      <span className="ml-2 text-sm">
                        {gatewayStatus.servers_connected}/{gatewayStatus.servers_total} servers
                      </span>
                    </div>
                  ) : null}
                </div>
              </div>

              {/* Gateway stats */}
              {gatewayStatus && (
                <div className="flex items-center space-x-6 text-sm text-gray-600">
                  <div>
                    <span className="font-medium">{gatewayStatus.total_tools}</span> tools
                  </div>
                  <div>
                    <span className="font-medium">{gatewayStatus.total_prompts}</span> prompts
                  </div>
                  <div>
                    <span className="font-medium">{gatewayStatus.total_resources}</span> resources
                  </div>
                  <div>
                    Uptime: <span className="font-medium">{formatUptime(gatewayStatus.uptime_seconds)}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Navigation */}
        <Navigation />

        {/* Main content */}
        <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          {error ? (
            <ErrorBanner error={error} onRetry={loadGatewayStatus} />
          ) : (
            <Routes>
              <Route path="/" element={<Dashboard gatewayStatus={gatewayStatus} />} />
              <Route path="/servers" element={<ServerList />} />
              <Route path="/tools" element={<ToolCatalog />} />
              <Route path="/tester" element={<ToolTester />} />
              <Route path="/activity" element={<ActivityLog />} />
            </Routes>
          )}
        </main>
      </div>
    </Router>
  );
}

// Navigation component
function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/servers', label: 'Servers', icon: Server },
    { path: '/tools', label: 'Tools', icon: Wrench },
    { path: '/tester', label: 'Tester', icon: Wrench },
    { path: '/activity', label: 'Activity', icon: Activity }
  ];

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex space-x-8">
          {navItems.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={`flex items-center space-x-2 py-4 px-1 border-b-2 text-sm font-medium transition-colors ${
                location.pathname === path
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

// Dashboard component
function Dashboard({ gatewayStatus }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Gateway Dashboard</h2>
        <p className="text-gray-600">Monitor and manage your MCP Gateway</p>
      </div>

      {gatewayStatus && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Gateway Status"
            value={gatewayStatus.status}
            valueClass={gatewayStatus.status === 'healthy' ? 'text-green-600' : 'text-yellow-600'}
          />
          <StatCard
            title="Connected Servers"
            value={`${gatewayStatus.servers_connected} / ${gatewayStatus.servers_total}`}
            valueClass="text-blue-600"
          />
          <StatCard
            title="Available Tools"
            value={gatewayStatus.total_tools}
            valueClass="text-purple-600"
          />
          <StatCard
            title="Uptime"
            value={formatUptime(gatewayStatus.uptime_seconds)}
            valueClass="text-gray-600"
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <QuickLinks />
        <RecentActivity />
      </div>
    </div>
  );
}

// Stat card component
function StatCard({ title, value, valueClass = 'text-gray-900' }) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="text-sm font-medium text-gray-500">{title}</div>
      <div className={`text-2xl font-bold ${valueClass}`}>{value}</div>
    </div>
  );
}

// Quick links component
function QuickLinks() {
  const links = [
    { to: '/servers', title: 'Manage Servers', description: 'Add, remove, and monitor backend servers' },
    { to: '/tools', title: 'Browse Tools', description: 'Explore available tools and capabilities' },
    { to: '/tester', title: 'Test Tools', description: 'Execute tools and test functionality' },
    { to: '/activity', title: 'View Activity', description: 'Monitor gateway activity and logs' }
  ];

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
      <div className="space-y-3">
        {links.map(({ to, title, description }) => (
          <Link
            key={to}
            to={to}
            className="block p-3 rounded-lg border hover:bg-gray-50 transition-colors"
          >
            <div className="font-medium text-gray-900">{title}</div>
            <div className="text-sm text-gray-500">{description}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// Recent activity component
function RecentActivity() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRecentActivity();
  }, []);

  const loadRecentActivity = async () => {
    try {
      const response = await api.getActivityLog(5);
      setActivities(response.events || []);
    } catch (error) {
      console.error('Failed to load recent activity:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
        <Link to="/activity" className="text-sm text-blue-600 hover:text-blue-700">
          View all
        </Link>
      </div>
      
      {loading ? (
        <div className="text-center py-4 text-gray-500">Loading...</div>
      ) : activities.length > 0 ? (
        <div className="space-y-3">
          {activities.map((activity, index) => (
            <div key={index} className="text-sm">
              <div className="flex justify-between">
                <span className="text-gray-900">{activity.details}</span>
                <span className="text-gray-500">
                  {new Date(activity.timestamp).toLocaleTimeString()}
                </span>
              </div>
              {activity.server_id && (
                <div className="text-gray-500">Server: {activity.server_id}</div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-4 text-gray-500">No recent activity</div>
      )}
    </div>
  );
}

// Error banner component
function ErrorBanner({ error, onRetry }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex">
        <AlertCircle className="h-5 w-5 text-red-400" />
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
          <div className="mt-2 text-sm text-red-700">{error}</div>
          <div className="mt-4">
            <button
              onClick={onRetry}
              className="bg-red-100 text-red-800 px-3 py-1 rounded text-sm hover:bg-red-200"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper functions
function formatUptime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m`;
  } else {
    return `${seconds}s`;
  }
}

export default App;