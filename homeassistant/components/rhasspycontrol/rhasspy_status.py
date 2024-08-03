"""Contains the RhasspyStatus type"""
from typing import NamedTuple
from datetime import datetime


class RhasspyStatus(NamedTuple):
    """Contains the current state of a Rhasspy instance"""

    listening: bool = True
    """If the Rhasspy is currently listening for the wake word"""

    volume: int = 100
    """The current output volume between 0..100"""

    available: bool = False
    """Is the Rhasspy ready"""

    last_input_timestamp: datetime | None = None
    """Last time something was output by the Rhasspy"""

    last_output_timestamp: datetime | None = None
    """Last time something was output by the Rhasspy"""

    last_tts_notification: str | None = None
    """Last notification accepted by this Rhasspy"""

    last_tts_notification_timestamp: datetime | None = None
    """Time the last notification was accepted"""

    last_tts_notification_title: str | None = None
    """Optional title of the the last accepted notification"""

    cpu_percentage : float | None = None
    """CPU usage in the last 15 minutes"""

    cpu_count : int | None = None
    """Total number of CPUs"""

    total_memory : int | None = None
    """Total memory"""

    used_memory : int | None = None
    """Memory used"""

    total_disk : int | None = None
    """Total disk size"""

    used_disk : int | None = None
    """Used disk"""

    current_temp : float | None = None
    """Current CPU temperature"""

