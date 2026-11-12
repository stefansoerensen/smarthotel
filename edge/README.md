# Edge gateway

One container per property. It runs the rooms' local rules (room controller, window open →
heating off, frost protection), buffers readings while the control plane is unreachable, executes
commands and acknowledges them. Today it runs against a simulated bus only.

```bash
docker build -t smarthotel-edge edge/
docker run -v edge-data:/data \
  -e EDGE_CLOUD_URL=https://<app>.up.railway.app \
  -e EDGE_TOKEN=<token from "Token erzeugen"> \
  smarthotel-edge
```

| Variable | Default | Meaning |
|---|---|---|
| `EDGE_CLOUD_URL` | — | Control plane base URL |
| `EDGE_TOKEN` | — | Gateway token, shown once in the Geräte tab |
| `EDGE_TICK_SECONDS` | `15` | Real seconds between ticks |
| `EDGE_SIM_MINUTES_PER_TICK` | `0.25` | Simulated minutes per tick (raise to speed the rooms up) |
| `EDGE_OUTDOOR` | `5` | Simulated outdoor temperature, °C |
| `EDGE_SCENARIO` | — | Simulated events, e.g. `30:101:window:1,90:101:window:0` |
| `EDGE_FAULTY_DEVICES` | — | Device codes that do not answer, e.g. `102-TEMPERATURE` |
| `EDGE_BUFFER_PATH` | `/data/edge.sqlite` | Reading queue and stored configuration |

The gateway never imports `backend/`; the contract is `contracts/edge-v1/`.
