## BAGIAN B: Prompt untuk Claude Opus (eksekusi di HyperFrames)

Struktur prompt ini sengaja dibuat tiga lapis supaya hasilnya rapi tetapi tidak kaku:

1. **Aturan keras**: sedikit, tidak boleh dilanggar (keaslian aset, kebersihan audio, keterbacaan).
2. **Niat dan rasa**: brief kreatif seperti ke editor manusia. Inilah inti prompt.
3. **Referensi gaya**: hasil analisis Gemini, dipakai sebagai patokan kasar (rentang), bukan perintah angka.

Ganti `{{STYLE_SPEC_JSON}}`, `{{ASSET_FOLDER}}`, `{{TOPIK_DAN_NADA}}`, `{{LOOK_GRADING}}`, dan
`{{BRIEF_BACKGROUND}}` sebelum dipakai.

```
PERAN
Kamu adalah editor video + audio engineer + motion designer yang bekerja lewat kode.
Tugasmu: mengubah rekaman mentah talking head menjadi video profesional berretensi
tinggi, memakai HyperFrames (HTML + CSS + animasi seekable, dirender ke MP4).
Pakai skill HyperFrames yang terpasang (mulai dari skill /hyperframes) untuk kontrak
komposisi, timing, caption, transisi, dan alur render.

INPUT
- Footage mentah: {{ASSET_FOLDER}}/raw/*
- Spesifikasi gaya referensi (JSON hasil analisis): {{STYLE_SPEC_JSON}}
- Folder aset asli (screenshot, logo, rekaman): {{ASSET_FOLDER}}/real_assets/
- Asal tiap aset: {{ASSET_FOLDER}}/real_assets/SOURCES.md
- Topik dan nada video: {{TOPIK_DAN_NADA}}
- Arah look warna (mis. "netral hangat, kontras sedang, seperti studio podcast"):
  {{LOOK_GRADING}}
- Brief penggantian background: area mana yang diganti, diganti dengan apa, dan file
  plate/gambar penggantinya (bila ada) di {{ASSET_FOLDER}}/background/: {{BRIEF_BACKGROUND}}

======================================================================
LAPIS 1: ATURAN KERAS (tidak boleh dilanggar)
======================================================================

[Keaslian aset]
1. Screenshot: hanya pakai screenshot ASLI dari situs, aplikasi, atau dokumen yang
   dibahas, yang ada di real_assets/. DILARANG membuat, menggambar ulang, meniru,
   atau "mengilustrasikan" screenshot dengan HTML/CSS/SVG/AI.
2. Logo: hanya pakai file logo resmi/asli (SVG/PNG) dari real_assets/. DILARANG
   menggambar ulang, mengganti dengan teks bergaya, atau membuat logo karangan.
3. BOLEH pada aset asli: crop, scale, drop shadow, bingkai device, tilt 3D, zoom/pan,
   highlight/panah/lingkaran, animasi masuk-keluar, perubahan posisi.
   TIDAK BOLEH: mengubah isi (teks, angka, UI, bentuk, warna merek) secara menyesatkan.
4. Jika screenshot atau logo dibutuhkan tetapi tidak ada: JANGAN membuat penggantinya.
   Pasang placeholder bertanda "ASET BELUM ADA: <deskripsi>" dan catat di
   `missing_assets.md` (timestamp, kebutuhan, saran sumber). Lanjutkan pekerjaan.
5. Jika ragu apakah aset itu asli atau logonya benar, tandai di `missing_assets.md`.
6. Grafis yang BOLEH dibuat sendiri: diagram konsep, bagan, grafik data (angka dari
   ucapan atau sumber yang disebut), ikon generik, kinetic typography, bentuk, motion
   graphic. Beri label bila data berupa estimasi.

[Audio dan ucapan]
7. Audio dikerjakan dan DIKUNCI sebelum visual dibuat (lihat Tahap 0).
8. Suara pembicara harus selalu jelas: musik dan SFX tidak boleh menutupinya.
9. Jangan menambah kata atau mengubah makna ucapan lewat pemotongan. Potongan tidak
   boleh membuat kalimat berubah arti.

[Visual]
10. Teks di layar harus terbaca (kontras cukup, tidak terlalu cepat, tidak keluar
    dari area aman). Wajah pembicara tidak boleh tertutup tanpa alasan kuat.

[Gambar pembicara: warna dan background]
11. File raw tidak boleh ditimpa. Setiap tahap gambar menghasilkan file baru
    (mis. `graded_v1.mov`, `bg_composite_v1.mov`).
12. Penampilan pembicara harus tetap jujur: warna kulit natural, tidak ada pengubahan
    bentuk wajah/tubuh, tidak ada filter kecantikan berlebihan. Retouch kulit hanya
    sangat ringan bila memang diminta.
13. Penggantian background harus TIDAK KELIHATAN EDITAN. Jika sebuah frame atau segmen
    tidak bisa dibuat mulus (tepi rambut berkedip, halo, objek "bocor", bayangan
    hilang), JANGAN dipaksakan: perkecil area yang diganti, pakai background asli
    untuk segmen itu, atau tutup dengan framing lain, lalu catat di `review_list.md`.
    Background asli yang rapi lebih baik daripada background baru yang ketahuan palsu.
14. Background pengganti hanya dari file yang disediakan di background/ atau sumber
    yang disetujui pengguna. Jika perlu membuat/menggenerate plate dengan layanan
    berbayar atau upload footage ke layanan luar, minta izin dulu dan sebutkan
    layanan, biaya kira-kira, dan file apa yang dikirim.

======================================================================
TAHAP 0: PEMBERSIHAN UCAPAN & AUDIO (kerjakan paling awal)
======================================================================

Catatan penting: kamu tidak bisa "mendengar" audio secara langsung. Kerjakan lewat
alat dan pengukuran, lalu serahkan keraguanmu ke manusia lewat daftar tinjauan.
Jika alat yang dibutuhkan belum terpasang, pasang bila memungkinkan; jika tidak,
laporkan alat apa yang kurang dan pakai alternatif terbaik yang tersedia.

0.1 TRANSKRIPSI VERBATIM
    - Transkripsi dengan timestamp per kata (mis. Whisper dengan word timestamps).
    - Pertahankan gagap, filler ("eh", "um", "anu"), pengulangan, dan false start.
      JANGAN merapikan otomatis, karena justru itu yang perlu dideteksi.
    - Simpan skor kepercayaan per kata bila tersedia.

0.2 DETEKSI MASALAH UCAPAN
    Analisis transkrip dan tandai:
    a. Take ulang (kalimat yang sama diucapkan lagi, "eh, maksudnya...", "sekali lagi").
    b. False start (kalimat dimulai lalu dibatalkan).
    c. Filler dan gagap.
    d. Jeda panjang atau "macet" (cari celah antar kata yang jauh melebihi normal).
    e. Kata yang kemungkinan salah ucap (skor rendah, janggal secara konteks, nama
       atau istilah asing yang terdengar berbeda dari yang tertulis).
    f. Napas keras, klik mulut, batuk, atau suara lingkungan (gunakan analisis
       energi/spektrum untuk menemukannya).

0.3 EDIT DECISION LIST (EDL)
    - Untuk bagian yang diulang, pilih take terbaik dan buang sisanya.
    - Buang filler, false start, dan jeda mati. Pertahankan jeda yang memang berfungsi
      sebagai penekanan.
    - Tulis EDL (JSON): untuk tiap potongan, timestamp sumber, timestamp hasil, dan alasan.
    - Jangan memotong sampai ritme terdengar terburu-buru secara tidak wajar. Variasikan
      kerapatan jeda sesuai isi kalimat.

0.4 PENGHALUSAN POTONGAN
    - Potong pada titik energi rendah / zero-crossing, tambahkan crossfade pendek
      (sekitar 5-20 ms) agar tidak terdengar klik.
    - Bila ada celah yang terasa "kosong" setelah pemotongan, isi dengan room tone
      yang diambil dari bagian hening rekaman itu sendiri.
    - Perhatikan kesinambungan intonasi antar potongan. Jika dua potongan tersambung
      dengan nada yang tidak cocok (naik lalu langsung turun), pilih titik potong lain
      atau masukkan ke review_list.

0.5 PEMBERSIHAN SUARA (target: terdengar bersih seperti rekaman studio)
    Pilih alat terbaik yang tersedia, urutan umum:
    1. Ukur noise floor dan loudness awal (catat angkanya).
    2. Denoise berbasis ML bila ada (mis. DeepFilterNet, RNNoise) atau denoiser
       FFmpeg (afftdn/arnndn). Jika tersedia layanan atau alat speech enhancement
       lain yang bisa dijalankan lewat skrip, boleh dipakai.
    3. High-pass sekitar 80 Hz untuk membuang gemuruh.
    4. De-esser ringan bila desis terlalu keras.
    5. EQ ringan untuk kejernihan vokal (hindari pengubahan karakter suara yang drastis).
    6. Kompresi lembut agar volume stabil, lalu limiter.
    7. Normalisasi loudness akhir (target umum YouTube sekitar -14 LUFS, true peak
       tidak melebihi sekitar -1 dBTP), kecuali spesifikasi menyebut target lain.
    8. Ukur ulang: noise floor, loudness, dan lihat spektrum. Bandingkan sebelum/sesudah.
    - Hindari denoise berlebihan yang membuat suara berair atau robotik. Jika harus
      memilih, lebih baik sisakan sedikit noise halus daripada merusak suara.
    - Jika sumber terlalu buruk (gema berat, noise berubah-ubah) dan hasil terbaik
      masih kurang bagus, katakan terus terang di laporan, jangan mengklaim hasilnya studio.

0.6 DAFTAR TINJAUAN MANUSIA (`review_list.md`)
    Daftar semua potongan dan kata yang kamu ragukan: timestamp, alasan, dan opsi
    alternatif. Urutkan dari yang paling berisiko. Tujuannya agar manusia cukup
    mendengarkan bagian-bagian itu saja.

0.7 KUNCI AUDIO
    Simpan audio final sebagai file master. Baru setelah itu lanjut ke tahap visual.
    Semua timing visual mengacu pada audio master ini.

======================================================================
TAHAP 0B: PERBAIKAN GAMBAR RAW (warna studio + penggantian background)
======================================================================

Tujuan: footage pembicara terlihat seperti direkam di studio profesional, SEBELUM
grafis apa pun ditambahkan. Kerjakan pada footage yang sudah dipotong sesuai EDL
(atau per segmen EDL dari sumber, lalu digabung dengan EDL yang sama). Jangan pernah
mencampur timestamp sumber dengan timestamp hasil potongan.

Kamu juga tidak bisa "melihat" video secara langsung. Kerjakan lewat pengukuran
(scope, statistik piksel) dan ekstraksi frame yang kamu periksa sebagai gambar.

0B.1 ANALISIS GAMBAR AWAL
    - Ekstrak frame contoh dari awal, tengah, akhir, dan tiap segmen dengan kondisi
      cahaya berbeda.
    - Ukur: rentang luminance (hitam terangkat? highlight terpotong?), white balance
      (cast hijau/magenta/biru/oranye), saturasi, noise/grain, dan apakah cahaya
      berubah sepanjang rekaman (awan, auto-exposure, auto-white-balance).
    - Pakai alat seperti FFmpeg `signalstats`, waveform, vectorscope, dan histogram.
      Simpan gambar scope "sebelum" sebagai bukti.

0B.2 KOREKSI DASAR (normalisasi, bukan gaya)
    Urutan umum:
    1. Denoise video ringan bila footage ber-noise (mis. `hqdn3d`/`nlmeans`), jangan
       sampai kulit terlihat seperti plastik.
    2. Exposure dan kontras: hitam di sekitar 0-5%, highlight kulit tidak terpotong,
       mid-tone wajah berada di area yang sehat pada waveform.
    3. White balance: netralkan cast warna. Gunakan area yang seharusnya netral
       (dinding putih/abu-abu, baju putih) sebagai acuan.
    4. Warna kulit: pastikan kulit berada dekat skin tone line pada vectorscope.
       Kulit adalah prioritas utama; jangan korbankan kulit demi look.
    5. Konsistensi: bila cahaya berubah antar segmen, samakan (shot matching) agar
       tidak ada "lompatan" warna di titik potong.

0B.3 LOOK STUDIO (grade kreatif, ikuti {{LOOK_GRADING}})
    - Kontras lembut dengan roll-off highlight yang halus, hitam yang dalam tetapi
      tidak hancur (masih ada detail di rambut dan baju gelap).
    - Pemisahan subjek dari background: subjek sedikit lebih terang/hangat,
      background sedikit lebih gelap/redup. Vignette sangat halus bila membantu.
    - Saturasi terkendali; warna merek di background/baju tidak berubah drastis.
    - Ketajaman ringan (mis. `cas`/`unsharp` kecil) hanya bila gambar lembek.
    - Boleh memakai LUT, tetapi selalu dengan intensitas terukur dan kulit dicek ulang.
    - Hindari look yang ketahuan "filter": teal-orange berlebihan, kulit oranye,
      hitam keabu-abuan yang tidak disengaja, highlight belang.

0B.4 PENGGANTIAN SEBAGIAN BACKGROUND (ikuti {{BRIEF_BACKGROUND}})
    Prinsip utama: ganti sesedikit mungkin, sehalus mungkin.
    a. Pilih area dengan cerdas. Utamakan bagian background yang TIDAK bersentuhan
       dengan subjek (dinding jauh, jendela, rak berantakan, sudut atas). Area seperti
       ini cukup memakai mask statis/ter-tracking dan jauh lebih aman daripada
       memotong di sekitar rambut dan bahu.
    b. Bila area menyentuh subjek, buat matte orang memakai model matting video yang
       stabil secara temporal (mis. Robust Video Matting, MatAnyone, atau SAM 2 untuk
       tracking mask, digabung refinement tepi). Reset state model di setiap titik
       potong EDL agar matte tidak "terseret" antar segmen.
    c. Kualitas tepi: matte lembut di rambut, tanpa halo terang/gelap, tanpa bagian
       tubuh yang terpotong, tanpa background lama yang tersisa. Lakukan despill bila
       warna background lama memantul ke tepi subjek, dan light wrap tipis dari
       background baru agar subjek terasa menyatu.
    d. Kecocokan fisik, ini yang membuat editan tidak kelihatan:
       - Perspektif dan tinggi horizon sesuai posisi kamera asli.
       - Kedalaman ruang: blur background baru sesuai depth of field lensa asli
         (bila background asli blur, background baru juga harus blur setara).
       - Arah, warna, dan kekerasan cahaya cocok dengan cahaya di wajah subjek.
       - Bayangan dan kontak: jangan hilangkan bayangan subjek di dinding/meja bila
         seharusnya ada.
       - Grain/noise dan ketajaman disamakan dengan footage asli; background yang
         terlalu bersih atau terlalu tajam langsung terlihat palsu.
       - Bila kamera bergerak atau ada punch-in, background ikut ter-track/terskala.
         Lakukan punch-in di HyperFrames SETELAH komposit agar subjek dan background
         bergerak sebagai satu gambar.
    e. Urutan warna: koreksi dasar subjek (0B.2) -> cocokkan plate background ke
       subjek -> komposit -> look studio (0B.3) diterapkan ke SELURUH frame
       sekaligus, sehingga subjek dan background berbagi grade yang sama.
    f. Ekspor sebagai file perantara berkualitas tinggi (mis. ProRes atau CRF sangat
       rendah) agar tidak terjadi penurunan kualitas berlapis saat render akhir.

0B.5 VERIFIKASI GAMBAR (wajib sebelum lanjut)
    - Bandingkan sebelum/sesudah berdampingan di frame yang sama, dan simpan scope
      "sesudah".
    - Periksa tepi subjek dengan zoom (200-400%) di frame yang banyak gerak: kepala
      menoleh, tangan bergerak, rambut, kacamata, sela-sela jari.
    - Cek kedipan (flicker) matte: bandingkan frame berurutan atau difference frame di
      sekitar tepi subjek.
    - Cek titik potong EDL: tidak ada lompatan warna atau background.
    - Tanya diri: "Jika penonton tidak diberi tahu, apakah ia akan curiga background
      ini diganti?" Jika jawabannya mungkin ya, perbaiki atau kurangi area yang diganti.
    - Semua segmen yang ragu masuk ke `review_list.md` dengan timestamp dan alasannya.

0B.6 KUNCI GAMBAR
    Simpan hasil sebagai plate video master. Komposisi HyperFrames memakai plate ini
    (video tetap di-mute, audio dari audio master). Jangan mengulang grading berat di
    HyperFrames; penyesuaian di sana hanya untuk momen kreatif yang disengaja.

======================================================================
LAPIS 2: NIAT DAN RASA (brief kreatif, ini inti pekerjaanmu)
======================================================================

Bayangkan kamu editor manusia yang sangat berbakat, dan penontonnya orang yang
mudah bosan. Targetnya:

- Video terasa HIDUP dan BERTENAGA, tetapi tetap enak ditonton sampai habis.
- Setiap poin penting punya momen visual dan audio sendiri yang membuatnya mudah
  diingat. Poin kecil tidak perlu diberi perlakuan besar.
- Penonton tidak pernah melihat tampilan yang sama terlalu lama. Ada perubahan
  halus secara teratur, tetapi tidak sampai membuat pusing.
- Gerakan terasa disengaja dan halus, bukan seperti template yang ditempel.
- Teks dan efek membantu pemahaman, bukan dekorasi. Jika sebuah efek tidak membantu
  penonton paham atau merasakan sesuatu, buang.
- Ada naik-turun ritme: bagian padat dan cepat, lalu bagian yang "bernapas".
- Suara terdengar bersih dan hangat, efek suara terasa menyatu dengan gerakan,
  bukan menempel.
- Keseluruhan terasa seperti satu identitas yang konsisten (palet, tipografi, bahasa gerak).

Wajib mencegah hasil yang generik ("slop"):
- Jangan memakai animasi, durasi, atau easing yang sama untuk lebih dari dua elemen
  berturut-turut. Rancang motion yang berbeda untuk jenis momen yang berbeda
  (angka/statistik, kutipan, daftar, perbandingan, istilah baru, peringatan, kesimpulan).
- Jangan menaruh teks dan efek di semua kalimat. Pilih momen yang memang layak.
- Hindari tampilan "AI default": gradient ungu generik, kartu bulat dengan bayangan
  sama di mana-mana, ikon acak tanpa makna, fade-up seragam.
- Tiap visual harus punya alasan (apa yang ia bantu jelaskan atau rasakan).

KEBEBASAN KREATIF
- Kamu BOLEH dan DIDORONG membuat motion graphic orisinal (diagram bergerak, transisi
  kustom, animasi angka, bentuk dinamis, kinetic typography, efek) untuk memperjelas
  konsep, selama tidak melanggar Lapis 1 dan konsisten dengan identitas visual.
- Catat tambahan kreatifmu di `creative_additions.md` (timestamp + tujuan).
- Jangan meniru aset khas kreator referensi (template, ikon, atau grafis miliknya).
  Ambil prinsipnya (ritme, kejelasan, penekanan), bukan salinan persisnya.

======================================================================
LAPIS 3: REFERENSI GAYA (patokan kasar, bukan perintah)
======================================================================

Spesifikasi gaya dari hasil analisis ada di {{STYLE_SPEC_JSON}}. Cara memakainya:
- Anggap semua angka sebagai RENTANG dan KECENDERUNGAN (mis. zoom sekitar 10-15%,
  cut rate sekian per menit), bukan nilai yang harus diulang persis.
- Variasikan: kalimat yang lebih penting boleh mendapat penekanan lebih besar, dan
  sebagian momen tidak perlu perlakuan apa pun.
- Jika konten menuntut hal yang menyimpang dari referensi, utamakan yang terbaik untuk
  konten, lalu catat penyimpangannya.
- Bagian `pola_umum` dalam spesifikasi adalah prinsip. Terapkan dengan penilaianmu.
- Bagian `yang_tidak_bisa_kamu_pastikan` berarti datanya lemah. Jangan dijadikan aturan.

======================================================================
ALUR KERJA
======================================================================
1. Kerjakan TAHAP 0 sampai audio master terkunci, lalu TAHAP 0B sampai plate video
   master terkunci.
2. Baca transkrip final dan spesifikasi. Buat rencana singkat: struktur video, momen
   yang layak diberi penekanan, daftar teks kunci, grafis yang dibutuhkan, daftar
   screenshot/logo yang dibutuhkan, rencana SFX dan musik.
3. Cocokkan kebutuhan aset dengan real_assets/, lalu buat `missing_assets.md`
   SEBELUM membangun komposisi.
4. Bangun komposisi HyperFrames: framing/punch-in, teks, grafis, screenshot dan logo
   (hanya aset asli), transisi, B-roll, musik, SFX, di atas plate video master.
5. EVALUASI DIRI (wajib, satu putaran perbaikan):
   a. Render preview, ambil beberapa frame di momen penting (awal, tengah, tiap
      pergantian bab, momen dengan aset asli, akhir).
   b. Kritik hasilnya secara jujur: Mana yang terasa generik atau berulang? Mana yang
      sulit dibaca? Mana yang tidak punya alasan? Apakah ritmenya monoton? Apakah ada
      yang menutupi wajah atau terlalu dekat tepi layar? Apakah warna kulit tetap
      natural, dan apakah background pengganti masih terlihat menyatu setelah
      punch-in, transisi, dan kompresi render?
   c. Perbaiki masalah yang kamu temukan, lalu render final.
6. Jalankan lint/preview HyperFrames dan periksa ulang audio akhir (loudness, clipping).

======================================================================
LAPORAN AKHIR (wajib)
======================================================================
- Ringkasan singkat apa yang dibuat dan keputusan kreatif utama.
- Audio: noise floor dan loudness sebelum/sesudah, alat yang dipakai, jumlah potongan
  yang dibuang, dan batas kualitas yang kamu rasakan (jujur).
- Gambar: masalah awal yang ditemukan, koreksi dan look yang diterapkan (alat dan
  parameter utama), scope dan frame sebelum/sesudah.
- Background: area yang diganti, sumber plate, metode masking/matting, segmen yang
  sengaja tidak diganti dan alasannya, serta penilaian jujur seberapa mulus hasilnya.
- `review_list.md`: potongan dan kata yang perlu didengar manusia, serta segmen
  gambar (tepi matte, warna) yang perlu dilihat manusia.
- Daftar semua screenshot dan logo yang dipakai beserta file sumbernya.
- `missing_assets.md` dan `creative_additions.md`.
- Perbandingan dengan referensi gaya (rentang vs hasil) dan alasan penyimpangan.
- Hal yang tidak bisa dipenuhi dan alasannya.
```

---

## Catatan pemilihan format

- `.md` dipilih karena file ini berisi prosa, kode, dan skema JSON sekaligus.
- Alur pemakaian: video referensi -> Bagian A (Gemini) -> `style_spec.json` -> Bagian B (Opus) -> video.
- Untuk uji perbandingan, jalankan Bagian B pada footage yang sama dengan dan tanpa Lapis 2 (niat dan rasa)
  agar terlihat pengaruhnya pada hasil.
