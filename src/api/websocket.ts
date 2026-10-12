import type { ConnectionState } from '../types/pico';
export class ReconnectingSocket<T> {
  private ws?: WebSocket; private timer?: number; private attempt = 0; private stopped = false;
  constructor(private url: string, private onMessage: (data: T) => void, private onState: (s: ConnectionState) => void) {}
  connect() { this.stopped = false; this.open(); }
  private open() { if (this.stopped) return; this.onState(this.attempt ? 'RECONNECTING' : 'DISCONNECTED'); this.ws = new WebSocket(this.url); this.ws.onopen = () => { this.attempt = 0; this.onState('CONNECTED'); }; this.ws.onmessage = e => { try { this.onMessage(JSON.parse(e.data) as T); } catch { /* malformed packets are ignored */ } }; this.ws.onerror = () => this.ws?.close(); this.ws.onclose = () => { if (!this.stopped) { this.onState('RECONNECTING'); const delay = Math.min(5000, 1000 * 2 ** this.attempt++); this.timer = window.setTimeout(() => this.open(), delay); } }; }
  close() { this.stopped = true; if (this.timer) window.clearTimeout(this.timer); this.ws?.close(); }
}
