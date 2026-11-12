# Edge protocol v1 — message examples

Examples of every message between an edge gateway and the control plane. The backend tests post
them to `/edge/v1`; the edge tests check that the messages the gateway builds have the same shape.
Change both sides and these files together; a breaking change is `v2`, not an edit.

| File | Direction |
|---|---|
| `hello-response.json` | cloud → edge, answer to `POST /edge/v1/hello` |
| `readings-request.json` | edge → cloud, `POST /edge/v1/readings` |
| `heartbeat-request.json` | edge → cloud, `POST /edge/v1/heartbeat` |
| `commands-response.json` | cloud → edge, answer to `GET /edge/v1/commands` |
| `ack-request.json` | edge → cloud, `POST /edge/v1/commands/{id}/ack` |

All requests carry `Authorization: Bearer <gateway token>`. Times are ISO 8601 with offset.
