import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import ServersList from './components/ServersList';
import ServerDetails from './components/ServerDetails';
import AllTools from './components/AllTools';
import AllPrompts from './components/AllPrompts';
import AllResources from './components/AllResources';
import ChatInterface from './components/ChatInterface';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="header">
          <div className="container">
            <h1>🔧 MCP Powered Chat</h1>
          </div>
        </header>
        
        <div className="container">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/servers" element={<ServersList />} />
            <Route path="/servers/:name" element={<ServerDetails />} />
            <Route path="/tools" element={<AllTools />} />
            <Route path="/prompts" element={<AllPrompts />} />
            <Route path="/resources" element={<AllResources />} />
            <Route path="/chat" element={<ChatInterface />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
