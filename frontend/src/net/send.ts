import type { ClientMessage } from '../types/contract';

/**
 * Type-checked outgoing send. Constrains the payload to the union of messages the
 * server actually handles (main.py:211-293), so a typo'd `type` or a missing field
 * fails at build time instead of being silently ignored by the server.
 */
export function sendMessage(socket: WebSocket, msg: ClientMessage): void {
  socket.send(JSON.stringify(msg));
}
