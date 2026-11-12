# Smart Building — Plan SB4: Energy

> Steps use checkbox (`- [ ]`) syntax. Tick them in the same commit as the work.

**Goal:** Meter readings condensed to 15-minute and daily consumption, and consumption per occupied
night and room, as an input for the live P&L of the Hotel OS (hub d31).

**Hub:** b29 (SB4), d31, ADR-0008.

### Task 1: History
- [x] `meter_readings` (every value of a meter point, from the simulator or the edge) and
  `occupancy_periods` (opened and closed by the Hotel OS sync).

### Task 2: Aggregation
- [x] Tests: a delta belongs to the interval of the later reading; a falling counter counts nothing;
  the last reading before the range is the start value; local days follow the property time zone.
- [x] `services/energy/aggregate.py`; `GET /api/properties/{code}/energy` (15 min up to 7 days, day
  up to 366 days, per room).

### Task 3: Nights and the live P&L
- [x] Tests: kWh per room and night (12:00–12:00 local); occupied when a stay covers midnight;
  kWh and cost per occupied night with the price from the Hotel OS link; the Hotel OS endpoint needs
  the key.
- [x] `GET /api/properties/{code}/energy/nights`, `GET /api/integrations/hotel-os/v1/energy`.

### Task 4: Frontend
- [x] Haus tab "Energie": totals, kWh and cost per occupied night, bars per day, nights per room;
  price per kWh in the Hotel OS tab.

### Task 5: Verification
- [ ] Green CI; the Energie tab on Railway.
