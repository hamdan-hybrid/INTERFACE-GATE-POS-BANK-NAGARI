# Interface Gate POS - Hybrid Ticketing (ESP32)

Firmware siap flash untuk ESP32 di flap gate tiket: scan QR tiket, cek ke server, buka gate, hitung orang yang
lewat, dan minta foto (capture) untuk tiap orang.

Build: 21 November 2026 · ESP32 core 3.3.12 · board ESP32 Dev Module, partisi Huge APP, flash 4 MB.

## Daftar isi

- [Cara kerja](#cara-kerja)
- [Isi repo](#isi-repo)
- [Komponen](#komponen)
- [Wiring](#wiring)
- [Flash firmware](#flash-firmware)
- [Cara penggunaan](#cara-penggunaan)
- [Masalah umum](#masalah-umum)

## Cara kerja

1. QR reader (Wiegand) membaca kode tiket.
2. ESP mengirim `GET <domain>/api/v1/scan-qr?qr-code=<kode>` (API key di header `X-API-Key`).
   Jika server membalas `"status": true`, relay ON (gate buka) untuk `jum_tiket` orang.
   Jika server tidak menjawab dalam 3 detik (paket hilang di jaringan), ESP langsung mengulang sekali dengan
   `&retry=1`. Server (Gate Guard 2.0.1 ke atas) tetap menjawab valid walau permintaan pertama sudah memvalidasi tiket, jadi tiket tidak
   hangus. Scan ulang tiket yang sama dalam 30 detik setelah gagal juga dikirim dengan `&retry=1`.
3. Sensor menghitung orang: 1 orang = sensor terhalang lalu kembali normal.
   Saat sensor mulai terhalang, ESP mengirim `GET <domain>/api/v1/capture?qr-code=<kode tiket orang itu>`.
4. Gate hanya tertutup (relay OFF) jika jumlah orang yang lewat sudah sama dengan jumlah tiket.

Beberapa tiket bisa di-scan berturut-turut saat gate masih terbuka. Jumlahnya ditambahkan dan tiap orang
difoto dengan kode tiketnya sendiri, sesuai urutan scan.

## Isi repo

```
├── README.md
├── monitor.py                                  serial monitor tanpa me-reset ESP
├── gambar/                                     diagram wiring
└── firmware/
    ├── hybrid-gate-ticketing.ino.merged.bin    semua dalam satu file (untuk ESP baru)
    ├── hybrid-gate-ticketing.ino.bin           aplikasi
    ├── hybrid-gate-ticketing.ino.bootloader.bin
    ├── hybrid-gate-ticketing.ino.partitions.bin
    ├── boot_app0.bin
    └── SHA256SUMS                              checksum untuk cek file tidak rusak
```

## Komponen

| Komponen | Keterangan |
|---|---|
| ESP32 DevKit (ESP32-WROOM, flash 4 MB) | board "ESP32 Dev Module" |
| QR reader output Wiegand | format 26 / 34 / 66 bit atau mode teks |
| Modul relay 1 channel | input aktif HIGH |
| Sensor penghitung orang (beam / IR) | NPN NO, 12 V DC, 3 kabel (coklat +V, biru 0V, hitam OUT) |
| Optocoupler PC817 | memisahkan sinyal sensor 12 V dari ESP32 |
| 3 resistor 1 kΩ | jalur D0 dan D1 QR reader, LED PC817 |
| 1 resistor 10 kΩ | pull-up GPIO15 ke 3V3 |

## Wiring

### Ringkasan pin

| Perangkat | Kabel / pin | ESP32 | Catatan |
|---|---|---|---|
| QR reader | D0 · hijau | **GPIO21** (D21) | lewat resistor 1 kΩ |
| QR reader | D1 · putih | **GPIO22** (D22) | lewat resistor 1 kΩ |
| QR reader | GND · hitam | **GND** | satukan juga dengan − adaptor reader |
| Relay | IN | **GPIO2** (D2) | HIGH = relay ON = gate buka. LED biru di board ikut nyala. |
| Relay | VCC | **VIN** | 5 V dari USB / VIN |
| Relay | GND | **GND** | |
| Relay | COM + NO | kontroler gate | input "buka" (kontak kering), ON terus selama gate buka |
| Sensor orang | PC817 kaki 4 (kolektor) | **GPIO15** (D15) | + resistor 10 kΩ ke **3V3** |
| Sensor orang | PC817 kaki 3 (emitor) | **GND** | |

### Posisi pin di board

![Peta pin ESP32 DevKit 30 pin dan pin yang dipakai](gambar/wiring-board.svg)

Board ESP32 DevKit V1 30 pin, dilihat dari atas, port USB di bawah. Board 38 pin punya urutan pin yang berbeda:
cari tulisan D2, D15, D21, D22, GND, VIN dan 3V3 di board. Semua pin GND tersambung di dalam board, jadi boleh pakai
yang mana saja.

### QR reader

![Wiring QR reader ke ESP32](gambar/wiring-qr-reader.svg)

Resistor 1 kΩ dipasang seri di kabel D0 dan D1. GND reader, − adaptor reader, dan GND ESP32 harus tersambung jadi
satu. Tanpa ground bersama, pulsa Wiegand tidak terbaca. Reader juga harus disetel ke mode output Wiegand.

### Relay gate

![Wiring relay ke ESP32 dan kontroler gate](gambar/wiring-relay.svg)

COM dan NO relay masuk ke input "buka" kontroler gate (kontak kering, tanpa tegangan dari ESP). Relay ON terus
selama gate buka, bukan pulsa. Modul relay harus **aktif HIGH**. Modul relay aktif LOW perlu firmware yang di-build ulang oleh developer.

GPIO2 juga pin boot ESP32. Dengan modul relay aktif HIGH, upload firmware tetap normal. Jika upload gagal, cabut
kabel IN relay selama upload.

### Sensor orang dengan PC817

Yang dipakai: sensor **NPN NO, 12 V DC, 3 kabel** (coklat, biru, hitam), IC **PC817**, resistor **1 kΩ** dan
**10 kΩ**. Sensor diberi daya dari adaptor 12 V yang sama dengan QR reader.

![Wiring sensor NPN lewat PC817 ke GPIO15](gambar/wiring-sensor-pc817.svg)

- Coklat (+V) ke + adaptor 12 V, dan lewat resistor 1 kΩ ke kaki 1 PC817.
- Hitam (OUT) ke kaki 2 PC817.
- Biru (0V) ke − adaptor 12 V.
- Kaki 4 PC817 ke GPIO15, dengan resistor 10 kΩ dari GPIO15 ke 3V3. Kaki 3 PC817 ke GND ESP32.

Logika: kosong → GPIO15 **HIGH**, terhalang → LED di PC817 menyala → GPIO15 **LOW**. Ini sudah sesuai firmware.
Jika sensor Anda kebalikannya (HIGH saat terhalang), firmware perlu di-build ulang oleh developer.

### Cek sebelum dinyalakan

- [ ] GND QR reader, − adaptor reader, dan GND ESP32 tersambung jadi satu.
- [ ] Resistor 10 kΩ pull-up ke **3V3**, bukan ke VIN atau 5V. Tegangan 5V di GPIO15 bisa merusak ESP.
- [ ] Kabel 12 V sensor (coklat dan kaki 1 PC817) tidak menyentuh pin ESP sama sekali.
- [ ] Resistor 1 kΩ terpasang antara kabel coklat dan kaki 1 PC817. Tanpa resistor ini, LED di PC817 terbakar.
- [ ] QR reader disetel ke mode output Wiegand dan berbunyi beep saat scan.
- [ ] Tidak ada kabel di pin EN. Kabel yang masuk ke EN membuat ESP terus-menerus restart.

GPIO16 dan GPIO17 tidak dipakai lagi (dulu untuk modul audio, sudah dihapus).

## Flash firmware

### Cara 1: lewat browser (tanpa install)

1. Buka <https://espressif.github.io/esptool-js/> di Chrome atau Edge, colokkan ESP32 lewat USB.
2. Klik **Connect**, pilih port ESP32.
3. Isi **Flash Address** `0x0`, pilih file `firmware/hybrid-gate-ticketing.ino.merged.bin`, klik **Program**.

Cara ini memakai `merged.bin`, jadi semua setting di ESP terhapus (lihat catatan di bawah).

### Cara 2: esptool

Pasang dengan `pip install esptool`. Di Windows, ganti `/dev/ttyUSB0` dengan port COM, misalnya `COM3`.
Jika upload gagal dengan `No more data to read from the serial port`, ganti `--baud 921600` menjadi
`--baud 115200` (lebih lambat tapi lebih stabil) atau ganti kabel USB.
Untuk esptool versi 4, ganti `esptool` menjadi `esptool.py` dan `write-flash` menjadi `write_flash`.

Update firmware, setting tetap tersimpan:

```bash
cd firmware
esptool --chip esp32 --port /dev/ttyUSB0 --baud 921600 write-flash \
  0x1000  hybrid-gate-ticketing.ino.bootloader.bin \
  0x8000  hybrid-gate-ticketing.ino.partitions.bin \
  0xe000  boot_app0.bin \
  0x10000 hybrid-gate-ticketing.ino.bin
```

ESP baru, satu file:

```bash
cd firmware
esptool --chip esp32 --port /dev/ttyUSB0 --baud 921600 write-flash 0x0 hybrid-gate-ticketing.ino.merged.bin
```

> `merged.bin` menimpa seluruh flash 4 MB, termasuk area setting. WiFi, domain, API key, PIN, dan daftar HP
> yang sudah pairing kembali ke bawaan. Setelah itu kirim ulang setting lewat Bluetooth.

Setting bawaan setelah flash pertama:

| Setting | Bawaan |
|---|---|
| WiFi | kosong, wajib di-setting lewat Bluetooth |
| Domain | `http://10.10.1.104:3000` |
| API key | kosong |
| Nama Bluetooth | `HYBRID-TICKETING` |
| PIN Bluetooth | `123456` |

Cek file tidak rusak setelah download: `cd firmware && sha256sum -c SHA256SUMS`.

## Cara penggunaan

### 1. Lihat log

Log tampil di USB Serial (115200 baud) dan juga dikirim ke Bluetooth selama ada HP yang tersambung
(aplikasi terminal Bluetooth, lihat bagian 2). Log saat boot, sebelum HP tersambung, hanya ada di USB Serial.

```bash
python3 monitor.py /dev/ttyUSB0      # tidak me-reset ESP saat dibuka; ketik perintah lalu Enter
```

Bisa juga memakai serial monitor lain (Arduino IDE, PuTTY) di 115200 baud, akhiran baris "Newline".

Saat menyala, log menampilkan nama dan PIN Bluetooth, status WiFi, setting, hasil tes API, lalu `Siap scan QR`.

### 2. Setting lewat Bluetooth

1. Di HP Android, pairing ke **HYBRID-TICKETING** dengan PIN **123456**.
   Jika HP pernah pairing ke perangkat ini (atau ke nama lama "GATE-TICKETING"), lupakan dulu perangkatnya di HP.
2. Buka aplikasi terminal Bluetooth serial (misalnya *Serial Bluetooth Terminal*), sambungkan ke HYBRID-TICKETING.
3. Kirim satu baris:

   ```
   NAMA_WIFI;PASSWORD_WIFI;http://gate-backup.niagait.com;API_KEY_CABANG
   ```

4. ESP membalas `OK` lalu restart dengan setting baru. Jika formatnya salah, balasannya `FORMAT ERROR`.

Catatan:

- **API key:** ambil dari server pusat, menu **Cabang & API Key**. Jika bagian API key tidak ditulis
  (`NAMA_WIFI;PASSWORD_WIFI;DOMAIN`), API key yang sudah tersimpan tetap dipakai.
- **Pakai `http://`, jangan `https://`.** RAM ESP32 tidak cukup untuk https selama Bluetooth aktif (sisa sekitar
  17 KB, https butuh sekitar 40 KB), sehingga semua scan gagal dengan log `TLS error ... Memory allocation failed`.
  Akibatnya API key terkirim tanpa enkripsi. Lebih aman memakai BackEnd Gate cabang di jaringan lokal (`http://<ip>:3000`).
- **Password WiFi tidak boleh berisi `;`.**
- **iPhone tidak bisa dipakai,** karena firmware memakai Bluetooth klasik (SPP).
- **Ganti PIN bawaan `123456` setelah pemasangan** dengan perintah `pin <angka baru>` (lewat USB atau Bluetooth). Siapa pun yang tahu
  PIN bisa membuka gate lewat Bluetooth.
- **Setting tersimpan permanen** dan tetap ada setelah ESP mati atau setelah upload firmware baru (kecuali flash
  `merged.bin`, lihat [Flash firmware](#flash-firmware)).

### 3. Perintah

Ketik di serial monitor atau kirim lewat Bluetooth, lalu Enter. Hasilnya tampil di serial monitor.

| Perintah | Fungsi |
|---|---|
| `info` | tampilkan setting dan status gate |
| `3` atau `qty 3` | buka gate untuk 3 orang tanpa tiket (tanpa cek server, tanpa foto) |
| `scan <kode>` | simulasi scan QR (lewat server dan capture, sama seperti reader) |
| `lewat` | tes hitung 1 orang lewat tanpa sensor (tanpa foto). Ditolak selama sensor terhalang |
| `ssid <nama>` | ganti nama WiFi, lalu `restart` |
| `pass <password>` | ganti password WiFi, lalu `restart` |
| `domain <alamat>` | ganti server, langsung berlaku |
| `apikey <key>` | ganti API key, langsung berlaku. `apikey hapus` untuk mengosongkan. |
| `pin <4-16 angka>` | ganti PIN Bluetooth (lewat USB atau Bluetooth), lalu `restart`. Semua HP harus pairing ulang dengan PIN baru. |
| `restart` | restart ESP |

### 4. Pilihan server

| Domain | API key | Capture foto |
|---|---|---|
| Server pusat, `http://gate-backup.niagait.com` | wajib | Server pusat meneruskan ke BackEnd Gate cabang. **URL BackEnd Gate** cabang harus diisi di menu Cabang dan bisa dihubungi dari server pusat. |
| BackEnd Gate cabang, `http://<ip>:3000` | tidak perlu | langsung diambil BackEnd Gate |

Jika capture gagal, gate tetap buka dan tutup normal, hanya fotonya yang tidak ada.

### 5. Contoh log saat dipakai

```
QR: 4829175036
GET http://gate-backup.niagait.com/api/v1/scan-qr?qr-code=4829175036
HTTP 200: {"status":true,"msg":"Tiket valid, silakan masuk.","jum_tiket":"2"}
GATE BUKA (lewat 0/2)
Sensor: TERHALANG
GET http://gate-backup.niagait.com/api/v1/capture?qr-code=4829175036
CAPTURE 4829175036: HTTP 202
Sensor: NORMAL
Lewat 1/2
...
Lewat 2/2
GATE TUTUP
```

## Masalah umum

| Log / gejala | Penyebab | Solusi |
|---|---|---|
| `API: API key ditolak server` atau `HTTP 401` | API key kosong atau salah | kirim ulang setting lewat Bluetooth, atau `apikey <key>` |
| `HTTP 404 ... Tiket tidak ditemukan` | tiket tidak ada, atau milik cabang lain | cek API key cabang yang dipakai |
| `HTTP 409 ... sudah tervalidasi` | tiket sudah pernah dipakai masuk | tiket tidak bisa dipakai dua kali |
| `TLS error -32512: SSL - Memory allocation failed` | domain memakai `https://`, RAM tidak cukup | ganti ke `http://` dengan perintah `domain` |
| `Tidak bisa terhubung ke server (WiFi RSSI ...)` | domain salah, server mati, atau sinyal lemah | cek `info`, coba domain di browser, cek RSSI (lebih rendah dari -80 dBm berarti lemah) |
| `WiFi belum di-setting` | ESP baru, atau setelah flash `merged.bin` | kirim setting lewat Bluetooth |
| `WiFi putus, tiket tidak bisa dicek` | WiFi terputus atau belum di-setting | ESP mencoba konek ulang tiap 10 detik |
| `CAPTURE ...: HTTP 503` | URL BackEnd Gate cabang belum diisi di server pusat | isi di menu Cabang |
| `CAPTURE ...: HTTP 502` | BackEnd Gate tidak bisa dihubungi dari server pusat | cek BackEnd Gate menyala dan URL-nya benar |
| `CAPTURE ...: HTTP 404` | tiket belum masuk ke BackEnd Gate | cek sinkron transaksi ke BackEnd Gate |
| `Wiegand N bit: format tidak dikenal` | format output reader tidak dikenali | set reader ke Wiegand 26/34 atau mode teks |
| Tidak ada log `Sensor:` saat dilalui, atau terbalik | wiring sensor / PC817, atau logika sensor terbalik | cek resistor 1 kΩ di kaki 1 PC817 dan pull-up 10 kΩ. Logika terbalik perlu build ulang. |
| HP tidak diminta PIN atau gagal tersambung | data pairing lama masih tersimpan di HP | lupakan perangkat di HP, pairing ulang |
| `BLUETOOTH: gagal start` | stack Bluetooth gagal menyala | `restart`. Gate tetap berjalan tanpa Bluetooth. |
| Gate tidak menutup | jumlah yang lewat belum sama dengan jumlah tiket | tunggu sisa pengunjung, atau `restart` |
| Upload gagal `No more data to read from the serial port` | kabel USB / port kurang stabil di kecepatan tinggi | pakai `--baud 115200` atau ganti kabel USB |
