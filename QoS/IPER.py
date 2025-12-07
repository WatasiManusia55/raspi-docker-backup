import time
import requests
import csv
import matplotlib.pyplot as plt

BASE_URL = "https://pbl-tmj5a.siling-ai.my.id/qos"

# 50, 100, 150, ... 500
SAMPLE_SIZES = list(range(50, 501, 50))

SUMMARY_CSV = "qos_iper_summary.csv"
PLOT_FILE = "qos_iper.png"


def measure_iper(n_requests: int):
    """
    Kirim n_requests ke BASE_URL.
    Hitung N_delivered, N_error, dan IPER.
    """
    N_sent = n_requests
    N_recv = 0
    N_delivered = 0
    N_error = 0

    print(f"\n=== Pengukuran IPER untuk N = {n_requests} ===")

    for i in range(1, n_requests + 1):
        try:
            resp = requests.get(BASE_URL, timeout=10)
        except Exception as e:
            print(f"[N={n_requests} Req {i}] GAGAL (loss): {e}")
            continue

        if resp.status_code != 200:
            print(f"[N={n_requests} Req {i}] HTTP ERROR {resp.status_code}")
            continue

        N_recv += 1

        # cek isi JSON
        try:
            data = resp.json()
        except Exception as e:
            print(f"[N={n_requests} Req {i}] ERROR parse JSON: {e}")
            N_error += 1
            continue

        status_val = data.get("status", None)

        if status_val == "ok":
            N_delivered += 1
            print(f"[N={n_requests} Req {i}] OK")
        else:
            N_error += 1
            print(f"[N={n_requests} Req {i}] ERROR: status={status_val}")

        time.sleep(0.1)  # opsional

    # Hitung IPER
    denom = N_delivered + N_error
    if denom > 0:
        IPER = N_error / denom
    else:
        IPER = 0.0
    IPER_percent = IPER * 100.0

    print(f">> N_sent      = {N_sent}")
    print(f">> N_recv      = {N_recv}")
    print(f">> N_delivered = {N_delivered}")
    print(f">> N_error     = {N_error}")
    print(f">> IPER        = {IPER:.6f} ({IPER_percent:.4f}%)")

    return {
        "sample_size": n_requests,
        "N_sent": N_sent,
        "N_recv": N_recv,
        "N_delivered": N_delivered,
        "N_error": N_error,
        "IPER": IPER,
        "IPER_percent": IPER_percent,
    }


def main():
    summary_rows = []

    for n in SAMPLE_SIZES:
        row = measure_iper(n)
        summary_rows.append(row)

    # ===== Simpan ke CSV =====
    if summary_rows:
        with open(SUMMARY_CSV, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "sample_size", "N_sent", "N_recv",
                    "N_delivered", "N_error",
                    "IPER", "IPER_percent"
                ]
            )
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"\n✅ Summary IPER disimpan ke: {SUMMARY_CSV}")
    else:
        print("\n❌ Tidak ada data IPER untuk disimpan.")

    # ===== Grafik IPER (%) vs N =====
    if summary_rows:
        summary_rows_sorted = sorted(summary_rows, key=lambda x: x["sample_size"])
        x = [row["sample_size"] for row in summary_rows_sorted]
        y = [row["IPER_percent"] for row in summary_rows_sorted]

        plt.figure()
        plt.plot(x, y, marker="o")
        plt.xlabel("Jumlah request per sampel (N)")
        plt.ylabel("Packet Error Ratio (IPER) [%]")
        plt.title("Grafik Packet Error Ratio (IPER) vs Jumlah Request")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(PLOT_FILE, dpi=300)

        print(f"📊 Grafik IPER disimpan ke: {PLOT_FILE}")
    else:
        print("❌ Tidak ada data untuk grafik IPER.")


if __name__ == "__main__":
    main()
