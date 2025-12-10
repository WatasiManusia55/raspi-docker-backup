import graphviz

# Inisialisasi graph
dot = graphviz.Digraph(
    comment='ERD Sistem Deteksi Nyamuk', 
    graph_attr={'rankdir': 'LR', 'splines': 'ortho'} # Mengatur arah L-R dan garis lurus
)

# 1. Definisikan Entitas (Nodes)
# Menggunakan format kotak tabel untuk representasi yang jelas
dot.node('A', 'Sensor_Types', shape='box')
dot.node('B', 'Sensor_Data', shape='box')
dot.node('C', 'Notifications', shape='box')
dot.node('D', 'Jentik_Detections', shape='box')

# 2. Definisikan Relasi (Edges)

# Sensor_Types (1) ──< Sensor_Data (N)
# Menggunakan crow's foot notation (simulasi 1:N)
dot.edge('A', 'B', label='mengandung', headlabel='>', taillabel='1')

# Sensor_Data (1) ──< Notifications (N)
# Asumsi 1:N dari Data ke Notifikasi
dot.edge('B', 'C', label='memicu', headlabel='>', taillabel='1')

# Jentik_Detections (1) ──< Notifications (N)
# Asumsi 1:N dari Deteksi ke Notifikasi (Deteksi tunggal dapat memicu banyak notif)
dot.edge('D', 'C', label='berdasarkan', headlabel='>', taillabel='1')

# (Relasi langsung yang Anda tulis)
# Jentik_Detections (1) ──< Notifications (N)
# Sensor_Data (N) ──> Notifications (N) 
# Note: Dua relasi di atas menunjukkan bahwa Notifications punya dua Foreign Key.
# Dalam DOT, kita hanya perlu mendefinisikan panah yang sesuai.

# Render dan simpan file
dot.render('erd_nyamuk', view=True, format='png') 

print("Gambar ERD telah dibuat dan disimpan sebagai 'erd_nyamuk.png'.")