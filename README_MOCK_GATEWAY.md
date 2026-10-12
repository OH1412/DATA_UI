# PICO Mock Gateway

在 `/home/descfly/DATA_UI` 中运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python mock_pico_gateway.py
```

前端另开终端运行 `npm run dev`，访问 `http://localhost:5173`。Gateway 地址是 `http://127.0.0.1:8765`，FastAPI 文档在 `http://127.0.0.1:8765/docs`。

测试 telemetry：

```bash
pip install websockets
python test_client.py
```

参数：`--tracking-fps 60 --video-fps 10 --host 0.0.0.0 --port 8765`。视频由 Pillow 动态生成，telemetry 采用连续的正弦运动，不是前端内部 mock 数据。POST `/api/command` 支持 `prepare`、`start_stream`、`stop_stream`、`recenter`、`recalibrate`、`restart_client`。
