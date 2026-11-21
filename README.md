# Interface Gate POS - Hybrid Ticketing (ESP32)

Firmware siap upload untuk **ESP32 DevKit (ESP32-WROOM-32)** di flap gate tiket: scan QR tiket, cek ke server,
buka gate, hitung orang yang lewat, dan minta foto (capture) untuk tiap orang. Setting dan log lewat Bluetooth.

Versi firmware: lihat [`firmware/VERSI.txt`](firmware/VERSI.txt). Versi yang terpasang tampil di log saat boot
(`=== HYBRID TICKETING 1.0.0 ===`) dan di perintah `info` (baris `Firmware:`).

## Daftar isi

- [Cara kerja](#cara-kerja)
- [Isi folder](#isi-folder)
- [Upload firmware](#upload-firmware)
- [Komponen](#komponen)
- [Wiring](#wiring)
- [Cara penggunaan](#cara-penggunaan)
  - [Ganti PIN Bluetooth](#4-ganti-pin-bluetooth)
  - [Tes gate dan perintah `lewat`](#5-tes-gate-dan-perintah-lewat)
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

## Isi folder

| Folder / file | Isi |
|---|---|
| `upload.sh` | Upload firmware (Linux) |
| `firmware/` | File firmware (`*.bin`) dan `VERSI.txt` (versi, alamat flash, SHA256) |
| `tools/` | esptool (dipakai otomatis oleh `upload.sh`) |
| `monitor.py` | Serial monitor tanpa me-reset ESP |
| `gambar/` | Diagram wiring |

## Upload firmware

Download folder ini (`git clone`, atau **Code → Download ZIP** di GitHub lalu ekstrak). Colokkan ESP32, buka
terminal di folder ini, lalu jalankan:

```
bash upload.sh
```

Tunggu sampai muncul `SELESAI`, ESP32 restart sendiri.
Jika muncul `Tidak punya izin ke /dev/ttyUSB0`, jalankan sekali `sudo usermod -aG dialout $USER`, lalu logout dan
login lagi.

### Pilihan upload

| Perintah | Kegunaan |
|---|---|
| `bash upload.sh` | Update firmware. WiFi, domain, API key, PIN Bluetooth, dan pairing HP **tetap**. |
| `bash upload.sh --erase` | ESP32 **baru** / reset total. Semua setting terhapus, PIN Bluetooth kembali `123456`, pairing HP hilang. |
| `bash upload.sh /dev/ttyUSB1` | Pilih port jika ada lebih dari satu. |
| `BAUD=115200 bash upload.sh` | Langsung upload pelan. Biasanya tidak perlu: jika gagal, `upload.sh` otomatis mengulang di 115200. |

Setting bawaan untuk ESP32 baru atau setelah `--erase`:

| Setting | Bawaan |
|---|---|
| WiFi | kosong, wajib di-setting lewat Bluetooth (lihat [Setting lewat Bluetooth](#2-setting-lewat-bluetooth)) |
| Domain | `http://10.10.1.104:3000` |
| API key | kosong |
| Nama Bluetooth | `HYBRID-TICKETING` |
| PIN Bluetooth | `123456` |

### Jika gagal

| Pesan | Solusi |
|---|---|
| `ESP32 tidak terdeteksi` | Ganti kabel USB (harus kabel data), coba port USB lain. |
| `Failed to connect` / `No serial data received` | Cabut kabel IN relay dari D2 selama upload (GPIO2 juga pin boot ESP32). Masih gagal: tahan tombol **BOOT** di ESP32 saat upload, lepas setelah muncul `Writing`. |
| `This chip is ESP32-S3, not ESP32` (atau chip lain) | Board salah, firmware ini hanya untuk ESP32-WROOM-32. |
| `upload.sh hanya untuk Linux 64-bit` | Pakai laptop / PC Linux 64-bit, atau [upload lewat browser](#upload-lewat-browser-windows--mac). |
| `UPLOAD GAGAL` (setelah diulang otomatis di 115200) | Ganti kabel USB yang lebih pendek / bagus, colok langsung ke laptop (tanpa hub USB). |
| Karakter aneh `����` di serial monitor sesaat setelah restart | Normal, abaikan. |

### Upload lewat browser (Windows / Mac)

Tanpa memasang apa pun, memakai Chrome atau Edge.

1. Buka <https://espressif.github.io/esptool-js/>, colokkan ESP32 lewat USB.
2. Klik **Connect**, pilih port ESP32.
3. Isi alamat dan file berikut dari folder `firmware/` (klik **Add File** untuk menambah baris):

   | Flash Address | File |
   |---|---|
   | `0x1000` | `bootloader.bin` |
   | `0x8000` | `partitions.bin` |
   | `0xe000` | `boot_app0.bin` |
   | `0x10000` | `firmware.bin` |

4. Klik **Program**. Setelah selesai, tekan tombol **EN** di ESP32 (atau cabut lalu colok lagi USB-nya).

Setting tetap tersimpan, sama seperti `bash upload.sh`. Untuk ESP32 baru / reset total (sama seperti `--erase`),
klik **Erase Flash** dulu sebelum **Program**.

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

## Cara penggunaan

### 1. Lihat log

Log tampil di USB Serial (115200 baud) dan juga dikirim ke Bluetooth selama ada HP yang tersambung
(aplikasi terminal Bluetooth, lihat bagian 2). Log saat boot, sebelum HP tersambung, hanya ada di USB Serial.

```bash
python3 monitor.py /dev/ttyUSB0      # tidak me-reset ESP saat dibuka; ketik perintah lalu Enter
```

Bisa juga memakai serial monitor lain (Arduino IDE, PuTTY) di 115200 baud, akhiran baris "Newline".

Saat menyala, log menampilkan versi firmware (`=== HYBRID TICKETING 1.0.0 ===`), nama dan PIN Bluetooth, status
WiFi, setting, hasil tes API, lalu `Siap scan QR`.

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
- **Setting tersimpan permanen** dan tetap ada setelah ESP mati atau setelah upload firmware baru (kecuali
  `bash upload.sh --erase`, lihat [Pilihan upload](#pilihan-upload)).

### 3. Perintah

Ketik di serial monitor atau kirim lewat Bluetooth, lalu Enter. Hasilnya tampil di serial monitor.

| Perintah | Fungsi |
|---|---|
| `info` | tampilkan versi firmware, setting, dan status gate |
| `3` atau `qty 3` | buka gate untuk 3 orang tanpa tiket (tanpa cek server, tanpa foto) |
| `scan <kode>` | simulasi scan QR (lewat server dan capture, sama seperti reader) |
| `lewat` | tes hitung 1 orang lewat tanpa sensor (tanpa foto). Ditolak selama sensor terhalang. Lihat [Tes gate](#5-tes-gate-dan-perintah-lewat) |
| `ssid <nama>` | ganti nama WiFi, lalu `restart` |
| `pass <password>` | ganti password WiFi, lalu `restart` |
| `domain <alamat>` | ganti server, langsung berlaku |
| `apikey <key>` | ganti API key, langsung berlaku. `apikey hapus` untuk mengosongkan. |
| `pin <4-16 angka>` | ganti PIN Bluetooth (lewat USB atau Bluetooth), lalu `restart`. Semua HP harus pairing ulang dengan PIN baru. Lihat [Ganti PIN](#4-ganti-pin-bluetooth) |
| `restart` | restart ESP |

### 4. Ganti PIN Bluetooth

PIN bawaan adalah `123456`. Ganti setelah pemasangan, karena siapa pun yang tahu PIN bisa membuka gate lewat Bluetooth.

**Sintaks:**

```
pin <PIN baru>
```

PIN harus berupa angka, 4 sampai 16 digit. Contoh: `pin 482913`.

**Langkah lewat HP (Bluetooth):**

1. Sambungkan HP ke **HYBRID-TICKETING** di aplikasi terminal Bluetooth, masih dengan PIN lama.
2. Kirim `pin 482913` (ganti dengan PIN baru Anda). Balasannya:

   ```
   BLUETOOTH: pin ***
   OK, btpin disimpan
   Ketik 'restart' agar PIN baru dipakai (semua HP harus pairing ulang)
   ```

3. Kirim `restart`. Bluetooth terputus dan ESP menyala ulang. Tunggu sekitar 15 detik.
4. Di HP, buka **Pengaturan > Bluetooth**, pilih **HYBRID-TICKETING**, lalu **Lupakan** (Unpair).
5. Pairing ulang ke HYBRID-TICKETING dengan **PIN baru**, lalu sambungkan lagi di aplikasi terminal.

**Langkah lewat USB:** ketik `pin 482913` lalu `restart` di serial monitor. Setelah restart, log menampilkan:

```
BLUETOOTH: daftar HP yang sudah pairing dihapus, pairing ulang dengan PIN
BLUETOOTH: ON
NAME: HYBRID-TICKETING
PIN : 482913
```

Catatan:

- **PIN baru baru berlaku setelah `restart`.** Sebelum restart, PIN lama masih dipakai.
- **PIN yang salah format ditolak.** Balasannya `PIN harus 4-16 angka, contoh: pin 482913` dan PIN lama tetap dipakai.
- **PIN tidak pernah dikirim ke HP.** Perintah `pin` tampil sebagai `pin ***`, dan `info` lewat Bluetooth tidak menampilkan PIN.
- **Lupa PIN:** colokkan USB, ketik `info` di serial monitor dan lihat baris `BT PIN`, atau langsung buat PIN baru lewat USB.
- **PIN tetap tersimpan setelah update firmware.** Hanya `bash upload.sh --erase` yang mengembalikannya ke `123456`.
- PIN di sini adalah PIN pairing Bluetooth. Pin kabel (GPIO) relay dan sensor tetap D2 dan D15 (lihat [Wiring](#wiring)). Mengubahnya perlu firmware yang di-build ulang oleh developer.

### 5. Tes gate dan perintah `lewat`

Tes ini mengecek relay, sensor, dan server tanpa perlu pengunjung. Ketik perintah di serial monitor atau kirim
lewat aplikasi terminal Bluetooth, lalu Enter. Jika perintah dikirim lewat Bluetooth, log diawali baris
`BLUETOOTH: <perintah>`.

**Sintaks `lewat`:**

```
lewat
```

- **Tanpa angka.** Satu kali `lewat` = 1 orang lewat. Untuk 3 orang, kirim `lewat` 3 kali. `lewat 3` tetap dihitung 1.
- Hasilnya sama seperti 1 orang melewati sensor, tetapi **tanpa foto** (tidak ada capture).
- **Hanya dihitung saat gate buka.** Saat gate tutup, balasannya `Gate tutup, tidak dihitung`.
- **Ditolak selama sensor terhalang**, dengan balasan `Sensor sedang terhalang (ada orang), tidak dihitung`.
  Ini mencegah orang yang sedang berdiri di sensor terhitung dua kali.

**Tes 1: relay.** Ketik `1`. Relay harus berbunyi klik dan LED biru di board menyala.

```
INPUT QTY: 1
GATE BUKA (lewat 0/1)
```

**Tes 2: hitung tanpa sensor.** Lanjutan tes 1, ketik `lewat`. Relay klik lagi dan LED biru mati.

```
SIMULASI LEWAT
Lewat 1/1
GATE TUTUP
```

Untuk 2 orang: ketik `2`, lalu `lewat` dua kali. Gate baru tutup setelah `Lewat 2/2`.

**Tes 3: sensor.** Ketik `1`, lalu halangi sensor dengan tangan dan lepaskan.

```
INPUT QTY: 1
GATE BUKA (lewat 0/1)
Sensor: TERHALANG
Sensor: NORMAL
Lewat 1/1
GATE TUTUP
```

Jika sensor belum terpasang, ganti dengan kabel jumper: tempelkan **D15 ke GND** sebentar (= terhalang), lalu lepas
(= normal). Jika tidak muncul `Sensor: TERHALANG`, cek wiring PC817 (lihat [Sensor orang dengan PC817](#sensor-orang-dengan-pc817)).

**Tes 4: server.** Ketik `scan <kode tiket>`, misalnya `scan 4829175036`.

```
QR: 4829175036
GET http://gate-backup.niagait.com/api/v1/scan-qr?qr-code=4829175036
HTTP 200: {"status":true,"msg":"Tiket valid, silakan masuk.","jum_tiket":"1"}
GATE BUKA (lewat 0/1)
```

Lalu lewati sensor. Saat sensor terhalang harus muncul `CAPTURE 4829175036: HTTP 202` (foto diminta).
Jika tidak ada sensor, ketik `lewat` untuk menutup gate (tanpa foto).

> **Tiket yang dipakai untuk tes menjadi tervalidasi** dan tidak bisa dipakai masuk lagi (`HTTP 409`).
> Pakai tiket khusus tes.

**Tes 5: QR reader.** Scan tiket di reader. Log harus diawali `QR: <kode tiket>`, lalu sama seperti tes 4.
Jika tidak ada log sama sekali saat scan, cek kabel D0 (hijau) ke D21 dan D1 (putih) ke D22.

**Gate tertahan buka setelah tes:** ketik `info` untuk melihat sisa hitungan (`Gate    : BUKA (lewat 0/1)`), lalu
kirim `lewat` sampai muncul `GATE TUTUP`, atau `restart`.

### 6. Pilihan server

| Domain | API key | Capture foto |
|---|---|---|
| Server pusat, `http://gate-backup.niagait.com` | wajib | Server pusat meneruskan ke BackEnd Gate cabang. **URL BackEnd Gate** cabang harus diisi di menu Cabang dan bisa dihubungi dari server pusat. |
| BackEnd Gate cabang, `http://<ip>:3000` | tidak perlu | langsung diambil BackEnd Gate |

Jika capture gagal, gate tetap buka dan tutup normal, hanya fotonya yang tidak ada.

### 7. Contoh log saat dipakai

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
| `WiFi belum di-setting` | ESP baru, atau setelah `upload.sh --erase` | kirim setting lewat Bluetooth |
| `WiFi putus, tiket tidak bisa dicek` | WiFi terputus atau belum di-setting | ESP mencoba konek ulang tiap 10 detik |
| `CAPTURE ...: HTTP 503` | URL BackEnd Gate cabang belum diisi di server pusat | isi di menu Cabang |
| `CAPTURE ...: HTTP 502` | BackEnd Gate tidak bisa dihubungi dari server pusat | cek BackEnd Gate menyala dan URL-nya benar |
| `CAPTURE ...: HTTP 404` | tiket belum masuk ke BackEnd Gate | cek sinkron transaksi ke BackEnd Gate |
| `Wiegand N bit: format tidak dikenal` | format output reader tidak dikenali | set reader ke Wiegand 26/34 atau mode teks |
| Tidak ada log `Sensor:` saat dilalui, atau terbalik | wiring sensor / PC817, atau logika sensor terbalik | cek resistor 1 kΩ di kaki 1 PC817 dan pull-up 10 kΩ. Logika terbalik perlu build ulang. |
| HP tidak diminta PIN atau gagal tersambung | data pairing lama masih tersimpan di HP | lupakan perangkat di HP, pairing ulang |
| `BLUETOOTH: gagal start` | stack Bluetooth gagal menyala | `restart`. Gate tetap berjalan tanpa Bluetooth. |
| Gate tidak menutup | jumlah yang lewat belum sama dengan jumlah tiket | tunggu sisa pengunjung, atau `restart` |
