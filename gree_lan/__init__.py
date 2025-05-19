from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from homeassistant.const import Platform

async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    # hass.async_create_task(
    #     hass.config_entries.async_forward_entry_setup(entry, "water_heater")
    # )
    await hass.config_entries.async_forward_entry_setups(config_entry, ["water_heater","sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(config_entry, ["water_heater","sensor"])
    return True

