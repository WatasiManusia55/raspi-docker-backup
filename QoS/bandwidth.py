import speedtest
import datetime

def uji_bandwidth():
    """Melakukan uji bandwidth menggunakan speedtest-cli."""
    print("🚀 Memulai pengujian bandwidth...")
    print("-" * 30)

    try:
        # Inisialisasi objek Speedtest
        st = speedtest.Speedtest()

        # Pilih server terdekat secara otomatis
        print("🌍 Mencari server terbaik...")
        st.get_best_server()
        
        server_info = st.best
        print(f"✅ Server terpilih: {server_info['host']} ({server_info['name']})")
        print(f"   Lokasi: {server_info['country']}, Jarak: {server_info['d']} km")
        print("-" * 30)

        # Uji kecepatan unduh (Download)
        print("⬇️ Menguji kecepatan Unduh (Download)...")
        # Kecepatan dikembalikan dalam bit/detik, dibagi 10^6 untuk mendapatkan Mbps
        unduh_speed = st.download() / 10**6 
        print(f"**Kecepatan Unduh:** {unduh_speed:.2f} Mbps")
        print("-" * 30)

        # Uji kecepatan unggah (Upload)
        print("⬆️ Menguji kecepatan Unggah (Upload)...")
        unggah_speed = st.upload() / 10**6
        print(f"**Kecepatan Unggah:** {unggah_speed:.2f} Mbps")
        print("-" * 30)

        # Uji Latency (Ping)
        # Latency diambil dari info server terbaik
        latency = server_info['latency']
        print(f"⏱️ **Latensi (Ping):** {latency:.2f} ms")
        print("-" * 30)

        # Ringkasan Hasil
        print("🎉 **RINGKASAN HASIL UJI BANDWIDTH**")
        print(f"Waktu Pengujian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Download: {unduh_speed:.2f} Mbps")
        print(f"Upload: {unggah_speed:.2f} Mbps")
        print(f"Latency: {latency:.2f} ms")

    except speedtest.ConfigRetrievalError:
        print("❌ ERROR: Gagal mengambil konfigurasi server speedtest. Pastikan koneksi internet Anda aktif.")
    except Exception as e:
        print(f"❌ ERROR: Terjadi kesalahan: {e}")

# Jalankan fungsi utama
if __name__ == "__main__":
    uji_bandwidth()