# AI CLI React Client

A React TypeScript version of the AI CLI web client with the same functionality as the vanilla JS version.

## Features

- **Project Management**: Create, edit, delete, and duplicate AI projects
- **Chat Interface**: Real-time chat with AI assistant using streaming responses
- **Settings Management**: Configure global and project-specific settings
- **Tool Approval**: Interactive tool execution approval workflow
- **Command History**: Navigate through previous chat commands
- **Context Menus**: Right-click project management
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **React 18** with TypeScript
- **React Context** for state management
- **CSS3** with custom properties for theming
- **Fetch API** for HTTP requests
- **Streaming API** for real-time chat responses

## Project Structure

```
src/
├── components/          # React components
│   ├── Header.tsx       # Application header
│   ├── ProjectSelection.tsx  # Project list and management
│   ├── ChatInterface.tsx     # Chat UI and message handling
│   ├── Settings.tsx          # Settings configuration
│   ├── LoadingOverlay.tsx    # Loading state overlay
│   ├── ErrorToast.tsx        # Error notifications
│   ├── ProjectModal.tsx      # Project creation/edit modal
│   ├── ContextMenu.tsx       # Right-click context menu
│   └── SettingEditor.tsx     # Settings value editor
├── context/             # React Context providers
│   └── AppContext.tsx   # Main application state
├── services/            # API and external services
│   └── api.ts          # API client for server communication
├── types/              # TypeScript type definitions
│   └── index.ts        # Application types
├── App.tsx             # Main application component
├── App.css             # Application styles
└── index.tsx           # React entry point
```

## Getting Started

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm start
   ```

3. **Build for production:**
   ```bash
   npm run build
   ```

## API Configuration

The client expects the AI CLI server to be running on `http://localhost:8000` by default. You can change this in the settings or by modifying the initial server URL in the AppContext.

## Key Components

### AppContext
Manages all application state using React's useReducer hook:
- Current screen navigation
- Project list and current project
- Chat messages and conversation state
- Settings (global and project-specific)
- UI state (loading, errors, modals)

### API Client
Handles all communication with the AI CLI server:
- RESTful API calls for CRUD operations
- Streaming chat responses using Server-Sent Events
- Settings management endpoints
- Error handling and retry logic

### Screen Components
- **ProjectSelection**: Displays project list with create/edit/delete functionality
- **ChatInterface**: Real-time chat with message history and streaming responses
- **Settings**: Hierarchical settings management with type-specific editors

## Features Compared to Vanilla Version

✅ **Implemented:**
- Project CRUD operations
- Chat interface with streaming
- Settings management
- Error handling and loading states
- Responsive design
- TypeScript type safety

🚧 **Needs Enhancement:**
- Complete modal management system
- Advanced settings editor UI
- Tool approval workflow UI
- Command history navigation
- Keyboard shortcuts
- Context menu positioning

## Development

The React version maintains the same API contracts and functionality as the vanilla JavaScript version while providing:

- **Type Safety**: Full TypeScript support with proper type definitions
- **Component Reusability**: Modular React components
- **State Management**: Centralized state with React Context
- **Development Experience**: Hot reloading and React DevTools support

## Available Scripts

### `npm start`
Runs the app in development mode at [http://localhost:3000](http://localhost:3000)

### `npm test`
Launches the test runner in interactive watch mode

### `npm run build`
Builds the app for production to the `build` folder

## Browser Support

- Chrome/Edge 88+
- Firefox 85+
- Safari 14+

## Contributing

When adding new features:

1. Add TypeScript types to `src/types/index.ts`
2. Update the AppContext state and actions as needed
3. Create/modify components following the existing patterns
4. Update API client if new endpoints are needed
5. Add appropriate CSS classes following the naming convention
