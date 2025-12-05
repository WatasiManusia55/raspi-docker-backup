import cv2
import time
import os
import json
import numpy as np
import matplotlib.pyplot as plt

# ====================================================
# === KONFIGURASI PATH & PARAMETER ===
# ====================================================
CAM_TEST_INDEX = 1      # Ganti sesuai indeks kamera Anda (0, 1, atau 2)
CAPTURE_ATTEMPTS = 30   # Jumlah percobaan untuk mendapatkan data stabilitas
OUTPUT_DIR = "/home/pi/Documents/AI/latency_test_results"
JSON_FILENAME = "capture_latency_results.json"
GRAPH_FILENAME = "latency_stability_graph.png"
TEMP_FRAME_NAME = "temp_frame_to_delete.jpg" # Nama file sementara untuk I/O test

def measure_capture_latency(index, attempts, output_dir):
    """
    Mengukur waktu yang dibutuhkan untuk membuka, menangkap, dan menyimpan frame, 
    kemudian menyimpan hasilnya ke JSON dan membuat grafik.
    """
    
    # 1. Setup Direktori
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[INFO] Folder output dibuat: {output_dir}")

    json_path = os.path.join(output_dir, JSON_FILENAME)
    graph_path = os.path.join(output_dir, GRAPH_FILENAME)
    
    latency_results = []
    
    print(f"Mencoba membuka kamera pada indeks {index}...")
    
    # 2. Buka Kamera
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)

    if not cap.isOpened():
        print(f"❌ Gagal membuka kamera pada indeks {index}. Periksa koneksi atau indeks.")
        return None

    # Pengaturan Kamera Opsional
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Warm-up (Buang beberapa frame pertama)
    for _ in range(5):
        cap.read()
        
    print(f"✅ Kamera terbuka. Memulai pengujian {attempts} percobaan...")

    # 3. Loop Pengujian Capture
    for i in range(1, attempts + 1):
        start_time = time.time()
        
        # Ambil Frame (Capture)
        ret, frame = cap.read()
        
        if not ret:
            print(f"[WARN] Gagal membaca frame pada percobaan {i}. Mengabaikan iterasi ini.")
            continue
            
        # Simpan Frame ke Disk (Mensimulasikan output file)
        temp_file_path = os.path.join(output_dir, TEMP_FRAME_NAME)
        cv2.imwrite(temp_file_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        # Akhiri Pengukuran Waktu
        end_time = time.time()
        
        # Hitung Latensi dalam Milidetik (ms)
        latency_ms = (end_time - start_time) * 1000
        latency_results.append(latency_ms)
        
        print(f"  Percobaan {i}/{attempts}: {latency_ms:.2f} ms")
        
        # Hapus file sementara setelah setiap percobaan
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    # Tutup Kamera
    cap.release()

    # 4. Analisis dan Penyimpanan Data JSON
    if not latency_results:
        print("Pengujian gagal, tidak ada data latensi yang terkumpul.")
        return None

    latencies = np.array(latency_results)
    
    results = {
        "test_name": "Latensi Proses Capture Kamera (Capture + Write to Disk)",
        "camera_index": index,
        "total_attempts": len(latencies),
        "avg_latency_ms": round(np.mean(latencies), 2),
        "std_dev_ms": round(np.std(latencies), 2),
        "min_latency_ms": round(np.min(latencies), 2),
        "max_latency_ms": round(np.max(latencies), 2),
        "criteria_pass": bool(np.mean(latencies) < 1000), # < 1 detik
        "all_latencies_ms": latencies.tolist()
    }
    
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"\n[SUCCESS] Hasil JSON disimpan ke: {json_path}")
    
    # 5. Membuat Grafik Stabilitas
    
    plt.figure(figsize=(10, 5))
    plt.plot(range(1, len(latencies) + 1), latencies, marker='o', linestyle='-', color='teal', label='Latensi per Iterasi')
    plt.axhline(results['avg_latency_ms'], color='red', linestyle='--', label=f"Rata-rata: {results['avg_latency_ms']:.2f} ms")
    plt.axhline(1000, color='gray', linestyle=':', label='Batas Kriteria (1000 ms)')
    
    plt.title('Stabilitas Latensi Proses Capture Kamera (Capture + I/O)')
    plt.xlabel('Nomor Percobaan (Iterasi)')
    plt.ylabel('Latensi (ms)')
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    plt.savefig(graph_path)
    plt.close() # Tutup figure untuk membebaskan memori
    
    print(f"[SUCCESS] Grafik stabilitas disimpan ke: {graph_path}")

    return results

if __name__ == "__main__":
    try:
        measure_capture_latency(CAM_TEST_INDEX, CAPTURE_ATTEMPTS, OUTPUT_DIR)
    except KeyboardInterrupt:
        print("\nPengujian dibatalkan oleh pengguna.")
    finally:
        # Pembersihan file sementara
        temp_file_path = os.path.join(OUTPUT_DIR, TEMP_FRAME_NAME)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        print("Selesai.")