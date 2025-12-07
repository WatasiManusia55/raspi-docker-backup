import time
import requests
import csv
import matplotlib.pyplot as plt

BASE_URL = "https://pbl-tmj5a.siling-ai.my.id/qos"

# 50, 100, 150, ... 500
SAMPLE_SIZES = list(range(50, 501, 50))

SUMMARY_CSV = "qos_iplr_summary.csv"
PLOT_FILE = "qos_iplr.png"


def measure_iplr(n_requests: int):
    """
    Kirim n_requests ke BASE_URL.
    Kembalikan: N_sent, N_recv, lost, IPLR, IPLR_percent.
    """
    N_sent = n_requests
    N_recv = 0

    print(f"\n=== Pengukuran untuk N = {n_requests} ===")

    for i in range(1, n_requests + 1):
        try:
            t_start = time.perf_counter()
            resp = requests.get(BASE_URL, timeout=10)
            t_end = time.perf_counter()

            resp.raise_for_status()
            N_recv += 1
            rtt = (t_end - t_start) * 1000.0  # ms, opsional
            print(f"[N={n_requests} Req {i}] OK, RTT = {rtt:.2f} ms")
        except Exception as e:
            print(f"[N={n_requests} Req {i}] GAGAL: {e}")
            continue

        time.sleep(0.2)  # opsional

    lost = N_sent - N_recv
    IPLR = lost / N_sent
    IPLR_percent = IPLR * 100.0

    print(f">> N_sent = {N_sent}, N_recv = {N_recv}, lost = {lost}")
    print(f">> IPLR = {IPLR:.4f} ({IPLR_percent:.2f}%)")

    return N_sent, N_recv, lost, IPLR, IPLR_percent


def main():
    summary_rows = []

    for n in SAMPLE_SIZES:
        N_sent, N_recv, lost, IPLR, IPLR_percent = measure_iplr(n)
        summary_rows.append({
            "sample_size": n,
            "N_sent": N_sent,
            "N_recv": N_recv,
            "lost": lost,
            "IPLR": IPLR,
            "IPLR_percent": IPLR_percent
        })

    # ===== SIMPAN CSV =====
    if summary_rows:
        with open(SUMMARY_CSV, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["sample_size", "N_sent", "N_recv", "lost", "IPLR", "IPLR_percent"]
            )
            writer.writeheader()
            writer.writerows(summary_rows)

        print(f"\n✅ Summary IPLR disimpan ke: {SUMMARY_CSV}")
    else:
        print("\n❌ Tidak ada data IPLR untuk disimpan.")

    # ===== GRAFIK =====
    if summary_rows:
        summary_rows_sorted = sorted(summary_rows, key=lambda x: x["sample_size"])

        x = [row["sample_size"] for row in summary_rows_sorted]
        y = [row["IPLR_percent"] for row in summary_rows_sorted]

        plt.figure()
        plt.plot(x, y, marker="o")
        plt.xlabel("Jumlah request per sampel (N)")
        plt.ylabel("Packet Loss Ratio (IPLR) [%]")
        plt.title("Grafik Packet Loss Ratio (IPLR) vs Jumlah Request")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(PLOT_FILE, dpi=300)

        print(f"📊 Grafik IPLR disimpan ke: {PLOT_FILE}")
    else:
        print("❌ Tidak ada data untuk grafik IPLR.")


if __name__ == "__main__":
    main()
