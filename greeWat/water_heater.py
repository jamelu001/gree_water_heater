#!/usr/bin/python
# Do basic imports
import socket
import base64

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv


from homeassistant.components.water_heater import *
from homeassistant.const import (
    #Platform,
    TEMP_CELSIUS,
    PRECISION_WHOLE,
    #PRECISION_HALVES,
    ATTR_TEMPERATURE,
    # CONF_DEVICE_ID,
    # CONF_SWITCHES,
    # STATE_ON,
    STATE_OFF,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    CONF_TIMEOUT,
    ATTR_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event
from Crypto.Cipher import AES
try: import simplejson
except ImportError: import json as simplejson
from datetime import timedelta

REQUIREMENTS = ['pycryptodome']

_LOGGER = logging.getLogger(__name__)


MAX_TEMP = 55
MIN_TEMP = 35

DEFAULT_NAME = 'Gree Water Heater'
DEFAULT_PORT = 7000
DEFAULT_TIMEOUT = 10
DEFAULT_TARGET_TEMP_STEP = 1
CONF_ENCRYPTION_KEY = 'encryption_key'
CONF_UID = 'uid'
CONF_MAX_ONLINE_ATTEMPTS = 'max_online_attempts'
CONF_DISABLE_AVAILABLE_CHECK  = 'disable_available_check'
CONF_ENCRYPTION_VERSION = 'encryption_version'
CONF_TARGET_TEMP = 'target_temp'
HVAC_MODES = [STATE_HEAT_PUMP, STATE_ECO, STATE_HIGH_DEMAND, STATE_OFF]
CONF_TEMP_SENSOR = 'temp_sensor'
CONF_TARGET_TEMP_STEP = 'target_temp_step'






# update() interval
SCAN_INTERVAL = timedelta(seconds=60)
#偏移值
TEMP_OFFSET  = 100



GCM_IV = b'\x54\x40\x78\x44\x49\x67\x5a\x51\x6c\x5e\x63\x13'
GCM_ADD = b'qualcomm-test'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
    vol.Required(CONF_MAC): cv.string,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,  
    vol.Optional(CONF_ENCRYPTION_KEY): cv.string,
    vol.Optional(CONF_UID): cv.positive_int,
    vol.Optional(CONF_MAX_ONLINE_ATTEMPTS, default=3): cv.positive_int,
    vol.Optional(CONF_DISABLE_AVAILABLE_CHECK, default=False): cv.boolean,
    vol.Optional(CONF_ENCRYPTION_VERSION, default=1): cv.positive_int,
    vol.Optional(CONF_TARGET_TEMP): cv.entity_id,
    vol.Optional(CONF_TEMP_SENSOR): cv.entity_id,
    vol.Optional(CONF_TARGET_TEMP_STEP, default=DEFAULT_TARGET_TEMP_STEP): vol.Coerce(float),
    
})

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    _LOGGER.info('Setting up Gree Water Heater platform')
    name = config.get(CONF_NAME)
    ip_addr = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    mac_addr = config.get(CONF_MAC).encode().replace(b':', b'')
    timeout = config.get(CONF_TIMEOUT)
    encryption_key = config.get(CONF_ENCRYPTION_KEY)
    uid = config.get(CONF_UID)
    max_online_attempts = config.get(CONF_MAX_ONLINE_ATTEMPTS)
    disable_available_check = config.get(CONF_DISABLE_AVAILABLE_CHECK)
    encryption_version = config.get(CONF_ENCRYPTION_VERSION)
    temp_sensor_entity_id = config.get(CONF_TEMP_SENSOR)
    target_temp_entity_id = config.get(CONF_TARGET_TEMP)
    hvac_modes = HVAC_MODES
    target_temp_step = config.get(CONF_TARGET_TEMP_STEP)
    

    _LOGGER.info('Adding Gree Water Heater device to hass')

    async_add_devices([
     
     GreeWaterHeater(hass, name, ip_addr, port, mac_addr, timeout, temp_sensor_entity_id,target_temp_entity_id,hvac_modes,target_temp_step, encryption_version, disable_available_check, max_online_attempts, encryption_key, uid)
])




class GreeWaterHeater(WaterHeaterEntity):
    def __init__(self, hass, name, ip_addr, port, mac_addr, timeout, temp_sensor_entity_id,target_temp_entity_id,hvac_modes,target_temp_step, encryption_version, disable_available_check, max_online_attempts, encryption_key=None, uid=None):
        _LOGGER.info('Initialize the GREE Water Heater device')
        self.hass = hass
        self._name = name
        self._ip_addr = ip_addr
        self._port = port
        self._mac_addr = mac_addr.decode('utf-8').lower()
        self._timeout = timeout
        self._unique_id = 'waterHeater.gree_' + mac_addr.decode('utf-8').lower()
        self._device_online = None
        self._online_attempts = 0
        self._max_online_attempts = max_online_attempts
        self._disable_available_check = disable_available_check
        
        

        self._current_temperature = None

        self._target_temp_entity_id = target_temp_entity_id
        self._target_temperature = None

        self._firstTimeRun = True

        self._enable_turn_on_off_backwards_compatibility = False

        self.encryption_version = encryption_version
        self.CIPHER = None

        self._hvac_modes = hvac_modes
        self._hvac_mode = STATE_OFF

        self._unit_of_measurement = '°C'
        self._temp_sensor_entity_id = temp_sensor_entity_id
        self._has_temp_sensor = None
        self._target_temperature_step = target_temp_step

       

        if encryption_key:
            _LOGGER.info('Using configured encryption key: {}'.format(encryption_key))
            self._encryption_key = encryption_key.encode("utf8")
            if encryption_version == 1:
                # Cipher to use to encrypt/decrypt
                self.CIPHER = AES.new(self._encryption_key, AES.MODE_ECB)
            elif encryption_version != 2:
                _LOGGER.error('Encryption version %s is not implemented.' % encryption_version)
        else:
            self._encryption_key = None
        
        if uid:
            self._uid = uid
        else:
            self._uid = 0

        self._acOptions = { 'Pow': None, 'Wmod': None, 'SetTemInt': None, 'WatTmp': None, 'WstpSv': None, 'Watpercent': None }
        self._optionsToFetch = ["Pow","Wmod","SetTemInt","WatTmp","WstpSv","Watpercent"]


        if temp_sensor_entity_id:
            _LOGGER.info('Setting up temperature sensor: ' + str(temp_sensor_entity_id))
            async_track_state_change_event(hass, temp_sensor_entity_id, self._async_temp_sensor_changed)
                

        if target_temp_entity_id:
            _LOGGER.info('Setting up target temp entity: ' + str(target_temp_entity_id))
            async_track_state_change_event(hass, target_temp_entity_id, self._async_target_temp_entity_state_changed)

    



        # Pad helper method to help us get the right string for encrypting
    def Pad(self, s):
        aesBlockSize = 16
        return s + (aesBlockSize - len(s) % aesBlockSize) * chr(aesBlockSize - len(s) % aesBlockSize)            

    def FetchResult(self, cipher, ip_addr, port, timeout, json):
        _LOGGER.info('Fetching(%s, %s, %s, %s)' % (ip_addr, port, timeout, json))
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        clientSock.settimeout(timeout)
        clientSock.sendto(bytes(json, "utf-8"), (ip_addr, port))
        _LOGGER.info('3')
        data, addr = clientSock.recvfrom(64000)
        receivedJson = simplejson.loads(data)
        clientSock.close()
        pack = receivedJson['pack']
        base64decodedPack = base64.b64decode(pack)
        decryptedPack = cipher.decrypt(base64decodedPack)
        if self.encryption_version == 2:
            tag = receivedJson['tag']
            cipher.verify(base64.b64decode(tag))
        decodedPack = decryptedPack.decode("utf-8")
        replacedPack = decodedPack.replace('\x0f', '').replace(decodedPack[decodedPack.rindex('}')+1:], '')
        loadedJsonPack = simplejson.loads(replacedPack)  
        return loadedJsonPack

    def GetDeviceKey(self):
        _LOGGER.info('Retrieving HVAC encryption key')
        GENERIC_GREE_DEVICE_KEY = "a3K8Bx%2r8Y7#xDh"
        cipher = AES.new(GENERIC_GREE_DEVICE_KEY.encode("utf8"), AES.MODE_ECB)
        pack = base64.b64encode(cipher.encrypt(self.Pad('{"mac":"' + str(self._mac_addr) + '","t":"bind","uid":0}').encode("utf8"))).decode('utf-8')
        jsonPayloadToSend = '{"cid": "app","i": 1,"pack": "' + pack + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid": 0}'
        try:
            self._encryption_key = self.FetchResult(cipher, self._ip_addr, self._port, self._timeout, jsonPayloadToSend)['key'].encode("utf8")
        except:
            _LOGGER.info('Error getting device encryption key!')
            self._device_online = False
            self._online_attempts = 0
            return False
        else:
            _LOGGER.info('Fetched device encrytion key: %s' % str(self._encryption_key))
            self.CIPHER = AES.new(self._encryption_key, AES.MODE_ECB)
            self._device_online = True
            self._online_attempts = 0
            return True
        
    def GetGCMCipher(self, key):
        cipher = AES.new(key, AES.MODE_GCM, nonce=GCM_IV)
        cipher.update(GCM_ADD)
        return cipher

    def EncryptGCM(self, key, plaintext):
        encrypted_data, tag = self.GetGCMCipher(key).encrypt_and_digest(plaintext.encode("utf8"))
        pack = base64.b64encode(encrypted_data).decode('utf-8')
        tag = base64.b64encode(tag).decode('utf-8')
        return (pack, tag)

    def GetDeviceKeyGCM(self):
        _LOGGER.info('Retrieving HVAC encryption key')
        GENERIC_GREE_DEVICE_KEY = b'{yxAHAY_Lm6pbC/<'
        plaintext = '{"cid":"' + str(self._mac_addr) + '", "mac":"' + str(self._mac_addr) + '","t":"bind","uid":0}'
        pack, tag = self.EncryptGCM(GENERIC_GREE_DEVICE_KEY, plaintext)
        jsonPayloadToSend = '{"cid": "app","i": 1,"pack": "' + pack + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid": 0, "tag" : "' + tag + '"}'
        try:
            self._encryption_key = self.FetchResult(self.GetGCMCipher(GENERIC_GREE_DEVICE_KEY), self._ip_addr, self._port, self._timeout, jsonPayloadToSend)['key'].encode("utf8")
        except:
            _LOGGER.info('Error getting device encryption key!')
            self._device_online = False
            self._online_attempts = 0
            return False
        else:
            _LOGGER.info('Fetched device encrytion key: %s' % str(self._encryption_key))
            self._device_online = True
            self._online_attempts = 0
            return True

    def GreeGetValues(self, propertyNames):
        plaintext = '{"cols":' + simplejson.dumps(propertyNames) + ',"mac":"' + str(self._mac_addr) + '","t":"status"}'
        if self.encryption_version == 1:
            cipher = self.CIPHER
            jsonPayloadToSend = '{"cid":"app","i":0,"pack":"' + base64.b64encode(cipher.encrypt(self.Pad(plaintext).encode("utf8"))).decode('utf-8') + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid":{}'.format(self._uid) + '}'
        elif self.encryption_version == 2:
            pack, tag = self.EncryptGCM(self._encryption_key, plaintext)
            jsonPayloadToSend = '{"cid":"app","i":0,"pack":"' + pack + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid":{}'.format(self._uid) + ',"tag" : "' + tag + '"}'
            cipher = self.GetGCMCipher(self._encryption_key)
        return self.FetchResult(cipher, self._ip_addr, self._port, self._timeout, jsonPayloadToSend)['dat']

    def SetAcOptions(self, acOptions, newOptionsToOverride, optionValuesToOverride = None):
        if not (optionValuesToOverride is None):
            _LOGGER.info('Setting acOptions with retrieved HVAC values')
            for key in newOptionsToOverride:
                _LOGGER.info('Setting %s: %s' % (key, optionValuesToOverride[newOptionsToOverride.index(key)]))
                acOptions[key] = optionValuesToOverride[newOptionsToOverride.index(key)]
            _LOGGER.info('Done setting acOptions')
        else:
            _LOGGER.info('Overwriting acOptions with new settings')
            for key, value in newOptionsToOverride.items():
                _LOGGER.info('Overwriting %s: %s' % (key, value))
                acOptions[key] = value
            _LOGGER.info('Done overwriting acOptions')
        return acOptions
        
    def SendStateToAc(self, timeout):
        opt = '"Pow","Wmod","SetTemInt","WatTmp","WstpSv","Watpercent"'
        p = '{Pow},{Wmod},{SetTemInt},{WatTmp},{WstpSv},{Watpercent}'.format(**self._acOptions)
        statePackJson = '{"opt":[' + opt + '],"p":[' + p + '],"t":"cmd"}'
        if self.encryption_version == 1:
            cipher = self.CIPHER
            sentJsonPayload = '{"cid":"app","i":0,"pack":"' + base64.b64encode(cipher.encrypt(self.Pad(statePackJson).encode("utf8"))).decode('utf-8') + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid":{}'.format(self._uid) + '}'
        elif self.encryption_version == 2:
            pack, tag = self.EncryptGCM(self._encryption_key, statePackJson)
            sentJsonPayload = '{"cid":"app","i":0,"pack":"' + pack + '","t":"pack","tcid":"' + str(self._mac_addr) + '","uid":{}'.format(self._uid) + ',"tag":"' + tag +'"}'
            cipher = self.GetGCMCipher(self._encryption_key)
        receivedJsonPayload = self.FetchResult(cipher, self._ip_addr, self._port, timeout, sentJsonPayload)
        _LOGGER.info('Done sending state to HVAC: ' + str(receivedJsonPayload))

    def UpdateHATargetTemperature(self):
        
        self._target_temperature = self._acOptions['SetTemInt']
        _LOGGER.info(self._target_temperature)
        if self._target_temp_entity_id:
            _LOGGER.info(self._target_temp_entity_id)
            target_temp_state = self.hass.states.get(self._target_temp_entity_id)
            _LOGGER.info(target_temp_state)
            if target_temp_state:
                _LOGGER.info('5')
                attr = target_temp_state.attributes
                _LOGGER.info(attr)
                if self._target_temperature in range(MIN_TEMP, MAX_TEMP+1):
                    self.hass.states.async_set(self._target_temp_entity_id, float(self._target_temperature), attr)
        _LOGGER.info('HA target temp set according to HVAC state to: ' + str(self._acOptions['SetTemInt']))
       


    def UpdateHAHvacMode(self):
        # Sync current HVAC operation mode to HA
        if (self._acOptions['Pow'] == 0):
            self._hvac_mode = STATE_OFF
        else:
            self._hvac_mode = self._hvac_modes[self._acOptions['Wmod']]
        _LOGGER.info('HA operation mode set according to HVAC state to: ' + str(self._hvac_mode))

    def UpdateHACurrentTemperature(self):
        if not self._temp_sensor_entity_id:
            if self._has_temp_sensor:
                temp = self._acOptions['WatTmp'] if self._acOptions['WatTmp'] <= TEMP_OFFSET else self._acOptions['WatTmp'] - TEMP_OFFSET
                self._current_temperature = self.hass.config.units.temperature(float(temp), self._unit_of_measurement)
                _LOGGER.info('HA current temperature set with device built-in temperature sensor state : ' + str(self._current_temperature))

    def UpdateHAStateToCurrentACState(self):
        self.UpdateHATargetTemperature()
        self.UpdateHAHvacMode()
        self.UpdateHACurrentTemperature()

    def SyncState(self, acOptions = {}):
        #Fetch current settings from HVAC
        _LOGGER.info('Starting SyncState')

        if not self._temp_sensor_entity_id:
            if self._has_temp_sensor is None:
                _LOGGER.info('Attempt to check whether device has an built-in temperature sensor')
                try:
                    temp_sensor = self.GreeGetValues(["WatTmp"])
                except:
                    _LOGGER.info('Could not determine whether device has an built-in temperature sensor. Retrying at next update()')
                else:
                    if temp_sensor:
                        self._has_temp_sensor = True
                        self._acOptions.update({'WatTmp': None})
                        self._optionsToFetch.append("WatTmp")
                        _LOGGER.info('Device has an built-in temperature sensor')
                    else:
                        self._has_temp_sensor = False
                        _LOGGER.info('Device has no built-in temperature sensor')

        
        optionsToFetch = self._optionsToFetch

        try:
            currentValues = self.GreeGetValues(optionsToFetch)
        except:
            _LOGGER.info('Could not connect with device. ')
            if not self._disable_available_check:
                self._online_attempts +=1
                if (self._online_attempts == self._max_online_attempts):
                    _LOGGER.info('Could not connect with device %s times. Set it as offline.' % self._max_online_attempts)
                    self._device_online = False
                    self._online_attempts = 0
        else:
            if not self._disable_available_check:
                if not self._device_online:
                    self._device_online = True
                    self._online_attempts = 0
            # Set latest status from device
            self._acOptions = self.SetAcOptions(self._acOptions, optionsToFetch, currentValues)

            # Overwrite status with our choices
            if not(acOptions == {}):
                self._acOptions = self.SetAcOptions(self._acOptions, acOptions)

            # Initialize the receivedJsonPayload variable (for return)
            receivedJsonPayload = ''

            # If not the first (boot) run, update state towards the HVAC
            if not (self._firstTimeRun):
                if not(acOptions == {}):
                    # loop used to send changed settings from HA to HVAC
                    self.SendStateToAc(self._timeout)
            else:
                # loop used once for Gree Climate initialisation only
                self._firstTimeRun = False

            # Update HA state to current HVAC state
            self.UpdateHAStateToCurrentACState()

            _LOGGER.info('Finished SyncState')
            return receivedJsonPayload

    async def _async_temp_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        s = str(old_state.state) if hasattr(old_state,'state') else "None"
        _LOGGER.info('temp_sensor state changed | ' + str(entity_id) + ' from ' + s + ' to ' + str(new_state.state))
        # Handle temperature changes.
        if new_state is None:
            return
        self._async_update_current_temp(new_state)
        return self.schedule_update_ha_state(True)
    
    @callback
    def _async_update_current_temp(self, state):
        _LOGGER.info('Thermostat updated with changed temp_sensor state | ' + str(state.state))
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        try:
            _state = state.state
            _LOGGER.info('Current state temp_sensor: ' + _state)
            if self.represents_float(_state):
                self._current_temperature = self.hass.config.units.temperature(
                    float(_state), unit)
                _LOGGER.info('Current temp: ' + str(self._current_temperature))
        except ValueError as ex:
            _LOGGER.error('Unable to update from temp_sensor: %s' % ex)

    def represents_float(self, s):
        _LOGGER.info('temp_sensor state represents_float |' + str(s))
        try: 
            float(s)
            return True
        except ValueError:
            return False     
        
    def _async_target_temp_entity_state_changed(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        _LOGGER.info('target_temp_entity state changed | ' + str(entity_id) + ' from ' + (str(old_state.state) if hasattr(old_state,'state') else "None") + ' to ' + str(new_state.state))
        if new_state is None:
            return
        if new_state.state is "off" and (old_state is None or old_state.state is None):
            _LOGGER.info('target_temp_entity state changed to off, but old state is None. Ignoring to avoid beeps.')
            return
        if int(float(new_state.state)) is self._target_temperature:
            # do nothing if state change is triggered due to Sync with HVAC
            return
        self._async_update_current_target_temp(new_state)
        return self.schedule_update_ha_state(True)

    @callback
    def _async_update_current_target_temp(self, state):
        s = int(float(state.state))
        _LOGGER.info('Updating HVAC with changed target_temp_entity state | ' + str(s))
        if (s >= MIN_TEMP) and (s <= MAX_TEMP):
            self.SyncState({'SetTemInt': s})
            return
        _LOGGER.error('Unable to update from target_temp_entity!')



    

    @property
    def should_poll(self):
        _LOGGER.info('should_poll()')
        # Return the polling state.
        return True

    @property
    def available(self):
        if self._disable_available_check:
            return True
        else:
            if self._device_online:
                _LOGGER.info('available(): Device is online')
                return True
            else:
                _LOGGER.info('available(): Device is offline')
                return False
            
    def update(self):
        _LOGGER.info('update()')
        if not self._encryption_key:
            if self.encryption_version == 1:
                if self.GetDeviceKey():
                    self.SyncState()
            elif self.encryption_version == 2:
                if self.GetDeviceKeyGCM():
                    self.SyncState()
            else:
                _LOGGER.error('Encryption version %s is not implemented.' % encryption_version)
        else:
            self.SyncState()

    @property
    def name(self):
        _LOGGER.info('name(): ' + str(self._name))
        # Return the name of the climate device.
        return self._name


    @property
    def supported_features(self):
        return WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE



    @property
    def min_temp(self):
        _LOGGER.info('min_temp(): ' + str(MIN_TEMP))
        # Return the minimum temperature.
        return MIN_TEMP
    @property
    def max_temp(self):
        _LOGGER.info('max_temp(): ' + str(MAX_TEMP))
        # Return the maximum temperature.
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
        return TEMP_CELSIUS

    @property
    def current_operation(self):
        _LOGGER.info('hvac_mode(): ' + str(self._hvac_mode))
        # Return current operation mode ie. heat, cool, idle.
        return self._hvac_mode

    @property
    def current_temperature(self):
        _LOGGER.info('current_temperature(): ' + str(self._current_temperature))
        # Return the current temperature.
        return self._current_temperature

    @property
    def target_temperature(self):
        _LOGGER.info('target_temperature(): ' + str(self._target_temperature))
        # Return the temperature we try to reach.
        return self._target_temperature
    
    @property
    def unique_id(self):
        # Return unique_id
        return self._unique_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return the optional device state attributes."""
        data = {"target_temp_step": self._target_temperature_step}
        return data


    def set_temperature(self, **kwargs):
        _LOGGER.info('set_temperature(): ' + str(kwargs.get(ATTR_TEMPERATURE)))
        # Set new target temperatures.
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            # do nothing if temperature is none
            if not (self._acOptions['Pow'] == 0):
                # do nothing if HVAC is switched off
                _LOGGER.info('SyncState with SetTemInt=' + str(kwargs.get(ATTR_TEMPERATURE)))
                self.SyncState({ 'SetTemInt': int(kwargs.get(ATTR_TEMPERATURE))})
                self.schedule_update_ha_state()

    def set_operation_mode(self, hvac_mode):
        _LOGGER.info('set_hvac_mode(): ' + str(hvac_mode))
        # Set new operation mode.
        c = {}
        if (hvac_mode == STATE_OFF):
            c.update({'Pow': 0})
        else:
            c.update({'Pow': 1, 'Wmod': self._hvac_modes.index(hvac_mode)})
        
        self.SyncState(c)
        self.schedule_update_ha_state()

    @property
    def operation_list(self):
        return self._hvac_modes

    def turn_on(self):
        _LOGGER.info('turn_on(): ')
        # Turn on.
        c = {'Pow': 1}
        
        self.SyncState(c)
        self.schedule_update_ha_state()

    def turn_off(self):
        _LOGGER.info('turn_off(): ')
        # Turn off.
        c = {'Pow': 0}
        
        self.SyncState(c)
        self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(ft.partial(self.turn_on, **kwargs))

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(ft.partial(self.turn_off, **kwargs))

    # def update_state(self, status):
    #     try:
    #         self.async_added_to_hass
    #     except Exception as e:
    #         _LOGGER.debug(f"Entity {self.entity_id} update_state {repr(e)}, status = {status}")

    async def async_added_to_hass(self):
        _LOGGER.info('Gree climate device added to hass()')
        self.update()


