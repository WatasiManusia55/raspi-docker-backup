# ====================================================
# === BAGIAN 1: IMPORT LIBRARY & SETUP GLOBAL/KONSTANTA ===
# ====================================================


import RPi.GPIO as GPIO
import time
import spidev
import board
import adafruit_dht
from adafruit_dht import DHT22
import math
import json 
from flask import Flask, render_template, jsonify, request
import socket, requests, psutil, subprocess
import os
import uuid
import torch
from ultralytics import YOLO 
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
import numpy as np 
import cv2
import threading
from functools import wraps


# ====================================================
# === VARIABEL GLOBAL SISTEM & KONSTANTA ===
# ====================================================


# Throughput Metrik
sensor_count = 0
sensor_last = time.time()
sensor_throughput = 0
ai_count = 0
ai_last = time.time()
ai_throughput = 0
throughput_log = []


# --- SETUP SENSOR & PERANGKAT KERAS ---
dht = adafruit_dht.DHT22(board.D4)
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000


# Pastikan folder hasil ada
os.makedirs("static/results/detections", exist_ok=True)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --- Setup GPIO ---
try:
    GPIO.setmode(GPIO.BCM)
except RuntimeError as e:
    if "already been set" not in str(e):
        raise e


# --- Digital Pin Sensor Gas ---
MQ2_DO = 5
MQ135_DO = 27
GPIO.setup(MQ2_DO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(MQ135_DO, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# --- DHT22 ---
DHT_PIN = board.D17
dhtDevice = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)


# --- Konstanta Kalibrasi Sensor ---
HUMIDITY_CORRECTION_FACTOR = 10.0
V_REF = 3.3
R_LOAD = 10.0 # kΩ
PH7_VOLTAGE = 1.625 # Voltage pada pH 7.0
PH4_VOLTAGE = 1.613 # Voltage pada pH 4.0
A_MQ2 = 800
B_MQ2 = -1.5
MQ2_RATIO_CLEAN_AIR = 9.83
A_MQ135 = 1000
B_MQ135 = -2.862
MQ135_RATIO_CLEAN_AIR = 3.6
R0_MQ2 = 25.0 
R0_MQ135 = 25.0


# C. Assign channel MCP3008
CH_MQ2_AO = 0
CH_MQ135_AO = 1
CH_LDR = 2
CH_PH = 3


# ===============================
# CONFIG YOLO (DARI KODE KEDUA)
# ===============================
MIN_CONF   = 0.6
IMG_SIZE   = 1408
NMS_IOU    = 0.52
MAX_DET    = 1000
ONLY_CLASS = 0
MODEL_PATH = "/home/pi/Documents/AI/best (14).pt"


# ===============================
# GPU / CPU SETUP (DARI KODE KEDUA)
# ===============================
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] YOLO Device: {device}")


# ===============================
# LOAD YOLO MODEL (DARI KODE KEDUA)
# ===============================
try:
    model = YOLO(MODEL_PATH)
    print("[INFO] Model loaded successfully.")
except Exception as e:
    print("[ERROR] Cannot load model:", e)
    model = None


# ===============================
# CAMERA THREAD (FAST MODE) - DARI KODE KEDUA
# ===============================
CAM_INDEX = 0
global_frame = None


def camera_loop():
    global global_frame


    print("[INFO] Starting camera background thread...")


    cap = cv2.VideoCapture(CAM_INDEX)


    # =====================================================
    # EXPOSURE FIX — MANUAL MODE (ANTI GELAP)
    # =====================================================
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # manual mode
    time.sleep(0.1)


    cap.set(cv2.CAP_PROP_EXPOSURE, -4)      # coba -6 s/d -3
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 140)
    cap.set(cv2.CAP_PROP_CONTRAST, 32)
    cap.set(cv2.CAP_PROP_SATURATION, 64)
    cap.set(cv2.CAP_PROP_GAIN, 0)
    cap.set(cv2.CAP_PROP_EXPOSUREPROGRAM, 1)


    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)


    print("[INFO] Exposure Settings Applied:")
    print("  Auto Exposure :", cap.get(cv2.CAP_PROP_AUTO_EXPOSURE))
    print("  Exposure      :", cap.get(cv2.CAP_PROP_EXPOSURE))
    print("  Brightness    :", cap.get(cv2.CAP_PROP_BRIGHTNESS))
    print("  Contrast    :", cap.get(cv2.CAP_PROP_CONTRAST))
    print("  Saturation    :", cap.get(cv2.CAP_PROP_SATURATION))
    print("  Gain          :", cap.get(cv2.CAP_PROP_GAIN))
    print("========================================")


    # Loop kamera
    while True:
        ret, frame = cap.read()
        if ret:
            global_frame = frame


# Jalankan thread kamera
t = threading.Thread(target=camera_loop, daemon=True)
t.start()


# --- Variabel Global untuk Metrik & Kalibrasi ---
app = Flask(__name__)
from flask_cors import CORS
CORS(app)
@app.after_request
def add_security_headers(response):
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "connect-src 'self'; "
        "frame-ancestors 'self';"
    )
    return response
load_dotenv()
API_KEY = os.getenv("API_KEY") 
request_count = 0
start_time = time.time()
try:
    net_counters = psutil.net_io_counters()
    last_bytes_sent = net_counters.bytes_sent
    last_bytes_recv = net_counters.bytes_recv
    last_time = time.time()
except Exception:
    last_bytes_sent, last_bytes_recv, last_time = 0, 0, time.time()


# --- Setup Cache File ---
CACHE_FILE = "sensor_cache.json"
MAX_CACHE_SIZE = 1000 


# --- Database Credentials ---
DB_HOST = os.getenv("DB_HOST", "10.218.161.79")  
DB_NAME = os.getenv("DB_NAME", "iotdb")
DB_USER = os.getenv("DB_USER", "iotuser")
DB_PASS = os.getenv("DB_PASS", "iotpass123")


# ====================================================
# === AUTENTIKASI API KEY & UTILITY CACHE OFFLINE ===
# ====================================================
RATE_LIMIT = 5
RATE_WINDOW = 10
rate_log = {}


def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        if key != API_KEY:
            return jsonify({"error": "Unauthorized access"}), 401
        return func(*args, **kwargs)
    return wrapper


def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")


        now = time.time()


        # buat container timestamp buat API key
        if key not in rate_log:
            rate_log[key] = []


        # bersihkan timestamp yg sudah lewat window waktu
        rate_log[key] = [t for t in rate_log[key] if now - t < RATE_WINDOW]


        # cek apakah sudah melewati limit
        if len(rate_log[key]) >= RATE_LIMIT:
            return jsonify({
                "error": "Rate limit exceeded",
                "limit": RATE_LIMIT,
                "window_seconds": RATE_WINDOW
            }), 429


        # simpan timestamp request ini
        rate_log[key].append(now)


        return func(*args, **kwargs)
    return wrapper




def load_cache():
    """Memuat data cache dari file JSON."""
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_cache(data_list):
    """Menyimpan data cache ke file JSON."""
    try:
        if len(data_list) > MAX_CACHE_SIZE:
             data_list = data_list[-MAX_CACHE_SIZE:]
             print(f"⚠ Cache dipotong menjadi {MAX_CACHE_SIZE} entri.")
             
        with open(CACHE_FILE, 'w') as f:
            # Menggunakan default=str untuk menangani objek datetime jika ada
            json.dump(data_list, f, indent=4, default=str) 
    except Exception as e:
        print(f"❌ Gagal menyimpan cache ke file: {e}")


# ====================================================
# === BAGIAN 2: FUNGSI UTILITY SENSOR ===
# ====================================================


def read_adc(channel):
    """Membaca nilai ADC dari MCP3008."""
    if channel < 0 or channel > 7:
        return -1
    r = spi.xfer2([1, (8+channel)<<4, 0])
    adc_out = ((r[1] & 3) << 8) + r[2] 
    return adc_out


def read_resistance(adc_val, V_ref=V_REF, R_load=R_LOAD):
    """Menghitung Rs (Resistansi Sensor) dari nilai ADC."""
    ADC_MAX = 1023.0
    V_out = (adc_val * V_ref) / ADC_MAX
    
    if V_out <= 0:
        return float('inf')
    Rs = R_load * ((V_ref / V_out) - 1.0)
    return Rs


def resistance_to_ppm_mq(Rs, R0, A, B):
    """Konversi Rs ke ppm menggunakan Model Daya: ppm = A * (Rs/R0)^B."""
    try:
        ratio = Rs / R0 if R0 and R0 > 0 else 0
        if ratio <= 0:
            return None
        ppm = A * (ratio ** B)
        return round(ppm, 2)
    except Exception:
        return None


def resistance_to_ppm_mq2(Rs, R0):
    return resistance_to_ppm_mq(Rs, R0, A_MQ2, B_MQ2)


def resistance_to_ppm_mq135(Rs, R0):
    return resistance_to_ppm_mq(Rs, R0, A_MQ135, B_MQ135)


def adc_to_lux(adc_val):
    """Konversi LDR (dengan LOGIKA KOREKSI KUADRATIK)."""
    MAX_LUX_SCALE = 500.0 
    ADC_MAX = 1023.0


    if adc_val < 0 or adc_val >= ADC_MAX:
        return 0.0
    
    inverted_adc = ADC_MAX - adc_val
    normalized_value = inverted_adc / ADC_MAX
    # Rumus kuadratik untuk sensitivitas tinggi di kondisi gelap
    lux = (normalized_value ** 2) * MAX_LUX_SCALE
    
    return max(0.0, lux) 


def calibrate_sensor(channel, ratio_clean_air, samples=50, delay=0.2):
    """Menghitung R0 (Resistansi di Udara Bersih)."""
    Rs_sum = 0.0
    for i in range(samples):
        adc_val = read_adc(channel)
        Rs = read_resistance(adc_val)
        Rs_sum += Rs
        time.sleep(delay)
    Rs_avg = Rs_sum / samples
    return Rs_avg / ratio_clean_air


def setup_calibration():
    """Fungsi untuk menjalankan kalibrasi R0 saat startup."""
    global R0_MQ2, R0_MQ135
    print("=== Kalibrasi MQ-2 & MQ-135 saat startup... ===")
    try:
        R0_MQ2 = calibrate_sensor(CH_MQ2_AO, MQ2_RATIO_CLEAN_AIR)
        R0_MQ135 = calibrate_sensor(CH_MQ135_AO, MQ135_RATIO_CLEAN_AIR)
        print(f"R0 MQ-2: {R0_MQ2:.2f} kΩ, R0 MQ-135: {R0_MQ135:.2f} kΩ. Selesai.")
    except Exception as e:
        print(f"Gagal Kalibrasi R0: {e}. Menggunakan nilai default.")


# ====================================================
# === FUNGSI pH YANG DIPERBAIKI (INTEGRASI LOGIKA BARU) ===
# ====================================================


def read_ph_corrected():
    """Baca pH dengan logika yang diperbaiki"""
    adc = read_adc(CH_PH)
    voltage = (adc * V_REF) / 1023.0
    
    # print(f"DEBUG: ADC={adc}, Voltage={voltage:.3f}V", end=" | ")
    
    # LOGIKA YANG DIPERBAIKI
    if voltage < 1.60:  # pH < 5 (ASAM)
        ph_est = 4.5
        status = "🔴 ASAM"
        reason = f"Voltage {voltage:.3f}V < 1.60V (pH < 5)"
    elif voltage > 1.65:  # pH > 8 (BASA)
        ph_est = 8.5
        status = "🔵 BASA" 
        reason = f"Voltage {voltage:.3f}V > 1.65V (pH > 8)"
    else:  # pH 6-7.8 (NETRAL)
        ph_est = 7.0
        status = "🟢 NETRAL"
        reason = f"Voltage {voltage:.3f}V dalam range 1.60V-1.65V (pH 6-7.8)"
    
    # print(f"pH: {ph_est:.1f} | {status} | {reason}")
    return ph_est, status


def read_ph_stable(samples=5, delay=0.1):
    """Baca pH dengan multiple sampling untuk hasil yang stabil"""
    voltages = []
    for i in range(samples):
        ph_adc = read_adc(CH_PH)
        if ph_adc >= 0:  # Valid ADC reading
            voltage = (ph_adc * V_REF) / 1023.0
            voltages.append(voltage)
        time.sleep(delay)
    
    if not voltages:
        return 7.0, "🟡 ERROR", "Gagal membaca sensor"
    
    avg_voltage = sum(voltages) / len(voltages)
    
    # GUNAKAN LOGIKA YANG SUDAH DIPERBAIKI
    ph_val, ph_status = read_ph_corrected()
    
    return ph_val, ph_status, f"Voltage {avg_voltage:.3f}V"


# ====================================================
# === BAGIAN 3: FUNGSI JARINGAN & SENSOR UTAMA ===
# ====================================================


def network_analysis():
    # Logika network_analysis (tidak berubah)
    global last_bytes_sent, last_bytes_recv, last_time


    hostname = socket.gethostname()
    ip_local = socket.gethostbyname(hostname)


    try:
        ip_public = requests.get("https://api.ipify.org", timeout=1).text
    except:
        ip_public = "Tidak bisa ambil"


    interfaces = psutil.net_if_stats()
    net_io = psutil.net_io_counters()
    bytes_sent = net_io.bytes_sent
    bytes_recv = net_io.bytes_recv


    now = time.time()
    elapsed = now - last_time
    if elapsed > 0.01:
        tx_speed = (bytes_sent - last_bytes_sent) / elapsed / 1024
        rx_speed = (bytes_recv - last_bytes_recv) / elapsed / 1024
    else:
        tx_speed, rx_speed = 0.0, 0.0


    last_bytes_sent, last_bytes_recv, last_time = bytes_sent, bytes_recv, now


    try:
        ping = subprocess.check_output(
            ["ping", "-c", "1", "-W", "1", "8.8.8.8"],
            universal_newlines=True
        )
        latency_line = [line for line in ping.split('\n') if 'avg' in line]
        if latency_line:
            latency = latency_line[0].split('/')[4] + " ms"
        else:
            latency = "Timeout"
    except:
        latency = "Timeout"


    return {
        "ip_local": ip_local,
        "ip_public": ip_public,
        "interfaces": {name: stats.isup for name, stats in interfaces.items()},
        "tx_total": f"{bytes_sent/1024/1024:.2f} MB",
        "rx_total": f"{bytes_recv/1024/1024:.2f} MB",
        "tx_speed": f"{tx_speed:.2f} KB/s",
        "rx_speed": f"{rx_speed:.2f} KB/s",
        "latency": latency
    }




def get_all_sensor_readings():
    """Membaca semua sensor dan mengembalikan data dalam dictionary."""
    global sensor_count, sensor_last, sensor_throughput


    # === HITUNG THROUGHPUT SENSOR ===
    sensor_count += 1
    current_time = time.time()


    if current_time - sensor_last >= 1:
        sensor_throughput = sensor_count / (current_time - sensor_last)
        print(f"[THROUGHPUT SENSOR] {sensor_throughput:.2f} sampel/detik")


        sensor_count = 0
        sensor_last = current_time
    # === END THROUGHPUT ===


    # --- DHT22 (Suhu & Kelembaban) ---
    temperature_c, humidity = None, None
    try:
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        
        # Koreksi Kelembaban
        if humidity is not None:
            humidity = humidity - HUMIDITY_CORRECTION_FACTOR 
            if humidity < 0:
                humidity = 0.0
    except RuntimeError:
        pass 
    except Exception:
        pass


    # --- MQ2 (Gas Mudah Terbakar) ---
    mq2_adc = read_adc(CH_MQ2_AO)
    Rs_mq2 = read_resistance(mq2_adc)
    mq2_ppm = resistance_to_ppm_mq2(Rs_mq2, R0_MQ2)
    
    if mq2_ppm is not None and mq2_ppm >= 30:
        mq2_status = "Gas Terdeteksi" 
    elif mq2_ppm is not None:
        mq2_status = "Aman"
    else:
        mq2_status = "Error Baca Sensor"


    # --- MQ135 (Kualitas Udara) ---
    mq135_adc = read_adc(CH_MQ135_AO)
    Rs_mq135 = read_resistance(mq135_adc)
    mq135_ppm = resistance_to_ppm_mq135(Rs_mq135, R0_MQ135)
    if mq135_ppm is not None and mq135_ppm >= 300:
        mq135_status = "🚨 Udara TIDAK BAIK (>=300 PPM)"
    else:
        if mq135_ppm is not None:
            mq135_status = "✅ Udara BAIK (<300 PPM)"
        else:
            mq135_status = "Error Baca Sensor"


    # --- LDR (Cahaya) ---
    ldr_adc = read_adc(CH_LDR)
    ldr_lux = adc_to_lux(ldr_adc) 
    
    # 📌 LOGIKA LDR BERDASARKAN LUX (3-TIER BARU)
    if ldr_lux < 250:
        ldr_status = "Rendah"
    elif ldr_lux <= 350:
        ldr_status = "Ideal"
    else: # ldr_lux > 350
        ldr_status = "Tinggi"
    # END LOGIKA LDR


    # --- pH ---
    ph_val, ph_status = read_ph_corrected()


    # --- NETWORK ---
    net_info = network_analysis()


    return {
        # Data untuk tampilan Web (dengan format string)
        "temp": f"{temperature_c:.1f}" if temperature_c is not None else "Error",
        "hum": f"{humidity:.1f}" if humidity is not None else "Error",
        "mq2_status": mq2_status,
        "mq2_ppm": f"{mq2_ppm}" if mq2_ppm is not None else "Error",
        "mq135_status": mq135_status,
        "mq135_ppm": f"{mq135_ppm}" if mq135_ppm is not None else "Error",
        "ldr_status": ldr_status, # Mengirim marker status Lux ("Rendah", "Ideal", "Tinggi")
        "ldr_lux": f"{ldr_lux:.2f}",
        "ldr_adc": f"{ldr_adc}", 
        "ph_val": f"{ph_val:.1f}",  
        "ph_status": ph_status,  
        
        # Data MENTAH untuk penyimpanan DB (nilai float/None)
        "temp_raw": temperature_c,
        "hum_raw": humidity,
        "ph_val_raw": ph_val,
        "ph_status_raw": ph_status,
        "ldr_lux_raw": ldr_lux,
        "mq2_ppm_raw": mq2_ppm,
        "mq135_ppm_raw": mq135_ppm,
        "net": net_info
    }


# ====================================================
# === BAGIAN 4: FUNGSI AI (DARI KODE KEDUA) ===
# ====================================================


def run_yolo(image_path, original_filename):
    """Fungsi AI dari kode kedua yang lebih optimal"""
    global ai_count, ai_last, ai_throughput
    
    current_time = time.time()
    if current_time - ai_last >= 1:
        dur = current_time - ai_last
        ai_throughput = ai_count / dur
        ai_count = 0
        ai_last = current_time
    ai_count += 1


    uid = uuid.uuid4().hex
    out_name = f"{uid}_result.jpg"
    out_path = os.path.join("static/results/detections", out_name)


    results = model.predict(
        source=image_path,
        conf=MIN_CONF,
        imgsz=IMG_SIZE,
        iou=NMS_IOU,
        classes=[ONLY_CLASS],
        max_det=MAX_DET,
        device=device,
        verbose=False
    )


    res = results[0]
    det_count = len(res.boxes)
    avg_conf = 0.0
    conf_list = []


    if det_count > 0:
        confs = res.boxes.conf.detach().cpu().numpy()
        avg_conf = float(np.mean(confs))
        conf_list = [round(float(c), 4) for c in confs]


    plotted = res.plot()
    cv2.imwrite(out_path, plotted)


    return (
        f"uploads/{original_filename}",
        f"results/detections/{out_name}",
        avg_conf,
        det_count,
        conf_list
    )


# ====================================================
# === BAGIAN 5: FLASK ENDPOINTS (RUTE WEB) ===
# ====================================================


@app.route("/heartbeat")
def heartbeat():
    return jsonify({"status": "ok"})
    
@app.route("/throughput_upload", methods=["POST"])
def throughput_upload():
    received = request.data
    return {"status": "ok", "size_bytes": len(received)}
    
@app.route("/")
def index():
    global request_count, start_time
    request_count += 1
    elapsed = time.time() - start_time
    throughput = request_count / elapsed if elapsed > 0 else 0


    data = get_all_sensor_readings()
    net_info = data["net"]


    # Log terminal
    print("=" * 40)
    print(f"Request: {request_count}, Throughput: {throughput:.2f} req/s")
    print(f"LDR Status: {data['ldr_status']} | Lux: {data['ldr_lux']}")
    print(f"pH Status: {data['ph_status']} | pH: {data['ph_val']}")
    # ... (Log detail sensor lainnya)
    print("=" * 40)


    data_for_template = {k: v for k, v in data.items() if not k.endswith('_raw')}
    
    return render_template(
        "index.html",
        **data_for_template,
        throughput=f"{throughput:.2f} req/s"
    )


@app.route("/api/rate-test", methods=["GET"])
@require_api_key
@rate_limit
def rate_test():
    # Perbaikan Indentasi 
    return jsonify({"message": "OK"}) 


@app.route("/data")
@require_api_key
def get_data_json():
    """Endpoint untuk AJAX, mengembalikan data sensor mentah dalam JSON."""
    
    # Perbaikan Indentasi - baris-baris ini harus ter-indentasi
    data = get_all_sensor_readings()
    save_sensor_data(data)


    data_for_json = {k: v for k, v in data.items() if not k.endswith('_raw')}
    
    if 'jentik_status' not in data_for_json:
        data_for_json['jentik_status'] = "-- Belum dicek"


    return jsonify(data_for_json)




@app.route("/trigger_ai", methods=["POST"])
@require_api_key
def trigger_ai():
    """Trigger AI (YOLO) dengan ambil gambar dari kamera - VERSI OPTIMAL"""
    global global_frame


    if model is None:
        return jsonify({"error": "Model AI tidak tersedia di server."}), 500


    if global_frame is None:
        return jsonify({"error": "Kamera belum siap. Tunggu beberapa detik."}), 500


    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)


    # 1️⃣ Ambil gambar dari frame kamera yang sudah tersedia (SUPER FAST)
    frame = global_frame.copy()
    cv2.imwrite(filepath, frame)


    # 2️⃣ Pre-processing (sharpen/contrast)
    try:
        blur = cv2.GaussianBlur(frame, (0, 0), 3)
        sharp = cv2.addWeighted(frame, 1.4, blur, -0.4, 0)
        cv2.imwrite(filepath, sharp)
    except Exception as e:
        print(f"[IMAGE WARN] preprocessing gagal: {e}")


    # 3️⃣ Jalankan deteksi YOLO
    try:
        uploaded_rel, result_rel, avg_conf, det_count, conf_list = run_yolo(filepath, filename)
    except Exception as e:
        return jsonify({"error": f"Gagal menjalankan model AI: {e}"}), 500


    # 4️⃣ Simpan ke DB
    try:
        save_ai_data("jentik", det_count) 
    except Exception as e:
        print(f"[DB WARN] Gagal simpan hasil AI: {e}")


    # 5️⃣ PRINT KE TERMINAL & Kirim hasil ke frontend
    print("\n===== AI DETECTION RESULT =====")
    print(f"Jumlah Jentik  : {det_count}")
    print(f"Conf Score List: {conf_list}")
    print(f"Avg Confidence : {round(avg_conf,3)}")
    print("================================\n")


    status = "✅ Ada jentik terdeteksi." if det_count > 0 else "❌ Tidak ada jentik terdeteksi."
    
    return jsonify({
        "status": status,
        "num_detections": det_count,
        "confidence": round(avg_conf, 3),
        "confidence_list": conf_list,
        "result_image": f"/static/{result_rel}",  
        "uploaded_image": f"/static/{uploaded_rel}", 
        "jentik_status": status,  
        "params": {
            "conf": MIN_CONF, "iou": NMS_IOU, "imgsz": IMG_SIZE,
            "max_det": MAX_DET, "device": device
        }
    })


@app.route("/latest_detection")
@require_api_key
def get_latest_detection():
    """Mengambil hasil deteksi AI terbaru dari database."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500


    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT label, jumlah_deteksi, timestamp 
            FROM detection_data 
            ORDER BY timestamp DESC 
            LIMIT 1;
        """)
        result = cur.fetchone()
        cur.close()
        conn.close()


        if result:
            return jsonify({
                "status": "success",
                "label": result[0],
                "jumlah_deteksi": result[1],
                "timestamp": result[2].isoformat()
            })
        else:
            return jsonify({"status": "no data found"}), 200


    except Exception as e:
        print(f"Error fetching latest detection: {e}")
        return jsonify({"error": "Failed to fetch data from DB"}), 500
# ====================================================
# === BAGIAN 6: KONEKSI, SIMPAN DATA, & CACHING (POSTGRESQL) ===
# ====================================================


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception:
        return None


def get_data_value(data, key):
    raw_key = key + "_raw"
    val = data.get(raw_key)
    
    if val is None:
        return None 
    
    try:
        return float(val)
    except (TypeError, ValueError):
        return None 


def forward_cached_data():
    """
    Mencoba mengirim semua data yang tersimpan di cache lokal ke database.
    Dipanggil setelah satu data berhasil dikirim ke DB.
    """
    cache_data = load_cache()
    if not cache_data:
        return
        
    print(f"🔄 Mencoba mengirim {len(cache_data)} entri data dari cache...")
    conn = get_db_connection()
    if not conn:
        print("⚠ Koneksi DB masih belum pulih. Forwarding dibatalkan.")
        return


    try:
        cur = conn.cursor()
        success_count = 0
        insert_query = """
        INSERT INTO sensor_data 
        (suhu, kelembaban, ph, cahaya, gas_mq2, gas_mq135, 
        status_mq2, status_mq135, waktu, gas)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        for item in cache_data:
            try:
                waktu_obj = datetime.fromisoformat(item['waktu'])
                
                cur.execute(insert_query, (
                    item['suhu'], item['kelembaban'], item['ph'], item['cahaya'], 
                    item['gas_mq2'], item['gas_mq135'], item['status_mq2'], 
                    item['status_mq135'], waktu_obj, item['gas']
                ))
                success_count += 1
            except Exception as e:
                print(f"⚠ Item cache ke-{success_count+1} gagal di-forward: {e}. Menghentikan proses.")
                break 


        if success_count > 0:
            conn.commit()
            print(f"✅ Berhasil mem-forward {success_count} entri dari cache ke DB.")
            
            remaining_cache = cache_data[success_count:]
            save_cache(remaining_cache)
            if not remaining_cache:
                 print("Cache berhasil dikosongkan.")
        else:
            print("Tidak ada data baru yang berhasil di-forward.")


    except psycopg2.Error as e:
        print(f"❌ Error saat bulk forwarding (DB): {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


def save_sensor_data(data):
    """
    Mencoba menyimpan data sensor ke PostgreSQL. 
    Jika gagal (tidak ada koneksi), simpan ke cache lokal.
    """
    conn = get_db_connection()
    waktu = datetime.now()
    
    data_to_store = {
        'suhu': get_data_value(data, 'temp'), 
        'kelembaban': get_data_value(data, 'hum'),
        'ph': get_data_value(data, 'ph_val'), 
        'ph_status': data.get('ph_status'),  
        'cahaya': get_data_value(data, 'ldr_lux'),
        'gas_mq2': get_data_value(data, 'mq2_ppm'), 
        'gas_mq135': get_data_value(data, 'mq135_ppm'),
        'status_mq2': data.get('mq2_status'), 
        'status_mq135': data.get('mq135_status'),
        'waktu': waktu.isoformat(), 
        'gas': get_data_value(data, 'mq135_ppm') 
    }


    # === A. Coba Simpan ke Database ===
    if conn:
        try:
            cur = conn.cursor()
            insert_query = """
            INSERT INTO sensor_data 
            (suhu, kelembaban, ph, cahaya, gas_mq2, gas_mq135, 
            status_mq2, status_mq135, waktu, gas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cur.execute(insert_query, (
                data_to_store['suhu'], data_to_store['kelembaban'], 
                data_to_store['ph'], data_to_store['cahaya'], 
                data_to_store['gas_mq2'], data_to_store['gas_mq135'],
                data_to_store['status_mq2'], data_to_store['status_mq135'],
                waktu, data_to_store['gas']
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            print(f"✅ Data sensor berhasil disimpan ke DB.")
            
            # Coba kirim data yang tersimpan di cache
            forward_cached_data() 
            return


        except psycopg2.Error as e:
            print(f"❌ Error simpan data sensor (DB): {e}. Disimpan ke cache.")
            if conn:
                conn.rollback()
                conn.close()
            # Jatuh ke mekanisme caching jika DB error
    
    # === B. Simpan ke Cache Lokal (Fallback) ===
    print("⚠ Tidak bisa konek ke database atau terjadi error DB. Menyimpan data ke cache.")
    cache_data = load_cache()
    data_to_store['waktu'] = str(data_to_store['waktu']) 
    cache_data.append(data_to_store)
    save_cache(cache_data)




def save_ai_data(label, confidence):
    """Simpan hasil deteksi AI ke PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        print("⚠ Tidak bisa konek ke database (AI).")
        # Tidak ada caching untuk data AI di implementasi ini
        return


    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO detection_data (label, jumlah_deteksi, timestamp)
            VALUES (%s, %s, %s)
        """, (label, confidence, datetime.now()))
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Data hasil AI berhasil disimpan ke database.")
    except Exception as e:
        print(f"❌ Error simpan hasil AI: {e}")


# ====================================================
# === BAGIAN 7: MAIN EXECUTION ===
# ====================================================


if __name__ == "__main__":
    setup_calibration()


    try:
        print("\n" + "="*50)
        print("Aplikasi Terpadu (Sensor + AI) berjalan di:")
        print("Web UI: http://0.0.0.0:5000/")
        print("Data JSON: http://0.0.0.0:5000/data")
        print("Trigger AI (POST): http://0.0.0.0:5000/trigger_ai")
        print("="*50)
        app.run(host="0.0.0.0", port=5000, debug=False)


    except KeyboardInterrupt:
        print("\nStop program...")


    finally:
        print("Membersihkan GPIO dan SPI...")
        spi.close()
        GPIO.cleanup()