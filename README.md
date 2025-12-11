# PYTHON VPP API 

## 1. Arxitektura

VPP arxitekturasi quyidagi komponentlardan iborat:

```
 +-------------------+
 |   Python Client   |  <-- Skript yoki API
 +-------------------+
           │ JSON-RPC / Thrift / gRPC
           ▼
 +-------------------+
 |   VPP API Layer   |  <-- vpp_papi yoki requests orqali bog'lanish
 +-------------------+
           │
           ▼
 +-------------------+
 |   VPP Daemon      |  <-- vector packet processing engine
 +-------------------+
           │
           ▼
 +-------------------+
 | NIC / DPDK        |  <-- Fizik yoki virtual interfeyslar 
 +-------------------+

```

### 1.1 Python Client Layer

- vpp_papi — Python kutubxonasi VPP API bilan bog‘lanish uchun.
- requests — Agar VPP REST/Flask API o‘rnatilgan bo‘lsa, HTTP orqali bog‘lanish.

### 1.2 VPP API Layer

- VPP har bir buyruqni API message shaklida oladi (binary yoki JSON).
- Masalan, sw_interface_dump — barcha interfeyslarni so‘rov qiladi.
- API chaqiruvlari asenkron ishlashi mumkin: siz javobni kutmasdan boshqa buyruqlarni yuborishingiz mumkin.

### 2.3 VPP Daemon Layer

- Paketlar batch (vektor) usulida ishlanadi.
- Har bir node (ACL, IP lookup, NAT) paketni ketma-ket qayta ishlaydi.
- VPP DPDK bilan ishlaganda, kernel bypass qilinadi va direkt NICdan paket o‘qiladi/yoziladi.


## vpp_papi — Deep Dive

#### vpp_papi — bu Python VPP API client bo‘lib, u VPP bilan bog‘lanish va API chaqiruvlarini yuborish uchun ishlatiladi. Asosan u quyidagi xususiyatlarga ega:
- Binary API orqali ishlaydi (JSON yoki REST emas).
- API dynamically generated classes yaratadi (har bir VPP xabari uchun Python class).
- Python orqali VPP session o‘rnatib, request/response almashadi.

### 1. VPP Binary API

VPP API xabarlarini binary formatda yuboradi.

Har bir API message struct shaklida C da aniqlangan (VPP .api fayllarda).

Masalan: `sw_interface_dump` yoki `acl_add_replace.`

### API ish jarayoni:
```
Python Client (vpp_papi)
       │
       │  Binary API Message
       ▼
   VPP Daemon (VPP binary API handler)
       │
       │  Binary Response
       ▼
Python Client
```
### 1. Request Flow (Python → VPP)

```
Python Script
     │
     │ call API function (e.g. sw_interface_dump)
     ▼
vpp_papi dynamic class
     │
     │ marshal to binary
     ▼
VPP socket (Unix Domain / TCP)
     │
     │ binary API message
     ▼
VPP Daemon

```

### 2. VPP ichida ishlash

```
VPP Daemon
     │
     │ receive binary message
     ▼
API Handler (sw_interface node)
     │
     │ process request
     ▼
generate reply message (binary)

```
### 3. Reply Flow (VPP → Python)
```
VPP binary reply
     │
     │ send via socket
     ▼
vpp_papi
     │
     │ unmarshal binary → Python object
     ▼
Python client
     │
     │ return list of objects
     ▼
for iface in interfaces: print(iface.sw_if_index)
```
