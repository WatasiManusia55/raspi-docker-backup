import time
import os
import threading
import uuid
import numpy as np
import cv2
import torch
from ultralytics import YOLO
import json

# ====================================================
# === KONSTANTA & SETUP GLOBAL ===
# ====================================================

# Konfigurasi Model & Perangkat
MODEL_PATH = "/home/pi/Documents/AI/best (14).pt"
IMG_SIZE = 768 # Gunakan 768 atau 640/416 untuk performa yang lebih baik
MIN_CONF = 0.6
NMS_IOU = 0.52
ONLY_CLASS = 0
ITERATIONS = 30 # Jumlah iterasi pengujian beruntun

device = "cpu" # Diasumsikan CPU karena di Raspberry Pi
print(f"[INFO] YOLO Device: {device}")

# Variabel Global Kamera
CAM_INDEX = 1
global_frame = None
camera_running = True

# Load Model
try:
    model = YOLO(MODEL_PATH)
    print("[INFO] Model loaded successfully.")
    model.to(device)
except Exception as e:
    print(f"[ERROR] Cannot load model: {e}")
    model = None

# ====================================================
# === FUNGSI BANTU ===
# ====================================================

def get_cpu_temp():
    """Membaca suhu CPU dari Raspberry Pi (file /sys/class/thermal/thermal_zone0/temp)"""
    try:
        # Baca suhu (dalam milikelvin) dan konversi ke Celsius
        temp_file = '/sys/class/thermal/thermal_zone0/temp'
        if os.path.exists(temp_file):
            with open(temp_file, 'r') as f:
                temp_milli = int(f.read().strip())
                return temp_milli / 1000.0
        return None
    except Exception:
        return None

def camera_loop():
    """Loop kamera untuk mengambil frame secepat mungkin."""
    global global_frame, camera_running
    print("[INFO] Starting camera background thread...")
    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)

    if not cap.isOpened():
        print(f"[ERROR] Gagal membuka kamera pada indeks {CAM_INDEX}.")
        camera_running = False
        return

    # Atur parameter kamera
    # ... (Pengaturan set kamera, dihilangkan untuk keringkasan, tapi harus ada) ...

    # Warm-up kamera
    for _ in range(5):
        cap.read()
        time.sleep(0.1)

    print("[INFO] Camera stream started. Ready to capture.")

    while camera_running:
        ret, frame = cap.read()
        if ret:
            global_frame = frame.copy()
        else:
            # Tidak perlu mencetak WARN terlalu sering di loop ini
            pass 
        time.sleep(0.01)

    cap.release()
    print("[INFO] Camera thread stopped.")

def run_yolo_inference(frame):
    """Fungsi inferensi YOLO, menerima numpy array dan mengembalikan latensi."""
    if model is None or frame is None or frame.size == 0:
        return 0, 0.0, 0.0

    start_time = time.time()
    
    # PERHATIAN: Memproses frame (numpy array) secara langsung.
    try:
        results = model.predict(
            source=frame, # <-- MEMPROSES LANGSUNG DARI NUMPY ARRAY
            conf=MIN_CONF,
            imgsz=IMG_SIZE,
            iou=NMS_IOU,
            classes=[ONLY_CLASS],
            device=device,
            verbose=False,
            save=False 
        )
    except Exception as e:
        print(f"[ERROR] Inferensi gagal: {e}")
        return 0, 0.0, 0.0

    latency_ms = (time.time() - start_time) * 1000

    res = results[0]
    det_count = len(res.boxes)
    # Konversi ke float Python standar untuk JSON
    avg_conf = float(np.mean(res.boxes.conf.detach().cpu().numpy())) if det_count > 0 else 0.0
    
    return det_count, avg_conf, latency_ms

# ====================================================
# === FUNGSI UTAMA PENGUJIAN ===
# ====================================================

def run_stability_test(num_iterations=ITERATIONS, warm_up_sec=5):
    """
    Menjalankan loop inferensi berkelanjutan untuk mengukur stabilitas performa.
    """
    global global_frame, camera_running

    if model is None:
        return None

    # 1. Start Camera Thread
    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()

    # 2. Tunggu Frame Siap dan Cek Kegagalan Awal
    # ... (Kode tunggu frame siap) ...
    start_wait = time.time()
    while global_frame is None:
        time.sleep(0.5)
        if not camera_running or time.time() - start_wait > 10:
             print("[FAIL] Gagal mendapatkan frame kamera.")
             camera_running = False
             cam_thread.join()
             return None

    # 3. Warm-up
    print(f"\n[WARMUP] Melakukan warm-up selama {warm_up_sec} detik...")
    warm_up_start = time.time()
    while time.time() - warm_up_start < warm_up_sec:
        run_yolo_inference(global_frame.copy())
        time.sleep(0.1)
    print("  Warm-up selesai.")

    # 4. Pengujian Stabilitas (Iterasi Beruntun)
    print(f"\n[TEST START] Memulai pengujian stabilitas {num_iterations} iterasi...")
    
    test_data = []
    temp_start = get_cpu_temp()
    
    for i in range(1, num_iterations + 1):
        test_start_time = time.time()
        
        frame = global_frame.copy()
        temp_before = get_cpu_temp()
        
        # Inferensi
        det_count, avg_conf, latency_ms = run_yolo_inference(frame)
        
        temp_after = get_cpu_temp()
        
        # Kumpulkan Data Iterasi
        data = {
            "iteration": i,
            "latency_ms": latency_ms,
            "ips": 1000 / latency_ms if latency_ms > 0 else 0,
            "temp_start_C": temp_before,
            "temp_end_C": temp_after,
            "total_detections": det_count,
            "avg_confidence": avg_conf
        }
        test_data.append(data)
        
        print(f"  Iterasi {i}/{num_iterations}: Latency {latency_ms:.2f}ms | FPS: {data['ips']:.2f} | Temp: {temp_after}C", end='\r')
        
    # 5. Stop Thread dan Hitung Hasil Akhir
    camera_running = False 
    cam_thread.join()
    test_end_time = time.time()
    
    # Analisis Metrik Stabilitas
    latencies = [d['latency_ms'] for d in test_data]
    ips_list = [d['ips'] for d in test_data]
    
    # Hitung Perubahan Performa
    avg_ips = np.mean(ips_list)
    initial_ips = ips_list[0]
    final_ips = ips_list[-1]
    
    ips_change_percent = ((final_ips - initial_ips) / initial_ips) * 100 if initial_ips > 0 else 0
    
    # Hasil Akhir
    results = {
        "test_summary": "YOLOv8 Performance Stability Test",
        "device": device,
        "iterations": num_iterations,
        "total_test_duration_sec": round(test_end_time - test_start_time, 2),
        "avg_ips": round(avg_ips, 2),
        "avg_latency_ms": round(np.mean(latencies), 2),
        "latency_std_dev_ms": round(np.std(latencies), 2), # Deviasi standar (konsistensi)
        "temp_initial_C": temp_start,
        "temp_final_C": get_cpu_temp(), # Suhu setelah pengujian selesai
        "ips_change_percent": round(ips_change_percent, 2), # Perubahan Kinerja
        "raw_data": test_data
    }

    # 6. Cetak Ringkasan Hasil
    print("\n\n" + "="*50)
    print("        ✅ HASIL PENGUJIAN STABILITAS PERFORMA")
    print("="*50)
    print(f"🌡️  Suhu Awal/Akhir  : {results['temp_initial_C']}°C -> {results['temp_final_C']}°C")
    print(f"📈 Perubahan Kinerja: {results['ips_change_percent']:.2f}% (Final vs Initial)")
    print(f"🚀 **IPS Rata-rata:** **{results['avg_ips']:.2f}**")
    print(f"⏳ **Latensi Rata-rata:** **{results['avg_latency_ms']:.2f} ms**")
    print(f"📏 **Deviasi Latensi (Konsistensi):** **{results['latency_std_dev_ms']:.2f} ms**")
    print("="*50)

    return results

if __name__ == "__main__":
    JSON_FILENAME = "stability_results.json"
    
    try:
        results = run_stability_test(num_iterations=ITERATIONS)
        
        if results:
            with open(JSON_FILENAME, 'w') as f:
                json.dump(results, f, indent=4) 
            print(f"\n[SUCCESS] Hasil pengujian berhasil disimpan ke: **{JSON_FILENAME}**")
        else:
            print("\n[INFO] Pengujian gagal total.")
        
    except KeyboardInterrupt:
        print("\nPengujian dibatalkan oleh pengguna.")
    finally:
        print("Selesai.")