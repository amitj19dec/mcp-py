# MCP Gateway React UI

Modern React frontend for the MCP Gateway POC. Provides a comprehensive management interface for monitoring and controlling the MCP Gateway.

## Features

### 🏠 Dashboard
- **Gateway Status Overview**: Real-time status of the gateway and connected servers
- **Quick Actions**: Fast access to common management tasks
- **Statistics**: Tools, prompts, resources counts and uptime
- **Recent Activity**: Latest events and operations

### 🖥️ Server Management
- **Server List**: View all backend MCP servers and their status
- **Add/Remove Servers**: Dynamic server management
- **Health Monitoring**: Real-time connection status and health checks
- **Server Details**: Tool counts, connection info, and error messages

### 🛠️ Tool Catalog
- **Unified View**: Browse all tools, prompts, and resources from connected servers
- **Search & Filter**: Find capabilities by name, description, or source server
- **Namespace Organization**: Clear separation of tools by server namespace
- **Schema Inspection**: View tool parameters and documentation

### 🧪 Tool Tester
- **Interactive Testing**: Execute any tool directly through the UI
- **Dynamic Forms**: Auto-generated parameter inputs based on tool schemas
- **JSON Mode**: Advanced parameter input for complex data structures
- **Result Display**: Formatted tool responses with error handling

### 📊 Activity Monitor
- **Real-time Log**: Live stream of gateway activity and events
- **Filtering**: Filter by event type, server, or success status
- **Export**: Download activity logs for analysis
- **Auto-refresh**: Configurable automatic updates

## Technology Stack

- **React 18**: Modern React with hooks and functional components
- **React Router**: Client-side routing for single-page application
- **Tailwind CSS**: Utility-first CSS framework for responsive design
- **Axios**: HTTP client for API communication
- **Lucide React**: Beautiful icon library
- **Create React App**: Build tooling and development server

## Quick Start

### Prerequisites
- Node.js 16+ and npm
- Running MCP Gateway backend

### Installation

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Configure environment**:
```bash
cp .env.template .env.local
# Edit .env.local with your backend URL and token
```

3. **Start development server**:
```bash
npm start
```

4. **Open in browser**: http://localhost:3000

## Configuration

### Environment Variables

Copy `.env.template` to `.env.local` and configure:

```env
# Backend API configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_UI_TOKEN=ui-dev-token-456

# Feature flags
REACT_APP_ENABLE_DEBUG=true
REACT_APP_ENABLE_AUTO_REFRESH=true

# Refresh intervals (milliseconds)
REACT_APP_SERVER_REFRESH_INTERVAL=10000
REACT_APP_ACTIVITY_REFRESH_INTERVAL=5000
REACT_APP_STATUS_REFRESH_INTERVAL=30000
```

### Available Environments

- **Development** (`.env.development`): Debug enabled, fast refresh
- **Production** (`.env.production`): Optimized for production deployment
- **Local** (`.env.local`): Your personal overrides (gitignored)

## Project Structure

```
frontend/
├── public/
│   └── index.html              # HTML template
├── src/
│   ├── components/             # React components
│   │   ├── ServerList.js       # Server management
│   │   ├── ToolCatalog.js      # Tool browsing
│   │   ├── ToolTester.js       # Tool execution
│   │   └── ActivityLog.js      # Activity monitoring
│   ├── services/
│   │   └── api.js              # API client and utilities
│   ├── App.js                  # Main application component
│   ├── index.js                # Application entry point
│   └── index.css               # Global styles and Tailwind
├── .env.template               # Environment configuration template
├── .env.development            # Development environment
├── .env.production             # Production environment
├── tailwind.config.js          # Tailwind CSS configuration
├── postcss.config.js           # PostCSS configuration
└── package.json                # Dependencies and scripts
```

## API Integration

### Authentication
The UI authenticates with the backend using a bearer token:
```javascript
headers: {
  'Authorization': `Bearer ${UI_TOKEN}`
}
```

### Available Endpoints
- `GET /api/status` - Gateway status
- `GET /api/servers` - Backend servers list
- `POST /api/servers` - Add new server
- `DELETE /api/servers/{id}` - Remove server
- `GET /api/tools` - Tool catalog
- `POST /api/tools/execute` - Execute tool
- `GET /api/activity` - Activity log

### Error Handling
- Automatic retry for network errors
- User-friendly error messages
- Graceful degradation when backend unavailable

## Development

### Available Scripts

```bash
# Start development server with hot reload
npm start

# Build production bundle
npm build

# Analyze bundle size
npm run build && npx serve -s build
```

### Code Organization

#### Components
- **Functional Components**: Using React hooks for state management
- **Reusable UI Elements**: Consistent design patterns
- **Responsive Design**: Works on desktop, tablet, and mobile

#### State Management
- **Local State**: useState for component-specific data
- **API State**: Direct API calls with loading/error states
- **No Redux**: Kept simple for POC scope

#### Styling
- **Tailwind CSS**: Utility-first approach
- **Custom Components**: Reusable design system
- **Responsive**: Mobile-first design
- **Accessible**: WCAG compliance considerations

### Adding New Features

1. **Create Component**: Add to `src/components/`
2. **Add Route**: Update routing in `App.js`
3. **API Integration**: Extend `services/api.js`
4. **Navigation**: Add to navigation menu

## Deployment

### Production Build

```bash
# Create optimized production build
npm run build

# Files will be in build/ directory
ls build/
```

### Static File Hosting

Deploy the `build/` directory to any static file host:

- **Azure Static Web Apps**: `az staticwebapp create`
- **Netlify**: Drag and drop build folder
- **Vercel**: `vercel deploy`
- **AWS S3**: `aws s3 sync build/ s3://bucket-name`

### Docker Deployment

```dockerfile
FROM nginx:alpine
COPY build/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### Environment Configuration

Set production environment variables during build:

```bash
# For static deployments
REACT_APP_API_URL=https://your-gateway.com npm run build

# For Docker builds
docker build --build-arg REACT_APP_API_URL=https://your-gateway.com .
```

## Customization

### Theming

Modify `tailwind.config.js` to customize:
- Colors and branding
- Typography and fonts
- Spacing and layout
- Component styles

### Feature Flags

Control features via environment variables:
```env
REACT_APP_ENABLE_DEBUG=false          # Disable debug logging
REACT_APP_ENABLE_AUTO_REFRESH=false   # Disable auto-refresh
```

### API Configuration

Customize API behavior in `services/api.js`:
- Request timeouts
- Retry logic
- Error handling
- Response formatting

## Troubleshooting

### Common Issues

1. **Cannot connect to backend**
   - Check `REACT_APP_API_URL` in `.env.local`
   - Verify backend is running on correct port
   - Check CORS configuration in backend

2. **Authentication errors**
   - Verify `REACT_APP_UI_TOKEN` matches backend `UI_TOKEN`
   - Check token format (no extra spaces)

3. **Build errors**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Check Node.js version compatibility
   - Verify all dependencies are installed

4. **Style issues**
   - Rebuild Tailwind: `npm run build`
   - Check PostCSS configuration
   - Verify Tailwind directives in CSS

### Debug Mode

Enable debug logging:
```env
REACT_APP_ENABLE_DEBUG=true
```

Check browser console for detailed logs of:
- API requests and responses
- Component state changes
- Error details

### Network Issues

Check network tab in browser developer tools:
- API request URLs
- Response status codes
- CORS errors
- Authentication headers

## Performance

### Optimization Features
- **Code Splitting**: Automatic route-based splitting
- **Tree Shaking**: Remove unused code
- **Minification**: Compressed production builds
- **Caching**: Long-term caching with hash-based filenames

### Monitoring
- **Auto-refresh**: Configurable intervals to reduce load
- **Efficient Updates**: Only fetch changed data
- **Error Boundaries**: Graceful error handling

## Security

### Authentication
- Bearer token authentication
- Configurable token via environment variables
- No sensitive data in localStorage

### API Security
- All API calls include authentication headers
- HTTPS recommended for production
- CORS properly configured

### Content Security
- No inline scripts or styles
- Sanitized user inputs
- Safe HTML rendering

## Browser Support

- **Modern Browsers**: Chrome 88+, Firefox 85+, Safari 14+, Edge 88+
- **Mobile**: iOS Safari 14+, Chrome Android 88+
- **Features**: ES6+, CSS Grid, Flexbox, Web APIs

## Contributing

### Development Setup
1. Fork and clone repository
2. Install dependencies: `npm install`
3. Copy environment template: `cp .env.template .env.local`
4. Start development: `npm start`

### Code Standards
- ESLint configuration included
- Prettier for code formatting
- Consistent component patterns
- TypeScript ready (add types as needed)

## Next Steps

This POC frontend provides the foundation for:

1. **Enhanced UI**: Advanced data visualization and charts
2. **Real-time Updates**: WebSocket integration for live updates
3. **Advanced Features**: Bulk operations, advanced filtering
4. **Enterprise Integration**: SSO, RBAC, audit trails
5. **Mobile App**: React Native or PWA conversion

The modular architecture makes it easy to extend and customize for specific enterprise requirements.
