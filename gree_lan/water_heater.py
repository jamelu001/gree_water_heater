#!/usr/bin/python
# Do basic imports

    
from .device import MockGreeDevice 
from datetime import timedelta
from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_TARGET_TEMP_STEP,
    CONF_HOST,
    CONF_MAC,
    CONF_PORT,
    )

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv


from homeassistant.components.water_heater import (
    STATE_ON,
    STATE_OFF,
    STATE_HEAT_PUMP,
    STATE_ECO,
    STATE_HIGH_DEMAND,
    PLATFORM_SCHEMA,
    ATTR_TEMPERATURE,
    WaterHeaterEntity,
    WaterHeaterEntityFeature
)


from homeassistant.const import (
    UnitOfTemperature,
    PRECISION_WHOLE,
    ATTR_TEMPERATURE,
    STATE_OFF,
)


from homeassistant.helpers.device_registry import DeviceInfo






_LOGGER = logging.getLogger(__name__)


MAX_TEMP = 55
MIN_TEMP = 35
CONF_ENCRYPTION_KEY = 'encryption_key'
CONF_ENCRYPTION_VERSION = 1
OPERATION_MODES = [STATE_HEAT_PUMP, STATE_ECO, STATE_HIGH_DEMAND, STATE_OFF]


#偏移值
TEMP_OFFSET  = 100

# update() interval
SCAN_INTERVAL = timedelta(seconds=60)





# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
#     vol.Required(CONF_HOST): cv.string,
#     vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
#     vol.Required(CONF_MAC): cv.string,
    
# })

async def async_setup_entry(hass, config_entry, async_add_entities, discovery_info=None):
    _LOGGER.info('Setting up Gree Water Heater platform')
    ip_addr = config_entry.data["host"]
    port = config_entry.data.get("port", DEFAULT_PORT)
    mac_addr = config_entry.data["mac"]
    
    device =  MockGreeDevice(ip_addr,mac_addr,port)

    _LOGGER.info('Adding Gree Water Heater device to hass')

    async_add_entities([
     
     GreeWaterHeater(hass,  device,  mac_addr)
])




class GreeWaterHeater(WaterHeaterEntity):
    def __init__(self, hass,  device,  mac_addr):
        _LOGGER.info('Initialize the GREE Water Heater device')
        self.hass = hass
        self._mac = mac_addr
        self._name = DOMAIN +'_waterHeater_'+ self._mac
        self._device = device
        self._unique_id = 'waterHeater.gree_' + self._mac
        self._current_temperature = None
        self._target_temperature = None

        self._firstTimeRun = True

        self._operation_modes = OPERATION_MODES
        self._hvac_mode = STATE_OFF

        self._target_temperature_step = DEFAULT_TARGET_TEMP_STEP

        self._acOptions = { 'Pow': None, 'Wmod': None, 'SetTemInt': None, 'WatTmp': None, 'WstpSv': None }
        self._optionsToFetch = ["Pow","Wmod","SetTemInt","WatTmp","WstpSv"]


    def SetAcOptions(self, acOptions, newOptionsToOverride, optionValuesToOverride):   
        for key in newOptionsToOverride:
            _LOGGER.info('Setting %s: %s' % (key, optionValuesToOverride[newOptionsToOverride.index(key)]))
            acOptions[key] = optionValuesToOverride[newOptionsToOverride.index(key)]
        return acOptions
    
            
    async def async_update(self):
       
        currentValues = await self._device.GreeGetValues(self._optionsToFetch)
        self._acOptions = self.SetAcOptions(self._acOptions, self._optionsToFetch, currentValues)
        #目标温度
        self._target_temperature = self._acOptions['SetTemInt']
        #模式
        if (self._acOptions['Pow'] == 0):
            self._hvac_mode = STATE_OFF
        else:
            self._hvac_mode = self._operation_modes[self._acOptions['Wmod']]
        #当前温度
        temp = self._acOptions['WatTmp'] if self._acOptions['WatTmp'] <= TEMP_OFFSET else self._acOptions['WatTmp'] - TEMP_OFFSET
        self._current_temperature = self.hass.config.units.temperature(float(temp), UnitOfTemperature.CELSIUS)
        if not (self._firstTimeRun):
            if self._target_temperature:
                await self.async_set_temperature()
            else:
                self._firstTimeRun = False

    @property
    def should_poll(self):
        return True


    @property
    def name(self):
        return self._name


    @property
    def supported_features(self):
        return WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE

    @property
    def min_temp(self):
        return MIN_TEMP
    @property
    def max_temp(self):
        return MAX_TEMP

    @property
    def target_temperature_low(self):
        return self.min_temp

    @property
    def target_temperature_high(self):
        return self.max_temp

    @property
    def precision(self):
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS
       

    @property
    def operation_list(self):
        return self._operation_modes

    @property
    def current_operation(self):
        return self._hvac_mode

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature
    
    @property
    def unique_id(self):
        return self._unique_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return the optional device state attributes."""
        data = {"target_temp_step": self._target_temperature_step}
        return data
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": DOMAIN + self._mac,
        }



    async def async_turn_on(self, **kwargs):
        await self._device.SendStateToAc({'Pow': 1})

    async def async_turn_off(self, **kwargs):
        await self._device.SendStateToAc({'Pow': 0})

    async def async_set_operation_mode(self, hvac_mode: str) -> None:
        """Set the operation mode of the water heater.
        Must be in the operation_list.
        """
        c = {}
        if (hvac_mode == STATE_OFF):
            c = ({'Pow': 0})
        else:
            c = ({'Pow': 1, 'Wmod': self._operation_modes.index(hvac_mode)})
        
        await self._device.SendStateToAc(c)

    async def async_set_temperature(self, **kwargs: any) -> None:
        """Set the temperature the water heater should heat water to."""
        c = { 'SetTemInt': int(kwargs[ATTR_TEMPERATURE])}
        await self._device.SendStateToAc(c)



    async def async_added_to_hass(self):
        _LOGGER.info('Gree climate device added to hass()')
        await self.async_update()
        
        


