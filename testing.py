import adafruit_dht
import board
import time

dhtDevice = adafruit_dht.DHT22(board.D4)

while True:
    try:
        temperature = dhtDevice.temperature
        humidity = dhtDevice.humidity
        print(f"Suhu: {temperature} C, Kelembaban: {humidity}%")
    except Exception as e:
        print("Error:", e)
    time.sleep(2)
