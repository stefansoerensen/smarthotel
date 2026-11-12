# Smart Building

The building-technology strand of chAIn: a cloud control plane plus an edge gateway per property.
It registers the devices of a hotel, rolls room types out to many rooms, keeps a digital twin of
every room, runs local rules on the gateway (window open → heating off), sets rooms to eco, preheat
or comfort from Hotel OS occupancy, reports building faults to the Hotel OS inbox and delivers
energy per occupied night for the live P&L.

Prototype status: built and accepted against simulators only; nothing runs in a hotel yet.

| Stage | What | Plan |
|---|---|---|
| SB0 | Repository, CI, login, Mandanten, Häuser, Geräteregister | [plan](docs/superpowers/plans/2026-11-12-plan-sb0-foundation.md) |
| SB1 | Raumtypen, Rollout, digitaler Zwilling, Raumsimulator | [plan](docs/superpowers/plans/2026-11-12-plan-sb1-device-model.md) |
| SB2 | Edge-Gateway: lokale Regeln, Puffer, Befehle mit Quittung | [plan](docs/superpowers/plans/2026-11-12-plan-sb2-edge-gateway.md) |
| SB3 | Kopplung Hotel OS: Belegung → Raummodus, Störungen → Inbox | [plan](docs/superpowers/plans/2026-11-12-plan-sb3-hotel-os.md) |
| SB4 | Energie je 15 min, Tag und belegter Nacht | [plan](docs/superpowers/plans/2026-11-12-plan-sb4-energy.md) |

- Working agreement: [CLAUDE.md](CLAUDE.md)
- What works: [docs/feature-status.md](docs/feature-status.md)
- How it fits together: [docs/architecture.md](docs/architecture.md)
- Deployment: [docs/deployment.md](docs/deployment.md)
- Edge gateway: [edge/README.md](edge/README.md)
- Contracts: [contracts/](contracts/)
