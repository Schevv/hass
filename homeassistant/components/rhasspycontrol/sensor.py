"""Contains the Rhasspy Control sensors"""
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
import datetime

from .controller import RhasspyDeviceController
from .const import DOMAIN


class RhasspySensor(CoordinatorEntity, SensorEntity):
    """Base class for Rhasspy sensors"""

    def __init__(self, device_controller: RhasspyDeviceController, name: str) -> None:
        super().__init__(device_controller)
        self.device_controller = device_controller
        self._attr_device_info = device_controller.device
        self._attr_assumed_state = False
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id = (
            device_controller.unique_id + "-" + name.replace(" ", "-").lower()
        )


class RhasspyLastNotificationSensor(RhasspySensor):
    """Sensor to hold the last notification for this Rhasspy"""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller, "Last Notification")
        self._attr_icon = "mdi:message-badge"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = ""
        self._attr_extra_state_attributes = {
            "timestamp": datetime.datetime.now(),
            "title": None,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.device_controller.data.last_tts_notification
        self._attr_extra_state_attributes = {
            "timestamp": self.device_controller.data.last_tts_notification_timestamp,
            "title": self.device_controller.data.last_tts_notification_title,
        }
        self.async_write_ha_state()


class RhasspyLastSpeechInputSensor(RhasspySensor):
    """Sensor that displays that last time Rhasspy was spoken to"""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller, "Time Last Command")
        self._attr_icon = "mdi:clock-in"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.device_controller.data.last_input_timestamp
        self.async_write_ha_state()


class RhasspyLastVoiceOutputSensor(RhasspySensor):
    """Sensor that displays that last time Rhasspy was outputting"""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller, "Time Last Output")
        self._attr_icon = "mdi:clock-out"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.device_controller.data.last_output_timestamp
        self.async_write_ha_state()

class RhasspyCpuLoadSensor(RhasspySensor):
    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller, "Cpu Load")
        self._attr_icon = "mdi:chip"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"
        self._attr_suggested_display_precision = 0
        self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.device_controller.data.cpu_percentage
        self._attr_extra_state_attributes = { "cpu_count": self.device_controller.data.cpu_count }
        self.async_write_ha_state()

class RhasspyCpuTempSensor(RhasspySensor):
    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller, "Cpu Temperature")
        self._attr_icon = "mdi:chip"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = "°C"
        self._attr_suggested_display_precision = 0
        self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.device_controller.data.current_temp
        self.async_write_ha_state()

class RhasspyMemorySensor(RhasspySensor):
    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller, "RAM")
        self._attr_icon = "mdi:memory"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_suggested_unit_of_measurement = "MB"
        self._attr_native_unit_of_measurement = "B"
        self._attr_suggested_display_precision = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.device_controller.data.used_memory
        self._attr_extra_state_attributes = { "total": self.device_controller.data.total_memory }
        self.async_write_ha_state()

class RhasspyDiskSensor(RhasspySensor):
    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller, "Hard Drive")
        self._attr_icon = "mdi:memory"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_suggested_unit_of_measurement = "GB"
        self._attr_native_unit_of_measurement = "B"
        self._attr_suggested_display_precision = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.device_controller.data.used_disk
        self._attr_extra_state_attributes =  { "total": self.device_controller.data.total_disk }
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set Sensors for device."""

    device_controller = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            RhasspyLastNotificationSensor(device_controller),
            RhasspyLastSpeechInputSensor(device_controller),
            RhasspyLastVoiceOutputSensor(device_controller),
            RhasspyCpuLoadSensor(device_controller),
            RhasspyCpuTempSensor(device_controller),
            RhasspyMemorySensor(device_controller),
            RhasspyDiskSensor(device_controller)
        ],
        True,
    )
