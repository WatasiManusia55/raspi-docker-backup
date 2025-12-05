import requests, time

url = "http://10.218.161.39:5000/ir-test?cir_mbps=10&duration=30"
start = time.time()
received = 0

for chunk in requests.get(url, stream=True).iter_content(chunk_size=1024):
    received += len(chunk)

end = time.time()
duration = end - start
ir_mbps = (received * 8) / (duration * 1024 * 1024)

print(f"CIR target : 10 Mbps")
print(f"IR received: {ir_mbps:.2f} Mbps")
# print("PASS" if ir_mbps >= 10 * 0.95 else "FAIL")
