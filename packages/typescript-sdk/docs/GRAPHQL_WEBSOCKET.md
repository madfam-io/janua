# GraphQL & WebSocket Client Integration

This document describes the GraphQL and WebSocket client integrations added to the Janua TypeScript SDK.

## Overview

The SDK now includes two powerful real-time features:

1. **GraphQL Client** - Type-safe GraphQL queries, mutations, and subscriptions using Apollo Client
2. **WebSocket Client** - Real-time bidirectional communication with automatic reconnection

## GraphQL Client

### Configuration

Enable GraphQL by providing `graphqlUrl` (and optionally `graphqlWsUrl` for subscriptions) in the SDK configuration:

```typescript
import { createClient } from '@janua/typescript-sdk';

const client = createClient({
  baseURL: 'https://api.janua.dev',
  graphqlUrl: 'https://api.janua.dev/graphql',
  graphqlWsUrl: 'wss://api.janua.dev/graphql', // Optional, for subscriptions
});
```

### Usage

#### Queries

Execute GraphQL queries with type safety:

```typescript
import { gql } from '@apollo/client';

const GET_USER = gql`
  query GetUser($id: ID!) {
    user(id: $id) {
      id
      email
      firstName
      lastName
    }
  }
`;

const result = await client.graphql!.query<GetUserData, GetUserVariables>(GET_USER, {
  variables: { id: 'user-123' },
  fetchPolicy: 'network-only',
});

console.log(result.data.user);
```

#### Mutations

Execute GraphQL mutations:

```typescript
const UPDATE_PROFILE = gql`
  mutation UpdateProfile($input: ProfileInput!) {
    updateProfile(input: $input) {
      id
      firstName
      lastName
    }
  }
`;

const result = await client.graphql!.mutate<UpdateProfileData, UpdateProfileVariables>(
  UPDATE_PROFILE,
  {
    variables: {
      input: {
        firstName: 'John',
        lastName: 'Doe',
      },
    },
  }
);

console.log(result.data?.updateProfile);
```

#### Subscriptions

Subscribe to real-time data updates:

```typescript
const USER_UPDATED = gql`
  subscription UserUpdated($userId: ID!) {
    userUpdated(userId: $userId) {
      id
      email
      firstName
      lastName
    }
  }
`;

const subscription = client.graphql!.subscribe<UserUpdatedData, UserUpdatedVariables>(
  USER_UPDATED,
  {
    variables: { userId: 'user-123' },
  }
);

subscription.subscribe({
  next: ({ data }) => {
    console.log('User updated:', data?.userUpdated);
  },
  error: (error) => {
    console.error('Subscription error:', error);
  },
  complete: () => {
    console.log('Subscription complete');
  },
});
```

### Features

- **Automatic Authentication** - Access tokens automatically included in requests
- **Apollo Client** - Industry-leading GraphQL client with powerful caching
- **Type Safety** - Full TypeScript support for queries, mutations, and subscriptions
- **Cache Management** - Built-in caching with methods to clear/reset cache
- **Error Handling** - Comprehensive error handling and logging
- **WebSocket Subscriptions** - Real-time data subscriptions via GraphQL over WebSocket

### API Reference

#### `GraphQL` Class

```typescript
class GraphQL {
  // Execute a query
  query<TData, TVariables>(
    query: DocumentNode,
    options?: GraphQLQueryOptions<TVariables>
  ): Promise<ApolloQueryResult<TData>>

  // Execute a mutation
  mutate<TData, TVariables>(
    mutation: DocumentNode,
    options?: GraphQLMutationOptions<TVariables>
  ): Promise<FetchResult<TData>>

  // Subscribe to updates
  subscribe<TData, TVariables>(
    subscription: DocumentNode,
    options?: GraphQLSubscriptionOptions<TVariables>
  ): Observable<FetchResult<TData>>

  // Clear cache
  clearCache(): Promise<void>

  // Reset store
  resetStore(): Promise<void>

  // Get underlying Apollo Client
  getClient(): ApolloClient<NormalizedCacheObject>

  // Disconnect WebSocket
  disconnect(): Promise<void>

  // Check subscription support
  hasSubscriptionSupport(): boolean
}
```

---

## WebSocket Client

### Configuration

Enable WebSocket by providing `wsUrl` in the SDK configuration:

```typescript
import { createClient } from '@janua/typescript-sdk';

const client = createClient({
  baseURL: 'https://api.janua.dev',
  wsUrl: 'wss://api.janua.dev/ws',
  wsAutoConnect: true, // Auto-connect on initialization (default: true)
  wsReconnect: true, // Enable auto-reconnection (default: true)
  wsReconnectInterval: 5000, // Reconnect delay in ms (default: 5000)
  wsReconnectAttempts: 5, // Max reconnection attempts (default: 5)
  wsHeartbeatInterval: 30000, // Heartbeat interval in ms (default: 30000)
});
```

### Usage

#### Connect/Disconnect

```typescript
// Connect manually (if wsAutoConnect is false)
await client.ws!.connect();

// Disconnect
client.ws!.disconnect();

// Check connection status
const isConnected = client.ws!.isConnected();
const status = client.ws!.getStatus(); // 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error'
```

#### Send Messages

```typescript
// Send a message
client.ws!.send({
  type: 'message',
  data: { text: 'Hello, WebSocket!' },
});
```

#### Subscribe to Channels

```typescript
// Subscribe to a channel
client.ws!.subscribe('notifications');

// Listen for messages
client.ws!.on('message', (message) => {
  if (message.channel === 'notifications') {
    console.log('Notification:', message.data);
  }
});

// Unsubscribe from a channel
client.ws!.unsubscribe('notifications');

// Get subscribed channels
const channels = client.ws!.getChannels();
```

#### Publish to Channels

```typescript
// Publish a message to a channel
client.ws!.publish('chat', {
  message: 'Hello, everyone!',
  userId: 'user-123',
}, 'message_sent');
```

#### Event Handling

```typescript
// Connection events
client.ws!.on('connected', ({ timestamp }) => {
  console.log('WebSocket connected at:', new Date(timestamp));
});

client.ws!.on('disconnected', ({ code, reason }) => {
  console.log(`WebSocket disconnected: ${code} - ${reason}`);
});

client.ws!.on('reconnecting', ({ attempt, maxAttempts }) => {
  console.log(`Reconnecting... (${attempt}/${maxAttempts})`);
});

client.ws!.on('reconnected', ({ timestamp }) => {
  console.log('WebSocket reconnected at:', new Date(timestamp));
});

// Message events
client.ws!.on('message', (message) => {
  console.log('Received message:', message);
});

// Error events
client.ws!.on('error', ({ error }) => {
  console.error('WebSocket error:', error);
});
```

### Features

- **Automatic Reconnection** - Configurable auto-reconnect with exponential backoff
- **Authentication** - Access tokens automatically included in connection
- **Heartbeat** - Automatic ping/pong to keep connection alive
- **Channel Subscriptions** - Subscribe to specific data channels
- **Event System** - Comprehensive event system for connection lifecycle
- **Type Safety** - Full TypeScript support for messages and events
- **Status Monitoring** - Real-time connection status tracking

### API Reference

#### `WebSocket` Class

```typescript
class WebSocket extends EventEmitter<WebSocketEventMap> {
  // Connect to server
  connect(): Promise<void>

  // Disconnect from server
  disconnect(): void

  // Send a message
  send(message: WebSocketMessage): void

  // Subscribe to a channel
  subscribe(channel: string): void

  // Unsubscribe from a channel
  unsubscribe(channel: string): void

  // Publish to a channel
  publish(channel: string, data: any, event?: string): void

  // Get connection status
  getStatus(): WebSocketStatus

  // Check if connected
  isConnected(): boolean

  // Get subscribed channels
  getChannels(): string[]
}
```

#### `WebSocketMessage` Interface

```typescript
interface WebSocketMessage {
  type: string          // Message type (e.g., 'subscribe', 'publish', 'message')
  channel?: string      // Optional channel name
  data?: any           // Message payload
  event?: string       // Optional event name
  timestamp?: number   // Message timestamp
}
```

#### `WebSocketStatus` Type

```typescript
type WebSocketStatus = 
  | 'connecting'     // Initial connection in progress
  | 'connected'      // Successfully connected
  | 'disconnected'   // Not connected
  | 'reconnecting'   // Attempting to reconnect
  | 'error'          // Connection error
```

---

## Advanced Usage

### Using Both GraphQL and WebSocket

Combine GraphQL queries with WebSocket subscriptions for powerful real-time applications:

```typescript
import { createClient } from '@janua/typescript-sdk';
import { gql } from '@apollo/client';

const client = createClient({
  baseURL: 'https://api.janua.dev',
  graphqlUrl: 'https://api.janua.dev/graphql',
  graphqlWsUrl: 'wss://api.janua.dev/graphql',
  wsUrl: 'wss://api.janua.dev/ws',
});

// Initial data load via GraphQL
const GET_MESSAGES = gql`
  query GetMessages($channelId: ID!) {
    messages(channelId: $channelId) {
      id
      text
      userId
      createdAt
    }
  }
`;

const { data } = await client.graphql!.query(GET_MESSAGES, {
  variables: { channelId: 'channel-123' },
});

console.log('Initial messages:', data.messages);

// Real-time updates via WebSocket
client.ws!.subscribe('channel-123');

client.ws!.on('message', (message) => {
  if (message.channel === 'channel-123' && message.event === 'new_message') {
    console.log('New message received:', message.data);
    // Update local state with new message
  }
});

// Send messages via WebSocket
client.ws!.publish('channel-123', {
  text: 'Hello!',
  userId: 'user-456',
}, 'new_message');
```

### Custom Cache Configuration

Configure Apollo Client cache for optimal performance:

```typescript
import { InMemoryCache } from '@apollo/client/core';
import { createGraphQLClient } from '@janua/typescript-sdk';

const cache = new InMemoryCache({
  typePolicies: {
    Query: {
      fields: {
        user: {
          read(existing, { args, toReference }) {
            return existing || toReference({
              __typename: 'User',
              id: args?.id,
            });
          },
        },
      },
    },
  },
});

const graphqlClient = createGraphQLClient({
  httpUrl: 'https://api.janua.dev/graphql',
  wsUrl: 'wss://api.janua.dev/graphql',
  cache,
  getAuthToken: () => client.getAccessToken(),
  debug: true,
});
```

### Error Handling

Both clients provide comprehensive error handling:

```typescript
// GraphQL errors
try {
  const result = await client.graphql!.query(GET_USER, {
    variables: { id: 'invalid-id' },
  });
} catch (error) {
  if (error.graphQLErrors) {
    error.graphQLErrors.forEach((err) => {
      console.error('GraphQL error:', err.message);
    });
  }
  if (error.networkError) {
    console.error('Network error:', error.networkError);
  }
}

// WebSocket errors
client.ws!.on('error', ({ error }) => {
  console.error('WebSocket error:', error.message);
  
  // Handle specific error cases
  if (error.message.includes('authentication')) {
    // Re-authenticate
  }
});
```

---

## TypeScript Types

All GraphQL and WebSocket functionality is fully typed:

```typescript
import type {
  GraphQLConfig,
  GraphQLQueryOptions,
  GraphQLMutationOptions,
  GraphQLSubscriptionOptions,
  WebSocketConfig,
  WebSocketMessage,
  WebSocketEventMap,
  WebSocketStatus,
} from '@janua/typescript-sdk';
```

---

## Dependencies

The following dependencies are required for GraphQL and WebSocket functionality:

```json
{
  "dependencies": {
    "@apollo/client": "^3.8.0",
    "graphql": "^16.8.0",
    "graphql-ws": "^5.14.0"
  }
}
```

These are marked as peer dependencies and optional in the SDK, so they're only required if you use the GraphQL or WebSocket features.

---

## Best Practices

### GraphQL

1. **Use Fragments** - Define reusable fragments for common data structures
2. **Cache Optimization** - Configure cache policies appropriate for your data patterns
3. **Error Handling** - Always handle both GraphQL and network errors
4. **Type Generation** - Use GraphQL Code Generator for type-safe operations
5. **Subscription Cleanup** - Always unsubscribe when component unmounts

### WebSocket

1. **Connection Management** - Use `wsAutoConnect: false` for manual connection control
2. **Reconnection Strategy** - Configure reconnection attempts based on your use case
3. **Channel Management** - Unsubscribe from channels when no longer needed
4. **Message Validation** - Validate incoming messages before processing
5. **Heartbeat Tuning** - Adjust heartbeat interval based on network conditions

---

## Examples

Complete examples are available in the `examples/` directory:

- `examples/graphql-basic.ts` - Basic GraphQL queries and mutations
- `examples/graphql-subscriptions.ts` - Real-time GraphQL subscriptions
- `examples/websocket-chat.ts` - WebSocket-based chat application
- `examples/realtime-dashboard.ts` - Combined GraphQL + WebSocket dashboard

---

## Troubleshooting

### GraphQL Subscription Connection Fails

**Problem**: Subscriptions fail to connect even with `graphqlWsUrl` configured.

**Solution**: Ensure your GraphQL server supports WebSocket subscriptions using the `graphql-ws` protocol.

### WebSocket Reconnection Loop

**Problem**: WebSocket continuously reconnects and disconnects.

**Solution**: Check authentication token validity. WebSocket closes on auth failures. Use `wsReconnectAttempts` to limit reconnection attempts.

### High Memory Usage with Apollo Client

**Problem**: Memory usage increases over time with many queries.

**Solution**: Configure cache eviction policies and use `clearCache()` or `resetStore()` periodically:

```typescript
// Clear cache every hour
setInterval(() => {
  client.graphql!.clearCache();
}, 3600000);
```

---

## Migration Guide

If you're upgrading from an older version of the SDK:

### Enabling GraphQL

Add the GraphQL URL to your configuration:

```typescript
// Before
const client = createClient({
  baseURL: 'https://api.janua.dev',
});

// After
const client = createClient({
  baseURL: 'https://api.janua.dev',
  graphqlUrl: 'https://api.janua.dev/graphql',
  graphqlWsUrl: 'wss://api.janua.dev/graphql',
});
```

### Enabling WebSocket

Add the WebSocket URL to your configuration:

```typescript
// Before
const client = createClient({
  baseURL: 'https://api.janua.dev',
});

// After
const client = createClient({
  baseURL: 'https://api.janua.dev',
  wsUrl: 'wss://api.janua.dev/ws',
});
```

---

## Support

For issues, questions, or feature requests:

- GitHub Issues: https://github.com/madfam-io/janua/issues
- Documentation: https://docs.janua.dev
- Community: https://community.janua.dev

---

## License

AGPL-3.0 License - see LICENSE file for details.
