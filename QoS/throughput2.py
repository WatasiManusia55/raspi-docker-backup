import time
import requests
import csv
import matplotlib.pyplot as plt

# Domain server kamu
UPLOAD_URL = "https://pbl-tmj5a.siling-ai.my.id/throughput_upload"
DOWNLOAD_URL = "https://pbl-tmj5a.siling-ai.my.id/throughput_download"

# Rentang test: 5, 10, ..., 50 MB
SIZES_MB = list(range(5, 51, 5))

CSV_FILE = "throughput_test_5_50mb_kbps.csv"
PLOT_FILE = "throughput_test_5_50mb_kbps.png"

# Session untuk kecepatan lebih baik
session = requests.Session()


def test_upload(size_mb):
    size_bytes = size_mb * 1024 * 1024
    data = b"x" * size_bytes

    print(f"\n=== UPLOAD {size_mb} MB ===")
    t1 = time.perf_counter()
    resp = session.post(UPLOAD_URL, data=data, timeout=400)
    t2 = time.perf_counter()

    resp.raise_for_status()

    dur = t2 - t1
    kb = size_bytes / 1024
    kbps = kb / dur  # <-- langsung Kbps

    print(f"Waktu : {dur:.2f} s")
    print(f"Ukuran: {kb:.2f} KB")
    print(f"Throughput UP: {kbps:.2f} Kbps")

    return kbps


def test_download(size_mb):
    print(f"\n=== DOWNLOAD {size_mb} MB ===")

    params = {"size_mb": size_mb}
    t1 = time.perf_counter()
    resp = session.get(DOWNLOAD_URL, params=params, stream=True, timeout=400)

    total = 0
    for chunk in resp.iter_content(32768):  # 32 KB chunk
        if not chunk:
            break
        total += len(chunk)

    t2 = time.perf_counter()
    resp.raise_for_status()

    dur = t2 - t1
    kb = total / 1024
    kbps = kb / dur  # <-- langsung Kbps

    print(f"Waktu : {dur:.2f} s")
    print(f"Ukuran: {kb:.2f} KB")
    print(f"Throughput DOWN: {kbps:.2f} Kbps")

    return kbps


def main():
    results = []

    for size in SIZES_MB:
        try:
            up = test_upload(size)
        except Exception as e:
            print("Upload error:", e)
            up = 0

        try:
            down = test_download(size)
        except Exception as e:
            print("Download error:", e)
            down = 0

        results.append({
            "size_mb": size,
            "upload_kbps": up,
            "download_kbps": down
        })

    # SIMPAN CSV
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["size_mb", "upload_kbps", "download_kbps"])
        writer.writeheader()
        writer.writerows(results)

    # HITUNG RATA-RATA
    up_vals = [r["upload_kbps"] for r in results if r["upload_kbps"] > 0]
    down_vals = [r["download_kbps"] for r in results if r["download_kbps"] > 0]

    avg_up = sum(up_vals)/len(up_vals) if up_vals else 0
    avg_down = sum(down_vals)/len(down_vals) if down_vals else 0

    print("\n===== RATA-RATA =====")
    print(f"Upload   : {avg_up:.2f} Kbps")
    print(f"Download : {avg_down:.2f} Kbps")

    # GRAFIK
    x = [r["size_mb"] for r in results]
    y1 = [r["upload_kbps"] for r in results]
    y2 = [r["download_kbps"] for r in results]

    plt.plot(x, y1, marker="o", label="Upload (Kbps)")
    plt.plot(x, y2, marker="s", label="Download (Kbps)")
    plt.grid(True)
    plt.xlabel("Ukuran (MB)")
    plt.ylabel("Throughput (Kbps)")
    plt.title("Throughput Upload/Download 5–50 MB (Kbps)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300)

    print(f"📄 CSV siap: {CSV_FILE}")
    print(f"📊 Grafik siap: {PLOT_FILE}")


if __name__ == "__main__":
    main()
