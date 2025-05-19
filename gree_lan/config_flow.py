from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from .const import DOMAIN, CONF_HOST, CONF_MAC, CONF_PORT, DEFAULT_PORT
import re

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_MAC): str,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int
})



class CannotConnect(Exception):
    pass

class GreeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            
            if user_input[CONF_MAC]:
                await self.async_set_unique_id(user_input[CONF_MAC])
            else:
                await self._async_handle_discovery_without_unique_id()
            return self.async_create_entry(
                title=f"Gree Heater {user_input[CONF_HOST]}",
                data=user_input
            )
                
        
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GreeOptionsFlow(config_entry)

class GreeOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            
            return self.async_create_entry(title="", data=user_input)
            
               

        data_schema = vol.Schema({
            vol.Required(CONF_HOST, 
                default=self.config_entry.data.get(CONF_HOST)): str,
            vol.Required(CONF_MAC, 
                default=self.config_entry.data.get(CONF_MAC)): str,
            vol.Optional(CONF_PORT, 
                default=self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)): int
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )