# Document Similarity Service

Layanan FastAPI untuk menjadwalkan pemeriksaan kemiripan teks PDF. Proses mengunduh PDF, mengekstrak teks, mencari kandidat melalui Google Custom Search, membandingkan potongan teks, lalu menyimpan hasil pekerjaan ke MySQL. Nilai kemiripan adalah hasil algoritma pembandingan, bukan keputusan akademik tentang plagiarisme.

## API dan alur

`POST /check_plagiarism` menerima `file_name`, `book_id`, dan `market_id`. Respons sukses berisi `status: accepted` serta `job_id`. Implementasi memakai FastAPI BackgroundTasks di proses yang sama. Hasil disimpan dalam tabel `plagiarims_checker` (ejaan ini dipertahankan dari source). Status 0 menunggu, 1 selesai, dan 2 gagal. Tidak ada endpoint polling hasil terpisah saat ini.

## Persiapan

Gunakan Python 3.10+, database MySQL kosong, dan kredensial Google Custom Search milik sendiri. Dari root proyek:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r plagiarism_checker/requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python -m uvicorn plagiarism_checker.main:app --host 127.0.0.1 --port 8001
```

Isi `.env` lokal: koneksi `DB_*`, `GOOGLE_API_KEY`, `SEARCH_ENGINE_ID`, dan bila memakai nama file relatif, `PDF_BASE_PATH`. Database harus dibuat terlebih dahulu; startup membuat tabel pekerjaan. Jangan menimpa `.env` yang sudah diisi. Semua nilai contoh adalah konfigurasi lokal kosong, bukan kredensial layanan nyata.

Buka `http://127.0.0.1:8001/docs` setelah startup berhasil. Contoh body sintetis:

```json
{"file_name":"https://example.com/dokumen-latihan.pdf","book_id":1,"market_id":1}
```

URL contoh bukan dokumen uji yang dijanjikan tersedia. Ganti dengan PDF latihan yang boleh diunduh dan diproses. Tanpa Google API yang valid, pencarian akan gagal; tanpa MySQL, startup tidak dapat selesai.

## Berkas utama

`main.py` mendefinisikan API; `db.py` menangani pekerjaan dan skema; `pipeline.py` mengunduh serta mengolah PDF; `search_pipeline.py` mencari dan mengambil halaman; `text_utils.py` menghitung kemiripan.

## Batas dan verifikasi

AST seluruh modul diperiksa tanpa memanggil database atau layanan Google. Integrasi eksternal belum dijalankan untuk ekspor ini. Dependency masih mengikuti requirements sumber yang belum dipin. Belum ada autentikasi, antrean pekerjaan persisten, pembatasan beban, atau kebijakan jaringan untuk unduhan URL pengguna. Jalankan pada localhost dengan dokumen latihan; tambahkan kontrol tersebut sebelum membuka akses publik.

## Asal dan lisensi

Kode berasal dari modul lokal `plagiarism_checker`. Environment asli dan dokumen PDF tidak disertakan. Belum ada file lisensi proyek pada sumber; daftar library berada di `plagiarism_checker/requirements.txt`.
