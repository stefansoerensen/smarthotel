"""Import every model module so all tables register on Base.metadata."""

from app.models.devices import device, gateway  # noqa: F401
from app.models.estate import property  # noqa: F401
from app.models.platform import outbox_event, tenant, user  # noqa: F401
from app.models.twin import room, room_type  # noqa: F401
