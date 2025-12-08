import cv2

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
print("Open V4L2 =", cap.isOpened())

cap2 = cv2.VideoCapture(0)
print("Open default =", cap2.isOpened())
