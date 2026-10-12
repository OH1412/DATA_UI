# LITCHI DATA SPACE

面向多设备运动数据采集与遥操作的团队工作空间。当前包含实时监控工作台，后续可扩展青瞳动捕、VR/XR、机器人控制器等设备接入，以及基于 Tailscale 的远程资产空间。

## 产品结构

- **监控工作台**：实时视频、人体骨架、设备健康、遥测时间线和操作控制。
- **资产空间**：设备、采集会话、标定文件、视频、动作数据和导出任务的统一入口。
- **接入设置**：设备发现、Tailscale 节点状态、权限、采集协议和标定配置。
- **首次引导**：首次进入时选择工作空间用途、接入设备和默认采集配置；之后可从接入设置重新修改。

品牌不再绑定单一硬件厂商；设备适配层应统一映射为 source、streams、telemetry、capabilities 和 commands，前端只消费标准化数据。

## Run

```bash
npm install
npm run dev
```

访问 `http://localhost:5173`。

默认服务端地址为 `http://127.0.0.1:8765`，前端连接：

- `GET /api/status`
- `POST /api/command`
- `ws://127.0.0.1:8765/ws/telemetry`
- `ws://127.0.0.1:8765/ws/video`
- `ws://127.0.0.1:8765/ws/events`

当 Gateway 未启动时，页面会保持 `DISCONNECTED`，不会填充假数据。JPEG 视频消息应使用 `jpeg_base64` 编码；遥测和视频最后一帧会保留到断线重连。
