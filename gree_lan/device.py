import socket
import base64
import logging


from .const import GENERIC_GREE_DEVICE_KEY,GENERIC_GREE_DEVICE_KEY_GCM


_LOGGER = logging.getLogger(__name__)

from Crypto.Cipher import AES
try: import simplejson
except ImportError: import json as simplejson


class MockGreeDevice:
    def __init__(self, ip,  mac, port):
        self._ip = ip
        self._port = port
        self._mac = mac
        self._timeout = 10
        self.encryption_version = 1
        self.CIPHER = None
        self._encryption_key = None
        self.GCM_IV = b'\x54\x40\x78\x44\x49\x67\x5a\x51\x6c\x5e\x63\x13'
        self.GCM_ADD = b'qualcomm-test'
        


    def Scan(self,ip):
        json = '{"t": "scan"}'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(self._timeout)
        sock.sendto(bytes(json, "utf-8"), (ip, self._port))
        data, addr = sock.recvfrom(64000)
        sock.close()
        receivedJson = simplejson.loads(data)
        
        _LOGGER.info('2222222222------------------------------------------------------------')
        _LOGGER.info(addr)
        _LOGGER.info(receivedJson)

        # try:
        # cipher = AES.new(GENERIC_GREE_DEVICE_KEY.encode("utf8"), AES.MODE_ECB)
        # loadedJsonPack = self.FetchResult(cipher, json).encode("utf8")
        # _LOGGER.info(loadedJsonPack)
        # except:
        #     try:
        #         loadedJsonPack_gcm = self.FetchResult(self.GetGCMCipher(GENERIC_GREE_DEVICE_KEY_GCM),  json).encode("utf8")
        #         self.encryption_version = 2
        #         return loadedJsonPack_gcm
        #     except:
        #         _LOGGER.error('无法获取设备')
        #         return False
        # else:
        #     return loadedJsonPack
        

    # Pad helper method to help us get the right string for encrypting
    def Pad(self, s):
        aesBlockSize = 16
        return s + (aesBlockSize - len(s) % aesBlockSize) * chr(aesBlockSize - len(s) % aesBlockSize)            

    def FetchResult(self, cipher, json):
        _LOGGER.info('Fetching(%s, %s, %s, %s)' % (self._ip, self._port, self._timeout, json))
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        clientSock.settimeout(self._timeout)
        clientSock.sendto(bytes(json, "utf-8"), (self._ip, self._port))
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
        _LOGGER.info(loadedJsonPack) 
        return loadedJsonPack

    def GetDeviceKey(self):
        _LOGGER.info('Retrieving HVAC encryption key')
        cipher = AES.new(GENERIC_GREE_DEVICE_KEY.encode("utf8"), AES.MODE_ECB)
        pack = base64.b64encode(cipher.encrypt(self.Pad('{"mac":"' + str(self._mac) + '","t":"bind","uid":0}').encode("utf8"))).decode('utf-8')
        jsonPayloadToSend = '{"cid": "app","i": 1,"pack": "' + pack + '","t":"pack","tcid":"' + str(self._mac) + '","uid": 0}'
        try:
            self._encryption_key = self.FetchResult(cipher, jsonPayloadToSend)['key'].encode("utf8")
        except:
            _LOGGER.error('Error getting device encryption key!')
            return False
        else:
            self.CIPHER = AES.new(self._encryption_key, AES.MODE_ECB)
            return True
        
    def GetGCMCipher(self, key):
        cipher = AES.new(key, AES.MODE_GCM, nonce=self.GCM_IV)
        cipher.update(self.GCM_ADD)
        return cipher

    def EncryptGCM(self, key, plaintext):
        encrypted_data, tag = self.GetGCMCipher(key).encrypt_and_digest(plaintext.encode("utf8"))
        pack = base64.b64encode(encrypted_data).decode('utf-8')
        tag = base64.b64encode(tag).decode('utf-8')
        return (pack, tag)

    def GetDeviceKeyGCM(self):
        plaintext = '{"cid":"' + str(self._mac) + '", "mac":"' + str(self._mac) + '","t":"bind","uid":0}'
        pack, tag = self.EncryptGCM(GENERIC_GREE_DEVICE_KEY_GCM, plaintext)
        jsonPayloadToSend = '{"cid": "app","i": 1,"pack": "' + pack + '","t":"pack","tcid":"' + str(self._mac) + '","uid": 0, "tag" : "' + tag + '"}'
        try:
            self._encryption_key = self.FetchResult(self.GetGCMCipher(GENERIC_GREE_DEVICE_KEY_GCM),  jsonPayloadToSend)['key'].encode("utf8")
        except:
            _LOGGER.error('Error getting device encryption key!')
            return False
        else:
            return True
        
    def GetEncryptionVersion(self):
        if not self._encryption_key:
            if self.GetDeviceKey():
                self.encryption_version = 1 
                return True
            elif  self.GetDeviceKeyGCM():
                self.encryption_version = 2
                return True
            else:
                _LOGGER.error('Error getting device encryption key!')
                raise Exception("Connection failed")
        else:
            return False


    async def GreeGetValues(self, propertyNames):
        try:
            if self.GetEncryptionVersion():
                await self.GreeGetValues( propertyNames)
        except:
            return
        plaintext = '{"cols":' + simplejson.dumps(propertyNames) + ',"mac":"' + str(self._mac) + '","t":"status"}'
        if self.encryption_version == 1:
            cipher = self.CIPHER
            jsonPayloadToSend = '{"cid":"app","i":0,"pack":"' + base64.b64encode(cipher.encrypt(self.Pad(plaintext).encode("utf8"))).decode('utf-8') + '","t":"pack","tcid":"' + str(self._mac) + '","uid": 0}'
        elif self.encryption_version == 2:
            pack, tag = self.EncryptGCM(self._encryption_key, plaintext)
            jsonPayloadToSend = '{"cid":"app","i":0,"pack":"' + pack + '","t":"pack","tcid":"' + str(self._mac) + '","uid": 0,"tag" : "' + tag + '"}'
            cipher = self.GetGCMCipher(self._encryption_key)
        return self.FetchResult(cipher, jsonPayloadToSend)['dat']

    
        
    async def SendStateToAc(self, Options):
        try:
            if self.GetEncryptionVersion():
                await self.SendStateToAc(Options)
        except:
            return
        opt = ','.join(f'"{k}"' for k in Options.keys()) 
        p = ','.join(str(v) for v in Options.values()) 
        statePackJson = '{"opt":[' + opt + '],"p":[' + p + '],"t":"cmd"}'
        _LOGGER.info(statePackJson)
        if self.encryption_version == 1:
            cipher = self.CIPHER
            sentJsonPayload = '{"cid":"app","i":0,"pack":"' + base64.b64encode(cipher.encrypt(self.Pad(statePackJson).encode("utf8"))).decode('utf-8') + '","t":"pack","tcid":"' + str(self._mac) + '","uid": 0}'
        elif self.encryption_version == 2:
            pack, tag = self.EncryptGCM(self._encryption_key, statePackJson)
            sentJsonPayload = '{"cid":"app","i":0,"pack":"' + pack + '","t":"pack","tcid":"' + str(self._mac) + '","uid": 0,"tag":"' + tag +'"}'
            cipher = self.GetGCMCipher(self._encryption_key)
        receivedJsonPayload = self.FetchResult(cipher,  sentJsonPayload)
        _LOGGER.info('Done sending state to HVAC: ' + str(receivedJsonPayload))




