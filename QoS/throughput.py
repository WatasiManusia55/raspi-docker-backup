import time
import requests
import csv
import matplotlib.pyplot as plt
import os  # Diperlukan untuk os.urandom
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging


# ==============================================================================
# KONFIGURASI PENGUJIAN
# ==============================================================================


# Ganti dengan domain kamu yang terhubung melalui Cloudflare Tunnel
UPLOAD_URL = "https://pbl-tmj5a.siling-ai.my.id/throughput_upload"
DOWNLOAD_URL = "https://pbl-tmj5a.siling-ai.my.id/throughput_download"


# Ukuran data uji: 5, 10, 15, ... , 50 MB
SIZES_MB: List[int] = list(range(5, 51, 5))
TIMEOUT_SECONDS: int = 300  # Timeout 5 menit


CSV_FILE: str = "throughput_results_random.csv" # Mengganti nama file CSV
PLOT_FILE: str = "throughput_graph_random.png" # Mengganti nama file Plot


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Data class untuk menyimpan hasil pengujian."""
    size_mb: int
    throughput_upload_kbps: float
    throughput_download_kbps: float
    time_upload_s: float
    time_download_s: float
    time_total_s: float  # time_upload_s + time_download_s


# ==============================================================================
# FUNGSI UTAMA PENGUJIAN
# ==============================================================================


def test_upload(session: requests.Session, size_mb: int) -> Optional[Tuple[float, float]]:
    """
    Menguji throughput upload ke server menggunakan DATA ACAK.
    Mengembalikan (kecepatan dalam kbps, waktu dalam detik). Return None jika gagal.
    """
    size_bytes = size_mb * 1024 * 1024
    # MENGGUNAKAN os.urandom UNTUK DATA UJI YANG SULIT DIKOMPRESI
    data = os.urandom(size_bytes)


    logger.info(f"[UPLOAD] Memulai uji {size_mb} MB (Data Acak)...")


    t_start = time.perf_counter()
    try:
        resp = session.post(
            UPLOAD_URL,
            data=data,
            timeout=TIMEOUT_SECONDS,
            headers={'Content-Type': 'application/octet-stream'}
        )
        resp.raise_for_status()  
        t_end = time.perf_counter()
    except requests.exceptions.RequestException as e:
        logger.error(f"[UPLOAD {size_mb}MB] GAGAL - Koneksi/Timeout: {e}")
        return None


    waktu_detik = t_end - t_start
    # Hitung jumlah data terkirim (dalam kilobit)
    data_kilobit = (size_bytes * 8) / 1000.0


    # Throughput (kbps) = jumlah data terkirim (kilobit) / waktu (detik)
    throughput_kbps = data_kilobit / waktu_detik


    logger.info(
        f"[UPLOAD {size_mb}MB] Selesai - "
        f"Waktu: {waktu_detik:.2f}s, "
        f"Kecepatan: {throughput_kbps:.2f} kbps"
    )


    return throughput_kbps, waktu_detik


def test_download(session: requests.Session, size_mb: int) -> Optional[Tuple[float, float]]:
    """
    Menguji throughput download dari server.
    Dalam skenario download, server yang menentukan data, namun klien
    mengukur data yang diterima dan waktu tempuhnya.
    Mengembalikan (kecepatan dalam kbps, waktu dalam detik). Return None jika gagal.
    """
    params = {"size_mb": size_mb}


    logger.info(f"[DOWNLOAD] Memulai uji {size_mb} MB...")


    t_start = time.perf_counter()
    try:
        resp = session.get(
            DOWNLOAD_URL,
            params=params,
            stream=True,
            timeout=TIMEOUT_SECONDS
        )
        resp.raise_for_status()


        total_bytes = 0
        chunk_size = 8192
        
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if not chunk:
                break
            total_bytes += len(chunk)
        t_end = time.perf_counter()


    except requests.exceptions.RequestException as e:
        logger.error(f"[DOWNLOAD {size_mb}MB] GAGAL - Koneksi/Timeout: {e}")
        return None


    waktu_detik = t_end - t_start
    # Hitung jumlah data diterima (dalam kilobit)
    data_kilobit = (total_bytes * 8) / 1000.0


    # Throughput (kbps) = jumlah data terkirim (kilobit) / waktu (detik)
    throughput_kbps = data_kilobit / waktu_detik


    logger.info(
        f"[DOWNLOAD {size_mb}MB] Selesai - "
        f"Waktu: {waktu_detik:.2f}s, "
        f"Data: {data_kilobit:.2f} kbit, "
        f"Kecepatan: {throughput_kbps:.2f} kbps"
    )


    return throughput_kbps, waktu_detik


# ==============================================================================
# PELAPORAN DATA (Tidak berubah, format CSV tetap kbps)
# ==============================================================================


def save_to_csv(results: List[TestResult]) -> bool:
    """Menyimpan hasil pengujian ke file CSV."""
    fieldnames = [
        "size_mb",
        "throughput_upload_kbps",
        "throughput_download_kbps",
        "time_upload_s",
        "time_download_s",
        "time_total_s"
    ]
    try:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow(result.__dict__)
        
        logger.info(f"✅ Hasil lengkap disimpan ke: {CSV_FILE}")
        return True
    except IOError as e:
        logger.error(f"❌ Gagal menyimpan CSV: {e}")
        return False


def plot_results(results: List[TestResult]) -> bool:
    """Membuat dan menyimpan grafik throughput."""
    try:
        x = [r.size_mb for r in results]
        # Konversi kbps ke Mbps untuk plot agar skala lebih mudah dibaca
        y_up = [r.throughput_upload_kbps / 1000.0 for r in results] 
        y_down = [r.throughput_download_kbps / 1000.0 for r in results]


        # Filter valid values for average calculation
        valid_up = [v for v in y_up if v > 0]
        valid_down = [v for v in y_down if v > 0]
       
        avg_up = sum(valid_up) / len(valid_up) if valid_up else 0.0
        avg_down = sum(valid_down) / len(valid_down) if valid_down else 0.0


        plt.style.use('seaborn-v0_8-darkgrid')
        plt.figure(figsize=(12, 7))
        
        # Plot lines
        plt.plot(x, y_up, marker="o", linestyle='-', color='#1f77b4', linewidth=2, label="Upload Throughput")
        plt.plot(x, y_down, marker="s", linestyle='--', color='#ff7f0e', linewidth=2, label="Download Throughput")
        
        # Add average lines (optional but helpful)
        if avg_up > 0:
            plt.axhline(y=avg_up, color='#1f77b4', linestyle=':', alpha=0.7, linewidth=1.5)
            plt.text(x[-1] + 0.5, avg_up, f' Avg UP: {avg_up:.2f} Mbps', color='#1f77b4', va='center')
        
        if avg_down > 0:
            plt.axhline(y=avg_down, color='#ff7f0e', linestyle=':', alpha=0.7, linewidth=1.5)
            plt.text(x[-1] + 0.5, avg_down, f' Avg DOWN: {avg_down:.2f} Mbps', color='#ff7f0e', va='center')
        
        plt.xlabel("Ukuran Data Uji (MB)", fontsize=12)
        plt.ylabel("Throughput (Mbps)", fontsize=12)
        plt.title(
            "Perbandingan Throughput Upload & Download (Menggunakan Data Acak)",
            fontsize=14,
            fontweight='bold'
        )
        plt.legend(fontsize=10, loc='upper right')
        plt.xticks(x)  
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.savefig(PLOT_FILE, dpi=300, bbox_inches='tight')


        logger.info(f"📊 Grafik throughput disimpan ke: {PLOT_FILE}")
        return True
    except Exception as e:
        logger.error(f"❌ Gagal membuat plot: {e}")
        return False


def print_statistics(results: List[TestResult]) -> None:
    """Menampilkan statistik hasil pengujian."""
    up_values_mbps = [r.throughput_upload_kbps / 1000.0 for r in results if r.throughput_upload_kbps > 0]
    down_values_mbps = [r.throughput_download_kbps / 1000.0 for r in results if r.throughput_download_kbps > 0]
    
    # Statistik waktu
    up_times = [r.time_upload_s for r in results if r.time_upload_s > 0]
    down_times = [r.time_download_s for r in results if r.time_download_s > 0]


    avg_up_mbps = sum(up_values_mbps) / len(up_values_mbps) if up_values_mbps else 0.0
    avg_down_mbps = sum(down_values_mbps) / len(down_values_mbps) if down_values_mbps else 0.0
    
    if up_values_mbps and down_values_mbps:
        avg_total = (avg_up_mbps + avg_down_mbps) / 2.0
    else:
        avg_total = avg_up_mbps if up_values_mbps else avg_down_mbps


    print("\n" + "="*50)
    print("RINGKASAN HASIL PENGUJIAN THROUGHPUT (DATA ACAK)")
    print("="*50)
    print(f"Total Pengujian      : {len(results)} ukuran data")
    print(f"Upload Berhasil      : {len(up_values_mbps)}/{len(results)}")
    print(f"Download Berhasil    : {len(down_values_mbps)}/{len(results)}")
    print("-"*50)
    print(f"Rata-rata Throughput Upload   : {avg_up_mbps:.2f} Mbps")
    print(f"Rata-rata Throughput Download : {avg_down_mbps:.2f} Mbps")
    print(f"Rata-rata Gabungan            : {avg_total:.2f} Mbps")
    print(f"Rata-rata Waktu Upload      : {sum(up_times) / len(up_times):.2f} s")
    print(f"Rata-rata Waktu Download    : {sum(down_times) / len(down_times):.2f} s")
    print("="*50)
    
    # Analysis
    print("\n📊 ANALISIS:")
    if avg_up_mbps < 1.0 or avg_down_mbps < 1.0:
        print("⚠️  Throughput rendah (< 1 Mbps). Kemungkinan penyebab:")
        print("  1. Limitasi bandwidth Cloudflare Tunnel gratis (~1-2 Mbps)")
        print("  2. Koneksi internet lokal yang lambat")
        print("  3. Lokasi server yang jauh (latensi tinggi)")
        print("  4. Resource server Raspberry Pi terbatas")
        print("💡 Saran: Coba uji dengan koneksi yang lebih cepat atau")
        print("          pertimbangkan upgrade ke Cloudflare paid tier")
    else:
        print("✅ Throughput dalam rentang normal atau baik.")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================


def main():
    """Fungsi utama untuk menjalankan pengujian."""
    print(f"\n🚀 Memulai pengujian throughput...")
    print(f"📤 URL Upload: {UPLOAD_URL}")
    print(f"📥 URL Download: {DOWNLOAD_URL}")
    print(f"📊 Ukuran data yang akan diuji: {SIZES_MB} MB")
    print("-" * 60)
    
    results: List[TestResult] = []
    
    # Create a session for connection pooling
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Throughput-Tester/1.0',
        'Accept': '*/*'
    })


    try:
        for size in SIZES_MB:
            print(f"\n{'='*40}")
            print(f"UJI DATA {size} MB")
            print('='*40)
            
            # Test upload
            up_result = test_upload(session, size)
            if up_result is not None:
                up_kbps, up_time_s = up_result
            else:
                up_kbps = 0.0
                up_time_s = 0.0
                logger.warning(f"Upload {size}MB gagal, dianggap 0 kbps dan {up_time_s:.2f}s")
            
            # Wait between tests
            time.sleep(2)
            
            # Test download
            down_result = test_download(session, size)
            if down_result is not None:
                down_kbps, down_time_s = down_result
            else:
                down_kbps = 0.0
                down_time_s = 0.0
                logger.warning(f"Download {size}MB gagal, dianggap 0 kbps dan {down_time_s:.2f}s")
            
            # Calculate total time and store result
            total_time_s = up_time_s + down_time_s


            results.append(TestResult(
                size_mb=size,
                throughput_upload_kbps=up_kbps,
                throughput_download_kbps=down_kbps,
                time_upload_s=up_time_s,
                time_download_s=down_time_s,
                time_total_s=total_time_s
            ))
            
            # Wait before next size
            time.sleep(3)
        
        # Save and visualize results
        if results:
            save_to_csv(results)
            plot_results(results)
            print_statistics(results)
        else:
            logger.error("❌ Tidak ada hasil yang berhasil dikumpulkan!")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Pengujian dihentikan oleh pengguna")
        if results:
            print("Menyimpan hasil yang sudah terkumpul...")
            save_to_csv(results)
            if len(results) >= 2:
                plot_results(results)
            print_statistics(results)
    except Exception as e:
        logger.error(f"❌ Error tidak terduga: {e}")
    finally:
        session.close()
        print("\n✅ Pengujian selesai!")


if __name__ == "__main__":
    main()

