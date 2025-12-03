# ir_client_verbose.py
import requests, time, csv, sys
from collections import deque

URL = "http://10.218.161.39:5000/ir-test?cir_mbps=10&duration=30"  # ubah sesuai
OUT_CSV = "ir_client_verbose.csv"

def run(url):
    r = requests.get(url, stream=True, timeout=10)
    start = time.time()
    received = 0
    sec_start = start
    persec = []
    chunk_size = 1024
    try:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            now = time.time()
            received += len(chunk)
            # per-second accounting
            if now - sec_start >= 1.0:
                elapsed = now - sec_start
                mbps = (received*8) / (elapsed * 1024 * 1024)
                persec.append((int(sec_start-start)+1, mbps, received))
                print(f"sec {int(sec_start-start)+1:3d}: {mbps:.3f} Mbps ({received} bytes in {elapsed:.2f}s)")
                # reset per-second counters
                sec_start = now
                received = 0
    except Exception as e:
        print("Exception during streaming:", e)

    total_time = time.time() - start
    # compute overall received bytes from persec
    total_bits = sum([p[1] for p in persec]) * total_time * 1024*1024 / (1 if total_time==0 else total_time) # fallback
    # Save CSV
    with open(OUT_CSV, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["sec","mbps","cum_bytes"])
        for row in persec:
            wr.writerow(row)
    print("Saved per-second CSV to", OUT_CSV)

if __name__ == "__main__":
    run(URL)