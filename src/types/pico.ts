export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number];
export type ConnectionState = 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED';
export type StreamName = 'ego' | 'left_wrist' | 'right_wrist' | 'pico_view';
export interface Pose { valid: boolean; confidence?: number; position: Vec3; quaternion: Quat; linear_velocity?: Vec3; angular_velocity?: Vec3 }
export interface Controller extends Pose { axis: [number, number]; trigger: number; grip: number; axis_click: boolean; primary_button: boolean; secondary_button: boolean; menu_button: boolean }
export interface Joint extends Pose { id: number; name: string; radius?: number; linear_acceleration?: Vec3; angular_acceleration?: Vec3 }
export interface Body { valid: boolean; calibrated: boolean; joint_count: number; joints: Joint[] }
export interface Hand { active: boolean; confidence: number; scale: number; joint_count: number; joints: Joint[] }
export interface Tracker extends Pose { id: number; sn: string; linear_acceleration?: Vec3; angular_acceleration?: Vec3 }
export interface Telemetry {
  type: 'telemetry'; schema: string; device_id: string; seq: number; source_timestamp_ns: number; gateway_timestamp_ns: number; input_mode: string;
  coordinate_frame: { name: string; handedness: string; x: string; y: string; z: string }; head: Pose;
  controllers: { left: Controller; right: Controller }; body: Body; hands: { left: Hand; right: Hand }; motion_trackers: Tracker[];
  derived: { head_pitch_deg: number; head_yaw_deg: number; head_roll_deg: number; left_wrist_speed_mps: number; right_wrist_speed_mps: number; left_wrist_depth_m: number; right_wrist_depth_m: number; left_hand_speed_mps: number; right_hand_speed_mps: number };
  health: { streaming: boolean; tracking_fps: number; latency_ms: number; packet_loss_percent: number; head_valid: boolean; left_controller_valid: boolean; right_controller_valid: boolean; body_valid: boolean; left_hand_valid: boolean; right_hand_valid: boolean; tracker_count: number };
}
export interface VideoMessage { type: 'video'; stream: StreamName; seq: number; source_timestamp_ns: number; width: number; height: number; fps: number; encoding: 'jpeg_base64'; data: string; depth?: { encoding: 'depth16_base64'|'float32_base64'; width: number; height: number; data: string; scale_m?: number }; vision?: { provider: string; objects?: { label: string; confidence: number; bbox?: [number,number,number,number]; depth_m?: number }[]; hands?: { side: 'left'|'right'; confidence: number; depth_m?: number }[] } }
export interface EventMessage { type: 'event'; timestamp?: string; level?: string; message: string }
export interface StatusResponse { device_id: string; online: boolean; streaming: boolean; body_calibrated: boolean; tracking_mode: string; tracker_count: number }
export interface TimelinePoint { t: number; leftSpeed: number; rightSpeed: number; leftDepth: number; rightDepth: number; pitch: number; leftTrigger: number; rightTrigger: number; confidence: number }
export const BODY_BONES: [number, number][] = [[0,1],[1,4],[4,7],[7,10],[0,2],[2,5],[5,8],[8,11],[0,3],[3,6],[6,9],[9,12],[12,15],[9,13],[13,16],[16,18],[18,20],[20,22],[9,14],[14,17],[17,19],[19,21],[21,23]];
export const HAND_BONES: [number, number][] = [[0,1],[1,2],[2,3],[3,4],[4,5],[1,6],[6,7],[7,8],[8,9],[9,10],[1,11],[11,12],[12,13],[13,14],[14,15],[1,16],[16,17],[17,18],[18,19],[19,20],[1,21],[21,22],[22,23],[23,24],[24,25]];
