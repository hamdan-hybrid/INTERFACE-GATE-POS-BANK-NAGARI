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
3. Sensor menghitung orang: 1 orang = sensor terhalang lalu kembali normal.
   Saat sensor mulai terhalang, ESP mengirim `GET <domain>/api/v1/capture?qr-code=<kode tiket orang itu>`.
4. Gate hanya tertutup (relay OFF) jika jumlah orang yang lewat sudah sama dengan jumlah tiket.

Beberapa tiket bisa di-scan berturut-turut saat gate masih terbuka. Jumlahnya ditambahkan dan tiap orang
difoto dengan kode tiketnya sendiri, sesuai urutan scan.

## Isi repo

```
├── README.md
├── monitor.py                                  serial monitor tanpa me-reset ESP
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
| ESP32 DevKit (ESP32-WROOM, flash 4 MB) | |
| QR reader output Wiegand | format 26 / 34 / 66 bit atau mode teks |
| Modul relay 1 channel | **input aktif HIGH** |
| Sensor penghitung orang (beam / IR) | **output menarik ke GND saat terhalang** |
| 2 resistor 1 kΩ | jalur D0 dan D1 QR reader |
| 1 dioda (mis. 1N4148 atau Schottky 1N5819) | jalur output sensor |

Firmware ini mengharuskan relay aktif HIGH dan sensor LOW saat terhalang. Jika perangkat Anda kebalikannya,
firmware perlu di-build ulang oleh developer.

## Wiring

```
                         ESP32 DevKit
                    ┌──────────────────────┐
QR reader D0 (hijau) ──[ 1kΩ ]──► GPIO23  │
QR reader D1 (putih) ──[ 1kΩ ]──► GPIO22  │
                                          │
Relay IN ───────────────────────── GPIO26  │
                                          │
Sensor OUT ──|◄──────────────────── GPIO27  │   dioda: garis (katoda) di sisi sensor
                                          │
GND QR reader + relay + sensor ─────── GND  │   semua ground disatukan
Relay VCC ──────────────────────── 5V/VIN  │
                    └──────────────────────┘

Relay COM + NO ──► input "buka" di kontroler gate (kontak kering)
```

| Perangkat | Pin perangkat | ESP32 | Catatan |
|---|---|---|---|
| QR reader | D0 (hijau) | GPIO23 | lewat resistor 1 kΩ |
| QR reader | D1 (putih) | GPIO22 | lewat resistor 1 kΩ |
| QR reader | GND | GND | catu daya reader sesuai spesifikasinya, ground disatukan dengan ESP32 |
| Relay | IN | GPIO26 | HIGH = relay ON = gate buka |
| Relay | VCC, GND | 5V/VIN, GND | |
| Relay | COM + NO | kontroler gate | relay ON terus selama gate buka (bukan pulsa) |
| Sensor | OUT | GPIO27 | lewat dioda, katoda (bergaris) ke OUT sensor. ESP memakai pull-up internal. |
| Sensor | GND | GND | |

GPIO16 dan GPIO17 tidak dipakai.

## Flash firmware

### Cara 1: lewat browser (tanpa install)

1. Buka <https://espressif.github.io/esptool-js/> di Chrome atau Edge, colokkan ESP32 lewat USB.
2. Klik **Connect**, pilih port ESP32.
3. Isi **Flash Address** `0x0`, pilih file `firmware/hybrid-gate-ticketing.ino.merged.bin`, klik **Program**.

Cara ini memakai `merged.bin`, jadi semua setting di ESP terhapus (lihat catatan di bawah).

### Cara 2: esptool

Pasang dengan `pip install esptool`. Di Windows, ganti `/dev/ttyUSB0` dengan port COM, misalnya `COM3`.
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

Semua log hanya tampil di USB Serial (115200 baud), tidak dikirim ke Bluetooth.

```bash
python3 monitor.py /dev/ttyUSB0      # Linux, tidak me-reset ESP saat dibuka; ketik perintah lalu Enter
```

Bisa juga memakai serial monitor lain (Arduino IDE, PuTTY) di 115200 baud, akhiran baris "Newline".

Saat menyala, log menampilkan nama dan PIN Bluetooth, status WiFi, setting, hasil tes API, lalu `Siap scan QR`.

### 2. Setting lewat Bluetooth

1. Di HP Android, pairing ke **HYBRID-TICKETING** dengan PIN **123456**.
   Jika HP pernah pairing ke perangkat ini (atau ke nama lama "GATE-TICKETING"), lupakan dulu perangkatnya di HP.
2. Buka aplikasi terminal Bluetooth serial (misalnya *Serial Bluetooth Terminal*), sambungkan ke HYBRID-TICKETING.
3. Kirim satu baris:

   ```
   NAMA_WIFI;PASSWORD_WIFI;https://gate-backup.niagait.com;API_KEY_CABANG
   ```

4. ESP membalas `OK` lalu restart dengan setting baru. Jika formatnya salah, balasannya `FORMAT ERROR`.

Catatan:

- **API key:** ambil dari server pusat, menu **Cabang & API Key**. Jika bagian API key tidak ditulis
  (`NAMA_WIFI;PASSWORD_WIFI;DOMAIN`), API key yang sudah tersimpan tetap dipakai.
- **Selalu tulis `https://` untuk server lewat internet.** Tanpa itu ESP memakai http dan API key terkirim tanpa enkripsi.
- **Password WiFi tidak boleh berisi `;`.**
- **iPhone tidak bisa dipakai,** karena firmware memakai Bluetooth klasik (SPP).
- **Ganti PIN bawaan `123456` setelah pemasangan** dengan perintah `pin <angka baru>` lewat USB. Siapa pun yang tahu
  PIN bisa membuka gate lewat Bluetooth.
- **Setting tersimpan permanen,** tetap ada setelah ESP mati atau setelah update firmware (kecuali flash `merged.bin`).

### 3. Perintah

Ketik di serial monitor atau kirim lewat Bluetooth, lalu Enter. Hasilnya tampil di serial monitor.

| Perintah | Fungsi |
|---|---|
| `info` | tampilkan setting dan status gate |
| `3` atau `qty 3` | buka gate untuk 3 orang tanpa tiket (tanpa cek server, tanpa foto) |
| `scan <kode>` | simulasi scan QR (lewat server dan capture, sama seperti reader) |
| `ssid <nama>` | ganti nama WiFi, lalu `restart` |
| `pass <password>` | ganti password WiFi, lalu `restart` |
| `domain <alamat>` | ganti server, langsung berlaku |
| `apikey <key>` | ganti API key, langsung berlaku. `apikey hapus` untuk mengosongkan. |
| `pin <4-16 angka>` | ganti PIN Bluetooth, **hanya lewat USB**, lalu `restart`. Semua HP harus pairing ulang. |
| `restart` | restart ESP |

### 4. Pilihan server

| Domain | API key | Capture foto |
|---|---|---|
| Server pusat, `https://gate-backup.niagait.com` | wajib | Server pusat meneruskan ke BackEnd Gate cabang. **URL BackEnd Gate** cabang harus diisi di menu Cabang dan bisa dihubungi dari server pusat. |
| BackEnd Gate cabang, `http://<ip>:3000` | tidak perlu | langsung diambil BackEnd Gate |

Jika capture gagal, gate tetap buka dan tutup normal, hanya fotonya yang tidak ada.

### 5. Contoh log saat dipakai

```
QR: 4829175036
GET https://gate-backup.niagait.com/api/v1/scan-qr?qr-code=4829175036
HTTP 200: {"status":true,"msg":"Tiket valid, silakan masuk.","jum_tiket":"2"}
GATE BUKA (lewat 0/2)
Sensor: TERHALANG
GET https://gate-backup.niagait.com/api/v1/capture?qr-code=4829175036
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
| `WiFi belum di-setting` | ESP baru, atau setelah flash `merged.bin` | kirim setting lewat Bluetooth |
| `API: API key ditolak server` atau `HTTP 401` | API key kosong atau salah | kirim ulang setting lewat Bluetooth, atau `apikey <key>` |
| `HTTP 404 ... Tiket tidak ditemukan` | tiket tidak ada, atau milik cabang lain | cek API key cabang yang dipakai |
| `HTTP 409 ... sudah tervalidasi` | tiket sudah pernah dipakai masuk | tiket tidak bisa dipakai dua kali |
| `Tidak bisa terhubung ke server (WiFi RSSI ...)` | domain salah, server mati, atau sinyal lemah | cek `info`, coba domain di browser, cek RSSI (lebih rendah dari -80 dBm berarti lemah) |
| `WiFi putus, tiket tidak bisa dicek` | WiFi terputus atau belum di-setting | ESP mencoba konek ulang tiap 10 detik |
| `CAPTURE ...: HTTP 503` | URL BackEnd Gate cabang belum diisi di server pusat | isi di menu Cabang |
| `CAPTURE ...: HTTP 502` | BackEnd Gate tidak bisa dihubungi dari server pusat | cek BackEnd Gate menyala dan URL-nya benar |
| `CAPTURE ...: HTTP 404` | tiket belum masuk ke BackEnd Gate | cek sinkron transaksi ke BackEnd Gate |
| `Wiegand N bit: format tidak dikenal` | format output reader tidak dikenali | set reader ke Wiegand 26/34 atau mode teks |
| Tidak ada log `Sensor:` saat dilalui, atau terbalik | wiring sensor atau dioda, atau logika sensor terbalik | cek arah dioda dan GND bersama. Logika terbalik perlu build ulang. |
| HP tidak diminta PIN atau gagal tersambung | data pairing lama masih tersimpan di HP | lupakan perangkat di HP, pairing ulang |
| `BLUETOOTH: gagal start` | stack Bluetooth gagal menyala | `restart`. Gate tetap berjalan tanpa Bluetooth. |
| Gate tidak menutup | jumlah yang lewat belum sama dengan jumlah tiket | tunggu sisa pengunjung, atau `restart` |
