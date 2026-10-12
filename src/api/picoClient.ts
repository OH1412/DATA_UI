import { ReconnectingSocket } from './websocket';
import type { EventMessage, StatusResponse, Telemetry, VideoMessage, ConnectionState } from '../types/pico';
export const DEFAULT_BASE = 'http://127.0.0.1:8765';
export class PicoClient {
  telemetry?: ReconnectingSocket<Telemetry>; video?: ReconnectingSocket<VideoMessage>; events?: ReconnectingSocket<EventMessage>;
  constructor(private base = DEFAULT_BASE, private onTelemetry: (m: Telemetry) => void, private onVideo: (m: VideoMessage) => void, private onEvent: (m: EventMessage) => void, private onState: (channel: string, s: ConnectionState) => void) {}
  connect() { this.telemetry = new ReconnectingSocket(`${this.base.replace('http','ws')}/ws/telemetry`, this.onTelemetry, s => this.onState('telemetry', s)); this.video = new ReconnectingSocket(`${this.base.replace('http','ws')}/ws/video`, this.onVideo, s => this.onState('video', s)); this.events = new ReconnectingSocket(`${this.base.replace('http','ws')}/ws/events`, this.onEvent, s => this.onState('events', s)); this.telemetry.connect(); this.video.connect(); this.events.connect(); }
  disconnect() { this.telemetry?.close(); this.video?.close(); this.events?.close(); }
  async status() { const r = await fetch(`${this.base}/api/status`); return await r.json() as StatusResponse; }
  async command(command: string, params = {}) { const r = await fetch(`${this.base}/api/command`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ command, params }) }); if (!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); }
}
