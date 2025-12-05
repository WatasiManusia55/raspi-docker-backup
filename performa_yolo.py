# perform_yolo_test.py (VERSI DENGAN LOGGING JSON)
import time
import os
import uuid
import torch
import numpy as np
import cv2
import threading
import json # <-- Tambah import JSON
from ultralytics import YOLO


# ====================================================
# === KONSTANTA & SETUP YOLO ===
# ====================================================


# Konfigurasi YOLO
MIN_CONF   = 0.6
IMG_SIZE   = 1408
NMS_IOU    = 0.52
MAX_DET    = 1000
ONLY_CLASS = 1 # Jentik (asumsi kelas 0)
MODEL_PATH = "/home/pi/Documents/AI/best (14).pt"


# Folder & File untuk menyimpan hasil
OUTPUT_DIR = "yolo_test_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)
JSON_LOG_FILE = os.path.join(OUTPUT_DIR, "yolo_detection_log.json") # <-- File JSON output


# GPU / CPU SETUP
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] YOLO Device: {device}")


# ====================================================
# === VARIABEL GLOBAL THREAD & METRIK ===
# ====================================================
CAM_INDEX = 1
global_frame = None    
is_running = True      
ai_count = 0          
ai_last = time.time()
ai_throughput = 0      
DETECTION_LOG = [] # <-- VARIABEL BARU UNTUK MENYIMPAN HASIL


# ====================================================
# === FUNGSI UTILITY ===
# ====================================================


def run_yolo(frame):
    """Fungsi untuk menjalankan deteksi YOLO pada satu frame."""
    global ai_count, ai_last, ai_throughput, DETECTION_LOG


    start_det_time = time.time() # Waktu mulai deteksi


    # 1. Hitung Throughput
    ai_count += 1
    current_time = time.time()
    if current_time - ai_last >= 1:
        dur = current_time - ai_last
        ai_throughput = ai_count / dur
        print(f"[THROUGHPUT AI] {ai_throughput:.2f} FPS")
        ai_count = 0
        ai_last = current_time
   
    # 2. Pre-processing (Sharpen/Contrast)
    try:
        processed_frame = frame.copy()
        blur = cv2.GaussianBlur(processed_frame, (0, 0), 3)
        processed_frame = cv2.addWeighted(processed_frame, 1.4, blur, -0.4, 0)
    except Exception:
        processed_frame = frame.copy()


    # 3. Jalankan deteksi YOLO
    results = model.predict(
        source=processed_frame,
        conf=MIN_CONF,
        imgsz=IMG_SIZE,
        iou=NMS_IOU,
        classes=[ONLY_CLASS],
        max_det=MAX_DET,
        device=device,
        verbose=False
    )


    end_det_time = time.time() # Waktu selesai deteksi
   
    res = results[0]
    det_count = len(res.boxes)
    avg_conf = 0.0
   
    if det_count > 0:
        confs = res.boxes.conf.detach().cpu().numpy()
        avg_conf = float(np.mean(confs))


    # 4. Simpan ke Log JSON
    DETECTION_LOG.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_det_time)),
        "detection_time_ms": round((end_det_time - start_det_time) * 1000, 2), # Milidetik
        "detections": det_count,
        "avg_confidence": round(avg_conf, 4)
    })
   
    return det_count, avg_conf


def save_log_to_json(final_metrics):
    """Menyimpan log deteksi dan metrik akhir ke file JSON."""
    final_output = {
        "metadata": {
            "model_path": MODEL_PATH,
            "device": device,
            "config": {
                "min_conf": MIN_CONF,
                "img_size": IMG_SIZE,
                "nms_iou": NMS_IOU
            }
        },
        "final_metrics": final_metrics,
        "detection_history": DETECTION_LOG
    }
   
    try:
        with open(JSON_LOG_FILE, 'w') as f:
            json.dump(final_output, f, indent=4)
        print(f"✅ Log deteksi dan metrik akhir berhasil disimpan ke: {JSON_LOG_FILE}")
    except Exception as e:
        print(f"❌ Gagal menyimpan log JSON: {e}")


# ====================================================
# === THREAD KAMERA (Tidak Berubah) ===
# ====================================================


def camera_loop():
    """Thread latar belakang untuk terus menerus mengambil frame kamera."""
    global global_frame, is_running


    print(f"[INFO] Starting camera background thread on ID: {CAM_INDEX}...")


    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print(f"❌ KRITIS: Gagal membuka webcam device {CAM_INDEX}. Hentikan thread.")
        is_running = False
        return


    # --- Pengaturan Exposure (Seperti di kode Anda) ---
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    time.sleep(0.1)


    cap.set(cv2.CAP_PROP_EXPOSURE, -4)  
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 140)
    cap.set(cv2.CAP_PROP_CONTRAST, 32)
    cap.set(cv2.CAP_PROP_SATURATION, 64)
    cap.set(cv2.CAP_PROP_GAIN, 0)
    cap.set(cv2.CAP_PROP_EXPOSUREPROGRAM, 1)


    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)


    # Loop kamera
    while is_running:
        ret, frame = cap.read()
        if ret:
            global_frame = frame
        else:
            time.sleep(0.01)


    cap.release()
    print("[INFO] Camera thread stopped.")


# ====================================================
# === MAIN EXECUTION ===
# ====================================================


if __name__ == "__main__":
   
    # 1. LOAD YOLO MODEL
    try:
        model = YOLO(MODEL_PATH)
        print("[INFO] Model loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Cannot load model: {e}")
        exit()


    # 2. JALANKAN THREAD KAMERA
    t = threading.Thread(target=camera_loop, daemon=True)
    t.start()
   
    # Tunggu hingga kamera siap
    print("[INFO] Waiting for first camera frame...")
    timeout_start = time.time()
    while global_frame is None and time.time() - timeout_start < 5:
        time.sleep(0.1)
   
    if global_frame is None:
        print("❌ GAGAL mendapatkan frame dari kamera dalam 5 detik. Pastikan CAM_INDEX (saat ini 1) sudah benar.")
        is_running = False
        t.join()
        exit()
   
    print("✅ Kamera siap. Memulai loop deteksi YOLO...")
   
    # 3. LOOP UTAMA (DETEKSI)
    total_detections = 0
    start_test_time = time.time()
    test_duration_seconds = 60
   
    try:
        while is_running and (time.time() - start_test_time) < test_duration_seconds:
            frame_to_process = global_frame.copy()
            det_count, avg_conf = run_yolo(frame_to_process)
            total_detections += det_count
           
            if ai_count % 10 == 0:
                 # Cetak hasil setiap 10 frame, menggunakan data dari log yang baru ditambahkan
                 latest_log = DETECTION_LOG[-1]
                 print(f"| Deteksi: {det_count} | Conf: {avg_conf:.3f} | Latensi: {latest_log['detection_time_ms']:.2f} ms | Total Jentik: {total_detections} |")


    except KeyboardInterrupt:
        print("\n[STOP] Dihentikan oleh pengguna (Ctrl+C).")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
       
    finally:
        # 4. CLEANUP & LAPORAN AKHIR
        is_running = False
        t.join()
       
        end_test_time = time.time()
        actual_duration = end_test_time - start_test_time
       
        # Hitung metrik akhir
        final_metrics = {
            "actual_duration_s": round(actual_duration, 2),
            "total_ai_processes": len(DETECTION_LOG),
            "total_detections": total_detections,
            "avg_fps": round(len(DETECTION_LOG) / actual_duration, 2) if actual_duration > 0 else 0.0
        }
       
        print("\n" + "="*50)
        print("=== LAPORAN UJI PERFORMA YOLO SELESAI ===")
        print(f"Durasi Tes Aktual: {final_metrics['actual_duration_s']:.2f} detik")
        print(f"Jumlah Proses AI: {final_metrics['total_ai_processes']}")
        print(f"FPS Rata-rata: {final_metrics['avg_fps']:.2f} FPS")
        print(f"Total Deteksi Jentik: {final_metrics['total_detections']}")
        print("="*50)
       
        # 5. SIMPAN LOG KE JSON
        save_log_to_json(final_metrics)
       
        print("Program selesai.")


