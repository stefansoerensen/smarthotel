# ADR-0008: Energy from cumulative meter readings, nights from 12:00 to 12:00

Status: Accepted (2026-11-12). SB4, hub d31.

## Context
The live P&L of the Hotel OS wants energy cost per occupied night. Meters report a cumulative
counter at irregular times, sometimes late (edge buffer), sometimes reset after a replacement.

## Decision
- Every value of a meter point is kept in `meter_readings`; other points keep only their last value.
- Consumption of an interval is the sum of positive deltas between consecutive readings whose later
  reading falls in the interval. A falling counter counts nothing. No interpolation.
- Days are local days of the property; 15-minute buckets are aligned to local midnight.
- A night runs from 12:00 to 12:00 local time and is *occupied* when an occupancy period from the
  Hotel OS sync covers its midnight. Occupancy periods open when a room becomes occupied and close
  when it no longer is or another reservation takes it.
- The price per kWh lives on the Hotel OS link as `Numeric(8, 4)`; costs are `Decimal`, rounded half
  to even to cents, and sent as strings. kWh are floats.
- The Hotel OS reads one night per call: `GET /api/integrations/hotel-os/v1/energy?property_code=…&date=…`.

## Consequences
+ Late, repeated or reset readings do not distort the totals.
+ The per-night figure matches how a hotel counts room nights.
− Without interpolation a sparse meter shifts consumption into the interval of its next reading;
  meters that report at least every 15 minutes make that irrelevant.
