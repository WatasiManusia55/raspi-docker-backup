import time
import requests
import csv
import matplotlib.pyplot as plt

BASE_URL = "https://pbl-tmj5a.siling-ai.my.id/qos"  # endpoint ringan

# 10, 20, 30, ... 200  -> 20 sampel
SAMPLE_SIZES = list(range(10, 201, 10))

RAW_CSV = "qos_raw.csv"
SUMMARY_CSV = "qos_summary.csv"
PLOT_FILE = "qos_rtt_iptd.png"


def measure_once(n_requests: int):
    """
    Mengirim n_requests ke BASE_URL,
    mengembalikan list RTT dan IPTD~ (dalam detik).
    """
    rtt_list = []
    iptd_list = []

    print(f"\n=== Mulai pengukuran untuk N = {n_requests} ===")

    for i in range(1, n_requests + 1):
        try:
            t_start = time.perf_counter()
            resp = requests.get(BASE_URL, timeout=10)
            t_end = time.perf_counter()
            resp.raise_for_status()
        except Exception as e:
            print(f"[N={n_requests} Req {i}] GAGAL: {e}")
            continue

        rtt = t_end - t_start        # detik
        iptd_approx = rtt / 2.0      # detik (aproksimasi)

        rtt_list.append(rtt)
        iptd_list.append(iptd_approx)

        print(f"[N={n_requests} Req {i}] RTT  = {rtt*1000:.2f} ms "
              f"| IPTD~ ≈ {iptd_approx*1000:.2f} ms")

        time.sleep(0.2)  # jeda antar request (opsional)

    return rtt_list, iptd_list


def main():
    all_raw_rows = []     # Untuk qos_raw.csv
    summary_rows = []     # Untuk qos_summary.csv

    for n in SAMPLE_SIZES:
        rtt_list, iptd_list = measure_once(n)

        if not rtt_list:
            print(f"⚠ Tidak ada request sukses untuk N={n}, lewati.")
            continue

        avg_rtt = sum(rtt_list) / len(rtt_list)
        avg_iptd = sum(iptd_list) / len(iptd_list)

        print(f"\n>> RINGKAS N={n}: "
              f"avg RTT={avg_rtt*1000:.2f} ms, avg IPTD~={avg_iptd*1000:.2f} ms")

        # Simpan raw
        for i, (rtt, iptd) in enumerate(zip(rtt_list, iptd_list), start=1):
            all_raw_rows.append({
                "sample_size": n,
                "req_index": i,
                "rtt_ms": rtt * 1000.0,
                "iptd_ms": iptd * 1000.0,
            })

        # Simpan summary per-N
        summary_rows.append({
            "sample_size": n,
            "num_success": len(rtt_list),
            "avg_rtt_ms": avg_rtt * 1000.0,
            "avg_iptd_ms": avg_iptd * 1000.0,
        })

    # ========== Tulis CSV RAW ==========
    if all_raw_rows:
        with open(RAW_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sample_size", "req_index", "rtt_ms", "iptd_ms"])
            writer.writeheader()
            writer.writerows(all_raw_rows)
        print(f"\n✅ Raw data disimpan ke: {RAW_CSV}")
    else:
        print("\n❌ Tidak ada raw data untuk disimpan.")

    # ========== Tulis CSV SUMMARY ==========
    if summary_rows:
        with open(SUMMARY_CSV, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["sample_size", "num_success", "avg_rtt_ms", "avg_iptd_ms"]
            )
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"✅ Summary data disimpan ke: {SUMMARY_CSV}")
    else:
        print("❌ Tidak ada summary data untuk disimpan.")

    # ========== Bikin Grafik ==========
    if summary_rows:
        # Urutkan berdasarkan sample_size biar rapi
        summary_rows_sorted = sorted(summary_rows, key=lambda x: x["sample_size"])

        x = [row["sample_size"] for row in summary_rows_sorted]
        y_rtt = [row["avg_rtt_ms"] for row in summary_rows_sorted]
        y_iptd = [row["avg_iptd_ms"] for row in summary_rows_sorted]

        plt.figure()
        plt.plot(x, y_rtt, marker="o", label="Rata-rata RTT (ms)")
        plt.plot(x, y_iptd, marker="s", label="Rata-rata IPTD~ (ms)")
        plt.xlabel("Jumlah request (N) per sampel")
        plt.ylabel("Waktu (ms)")
        plt.title("Rata-rata RTT & IPTD~ vs Jumlah Request per Sampel")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(PLOT_FILE, dpi=300)

        print(f"📊 Grafik disimpan ke: {PLOT_FILE}")
    else:
        print("❌ Tidak ada data summary, grafik tidak dibuat.")


if __name__ == "__main__":
    main()
