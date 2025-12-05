# button_simulator.py
import cv2
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import json
from datetime import datetime

class CameraButtonSimulator:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Ambil Jentik - Latency Test")
        self.window.geometry("800x600")
        
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.latency_data = []
        self.test_count = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup user interface"""
        # Frame untuk video
        self.video_frame = ttk.Frame(self.window)
        self.video_frame.pack(pady=10)
        
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack()
        
        # Tombol capture
        self.capture_btn = ttk.Button(
            self.window, 
            text="📸 AMBIL JENTIK", 
            command=self.capture_image,
            style="Accent.TButton"
        )
        self.capture_btn.pack(pady=20)
        
        # Label status
        self.status_label = ttk.Label(
            self.window, 
            text="Tekan tombol untuk mengambil gambar",
            font=("Arial", 12)
        )
        self.status_label.pack()
        
        # Frame untuk hasil
        self.result_frame = ttk.Frame(self.window)
        self.result_frame.pack(pady=10)
        
        self.result_label = ttk.Label(
            self.result_frame,
            text="",
            font=("Arial", 10)
        )
        self.result_label.pack()
        
        # Styling
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 14, "bold"), padding=20)
        
    def update_video(self):
        """Update video feed"""
        ret, frame = self.cap.read()
        if ret:
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            img = Image.fromarray(rgb_frame)
            img = img.resize((640, 480), Image.Resampling.LANCZOS)
            
            # Convert to ImageTk
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Update label
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
        
        # Schedule next update
        self.window.after(10, self.update_video)
    
    def capture_image(self):
        """Handle button click event"""
        self.test_count += 1
        
        # Start timer
        start_time = time.perf_counter()
        
        # Update status
        self.status_label.config(text="📸 Mengambil gambar...")
        self.capture_btn.config(state="disabled")
        
        # Capture in thread
        thread = threading.Thread(target=self._capture_thread, args=(start_time,))
        thread.start()
    
    def _capture_thread(self, start_time):
        """Thread untuk capture gambar"""
        # Capture frame
        ret, frame = self.cap.read()
        
        if ret:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{self.test_count}_{timestamp}.jpg"
            
            # Save image
            cv2.imwrite(filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Calculate latency
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            
            # Update UI in main thread
            self.window.after(0, self._update_results, latency_ms, filename)
        
    def _update_results(self, latency_ms, filename):
        """Update UI dengan hasil"""
        self.latency_data.append({
            'test': self.test_count,
            'latency_ms': round(latency_ms, 2),
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update status
        self.status_label.config(text="✅ Gambar berhasil diambil!")
        self.result_label.config(
            text=f"Test #{self.test_count}: {latency_ms:.1f} ms\nFile: {filename}"
        )
        
        # Enable button
        self.capture_btn.config(state="normal")
        
        # Auto-save results setiap 5 test
        if self.test_count % 5 == 0:
            self.save_results()
    
    def save_results(self):
        """Save latency data to file"""
        with open("button_latency_results.json", "w") as f:
            json.dump(self.latency_data, f, indent=2)
        
        print(f"✅ Saved {len(self.latency_data)} test results")
    
    def run(self):
        """Run the application"""
        self.update_video()
        self.window.mainloop()
        
        # Cleanup
        self.cap.release()
        self.save_results()

if __name__ == "__main__":
    app = CameraButtonSimulator()
    app.run()