
import base64
import struct
import json
import socket
import random
from Cryptodome.Cipher import AES
from Cryptodome.Hash import CMAC


DEV_ADDR = 0x01FD2C43
NWK_S_KEY = bytes.fromhex("E9551506A23063EF7221D4BDEA369FA3")
APP_S_KEY = bytes.fromhex("B6F5F673E34DB644BF59ED8A2D262DC4")

FCNT = 0 # Compteur de trame


def generer_phy_payload(donnees_texte, fcnt):
    payload_bytes = donnees_texte.encode('utf-8')
    mhdr = b'\x40'
    dev_addr_bytes = struct.pack('<I', DEV_ADDR)
    fctrl = b'\x00'
    fcnt_bytes = struct.pack('<H', fcnt & 0xFFFF)
    fhdr = dev_addr_bytes + fctrl + fcnt_bytes
    fport = b'\x01'

    fcnt_32 = struct.pack('<I', fcnt)
    block_a = b'\x01\x00\x00\x00\x00\x00' + dev_addr_bytes + fcnt_32 + b'\x00\x01'
    cipher = AES.new(APP_S_KEY, AES.MODE_ECB)
    keystream = cipher.encrypt(block_a)
    encrypted_payload = bytes(a ^ b for a, b in zip(payload_bytes, keystream))

    msg = mhdr + fhdr + fport + encrypted_payload

    b0 = b'\x49\x00\x00\x00\x00\x00' + dev_addr_bytes + fcnt_32 + b'\x00' + bytes([len(msg)])
    cobj = CMAC.new(NWK_S_KEY, ciphermod=AES)
    cobj.update(b0 + msg)
    mic = cobj.digest()[:4]

    phy_payload = msg + mic
    return base64.b64encode(phy_payload).decode('utf-8')


def envoyer_udp():
    donnees = "Temp: 23.5C"
    phy_b64 = generer_phy_payload(donnees, FCNT)
    print(f"[*] Payload chiffré généré : {phy_b64}")

    gw_mac_hex = "f57fff9035b68bd5"
    gw_mac = bytes.fromhex(gw_mac_hex)
    
    token = bytes([random.randint(0, 255), random.randint(0, 255)])
    header = b'\x02' + token + b'\x00' + gw_mac

    rxpk = {
        "rxpk": [{
            "tmst": 0, "chan": 0, "rfch": 0, "freq": 868.1,
            "stat": 1, "modu": "LORA", "datr": "SF7BW125",
            "codr": "4/5", "lsnr": 10.0, "rssi": -50,
            "size": len(base64.b64decode(phy_b64)),
            "data": phy_b64
        }]
    }
    
    payload = header + json.dumps(rxpk).encode('utf-8')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(payload, ("127.0.0.1", 1700))
    
    print(f"[+] Paquet radio UDP envoyé avec succès au port 1700 (FCnt = {FCNT})")

if __name__ == "__main__":
    envoyer_udp()