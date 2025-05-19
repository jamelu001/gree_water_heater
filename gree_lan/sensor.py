"""Sensor for Midea Lan."""


from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_SENSORS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType


from homeassistant.helpers.device_registry import DeviceInfo



from .device import MockGreeDevice 
from .const import DOMAIN,DEFAULT_PORT
import logging
_LOGGER = logging.getLogger(__name__)

TEMP_OFFSET  = 100



async def async_setup_entry(hass, config_entry, async_add_entities, discovery_info=None):
    
    ip_addr = config_entry.data["host"]
    port = config_entry.data.get("port", DEFAULT_PORT)
    mac_addr = config_entry.data["mac"]
    
    device =  MockGreeDevice(ip_addr,mac_addr,port)

    

    async_add_entities([
     
    GreeSensor(hass, device,mac_addr)
])



class GreeSensor(SensorEntity):
    def __init__(self, hass,  device,mac_addr):
        self.hass = hass
        self._mac = mac_addr
        self._name = DOMAIN + "sensor" + self._mac
        self._unique_id = 'sensor.gree_' + self._mac
        self._device = device
        self._currentValues = 0

    async def async_update(self):
        currentValues = await self._device.GreeGetValues(["Watpercent"])
        self._currentValues = currentValues[0] - TEMP_OFFSET

    @property
    def name(self):
        return self._name
    
    @property
    def unique_id(self):
        return self._unique_id
        
    @property
    def native_value(self):
        """Return entity value."""
        return self._currentValues

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": DOMAIN + self._mac,
        }


