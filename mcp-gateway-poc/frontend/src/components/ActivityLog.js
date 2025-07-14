/**
 * ActivityLog Component
 * Shows recent gateway activity for debugging and monitoring
 * Provides real-time updates and filtering capabilities
 */
import React, { useState, useEffect } from 'react';
import { Activity, RefreshCw, Filter, Download, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { api, formatTimestamp } from '../services/api';

function ActivityLog() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filterType, setFilterType] = useState('all');
  const [filterServer, setFilterServer] = useState('all');
  const [showSuccessOnly, setShowSuccessOnly] = useState(false);

  useEffect(() => {
    loadEvents();
    
    let interval;
    if (autoRefresh) {
      interval = setInterval(loadEvents, 5000); // Refresh every 5 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const loadEvents = async () => {
    try {
      const response = await api.getActivityLog(100);
      setEvents(response.events || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load activity log:', err);
      setError('Failed to load activity log');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadEvents();
  };

  const handleExport = () => {
    const csvContent = [
      ['Timestamp', 'Event Type', 'Details', 'Server', 'Tool', 'Success'].join(','),
      ...filteredEvents.map(event => [
        event.timestamp,
        event.event_type,
        `"${event.details.replace(/"/g, '""')}"`,
        event.server_id || '',
        event.tool_name || '',
        event.success
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mcp-gateway-activity-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Get unique event types and servers for filtering
  const getUniqueValues = (field) => {
    const values = new Set();
    events.forEach(event => {
      if (field === 'event_type') {
        values.add(event.event_type);
      } else if (field === 'server_id' && event.server_id) {
        values.add(event.server_id);
      }
    });
    return Array.from(values).sort();
  };

  // Filter events based on selected criteria
  const filteredEvents = events.filter(event => {
    if (filterType !== 'all' && event.event_type !== filterType) return false;
    if (filterServer !== 'all' && event.server_id !== filterServer) return false;
    if (showSuccessOnly && !event.success) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-2 text-gray-600">Loading activity log...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Activity Log</h2>
          <p className="text-gray-600">Monitor gateway activity and events</p>
        </div>
        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Auto-refresh</span>
          </label>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-2 px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExport}
            className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Download className="h-4 w-4" />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-1 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4 items-center">
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>
          
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Event Types</option>
            {getUniqueValues('event_type').map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          <select
            value={filterServer}
            onChange={(e) => setFilterServer(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Servers</option>
            {getUniqueValues('server_id').map(server => (
              <option key={server} value={server}>{server}</option>
            ))}
          </select>

          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={showSuccessOnly}
              onChange={(e) => setShowSuccessOnly(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Success only</span>
          </label>

          <div className="text-sm text-gray-500">
            Showing {filteredEvents.length} of {events.length} events
          </div>
        </div>
      </div>

      {/* Events list */}
      {filteredEvents.length > 0 ? (
        <div className="bg-white rounded-lg border">
          <div className="divide-y divide-gray-200">
            {filteredEvents.map((event, index) => (
              <EventItem key={`${event.timestamp}-${index}`} event={event} />
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg border p-8 text-center">
          <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {events.length === 0 ? 'No activity yet' : 'No events match your filters'}
          </h3>
          <p className="text-gray-600">
            {events.length === 0 
              ? 'Activity will appear here as the gateway processes requests'
              : 'Try adjusting your filter criteria to see more events'
            }
          </p>
        </div>
      )}
    </div>
  );
}

// Individual event item component
function EventItem({ event }) {
  const [expanded, setExpanded] = useState(false);

  const getEventIcon = (eventType, success) => {
    if (!success) {
      return <XCircle className="h-5 w-5 text-red-500" />;
    }

    switch (eventType) {
      case 'server_connected':
      case 'server_recovered':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'server_disconnected':
      case 'server_connection_failed':
      case 'server_health_check_failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'server_connecting':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'tool_called':
      case 'tool_call_completed':
        return <CheckCircle className="h-5 w-5 text-blue-500" />;
      case 'tool_call_failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  const getEventTypeColor = (eventType, success) => {
    if (!success) return 'text-red-600 bg-red-50';

    switch (eventType) {
      case 'server_connected':
      case 'server_recovered':
      case 'tool_call_completed':
        return 'text-green-600 bg-green-50';
      case 'server_disconnected':
      case 'server_connection_failed':
      case 'tool_call_failed':
        return 'text-red-600 bg-red-50';
      case 'server_connecting':
        return 'text-yellow-600 bg-yellow-50';
      case 'tool_called':
        return 'text-blue-600 bg-blue-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="p-4 hover:bg-gray-50">
      <div className="flex items-start space-x-3">
        {/* Icon */}
        <div className="flex-shrink-0 pt-1">
          {getEventIcon(event.event_type, event.success)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getEventTypeColor(event.event_type, event.success)}`}>
                {event.event_type.replace(/_/g, ' ')}
              </span>
              {event.server_id && (
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                  {event.server_id}
                </span>
              )}
              {event.tool_name && (
                <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded font-mono">
                  {event.tool_name}
                </span>
              )}
            </div>
            <div className="text-xs text-gray-500">
              {formatTimestamp(event.timestamp)}
            </div>
          </div>

          <div className="mt-1">
            <p className="text-sm text-gray-900">{event.details}</p>
          </div>

          {/* Expandable details */}
          {(event.client_id || Object.keys(event).length > 6) && (
            <div className="mt-2">
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-blue-600 hover:text-blue-700"
              >
                {expanded ? 'Hide details' : 'Show details'}
              </button>
              
              {expanded && (
                <div className="mt-2 p-3 bg-gray-50 rounded text-xs space-y-1">
                  {event.client_id && (
                    <div><span className="font-medium">Client:</span> {event.client_id}</div>
                  )}
                  <div><span className="font-medium">Timestamp:</span> {event.timestamp}</div>
                  <div><span className="font-medium">Success:</span> {event.success ? 'Yes' : 'No'}</div>
                  {Object.entries(event).map(([key, value]) => {
                    if (['timestamp', 'event_type', 'details', 'success', 'server_id', 'client_id', 'tool_name'].includes(key)) {
                      return null;
                    }
                    return (
                      <div key={key}>
                        <span className="font-medium">{key}:</span> {JSON.stringify(value)}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ActivityLog;