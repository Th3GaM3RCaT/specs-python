# ejemplo M-SEARCH SSDP (UDP broadcast)
import socket, time

MSEARCH = '\r\n'.join([
  'M-SEARCH * HTTP/1.1',
  'HOST:239.255.255.250:1900',
  'MAN:"ssdp:discover"',
  'MX:2',
  'ST:ssdp:all',
  '', ''
])

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.settimeout(3)
s.sendto(MSEARCH.encode('utf-8'), ('239.255.255.250', 1900))
start = time.time()
while True:
    try:
        data, addr = s.recvfrom(65507)
        print("RESP from", addr, data[:200])
    except socket.timeout:
        break
    if time.time() - start > 4:
        break
s.close()
