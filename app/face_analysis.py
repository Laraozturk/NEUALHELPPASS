import os
import cv2
import numpy as np
import time
from tensorflow.keras.models import load_model
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty
from kivy.clock import Clock

# Android işlemleri için (manuel butonlar için)
from plyer import sms, call

# 📍 Dosya yolları
BASE_DIR     = os.path.dirname(__file__)
MODEL_PATH   = os.path.join(BASE_DIR, 'models', 'emotion_model.h5')
CASCADE_PATH = os.path.join(BASE_DIR, 'data', 'haarcascade_frontalface_default.xml')

# 😶‍🌫️ Duygu etiketleri (modelinize göre ayarlayın)
EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

# 🎯 Yüklemeler
face_cascade  = cv2.CascadeClassifier(CASCADE_PATH)
emotion_model = load_model(MODEL_PATH, compile=False)

def analyze_face(image_path: str) -> int:
    """📊 Analiz kısmı (geliştirilmiş sürüm)"""
    img = cv2.imread(image_path)
    if img is None:
        print("❌ Görüntü okunamadı.")
        return 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        print("😐 Yüz algılanamadı.")
        return 0

    x, y, w, h = faces[0]
    roi = gray[y:y + h, x:x + w]
    roi = cv2.resize(roi, (64, 64)).astype("float32") / 255.0
    roi = np.expand_dims(roi, axis=0)       # (1, 64, 64)
    roi = np.expand_dims(roi, axis=-1)      # (1, 64, 64, 1)

    preds = emotion_model.predict(roi)[0]
    fear = float(preds[EMOTIONS.index("fear")])
    sad = float(preds[EMOTIONS.index("sad")])
    hazard = int((fear + sad) * 100)

    print(f"→ Fear: {fear:.2f}, Sad: {sad:.2f}, Hazard: %{hazard}")
    return hazard

class FifthScreen(Screen):
    hazard_status = NumericProperty(0)
    latitude = NumericProperty(0)
    longitude = NumericProperty(0)

    def on_pre_enter(self):
        Clock.schedule_once(lambda dt: self.capture_with_opencv(), 0.5)

    def capture_with_opencv(self):
        print("📸 OpenCV ile kamera açılıyor...")
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            print("❌ Kamera açılamadı!")
            return

        time.sleep(0.5)
        for _ in range(5): cam.read()  # ilk kareler siyah olabilir

        ret, frame = cam.read()
        if ret and frame is not None:
            photo_path = os.path.join(BASE_DIR, 'latest_face.jpg')
            cv2.imwrite(photo_path, frame)
            print(f"✅ Fotoğraf kaydedildi: {photo_path}")
            cam.release()

            self.hazard_status = analyze_face(photo_path)
            print(f"😨 Analiz sonucu: Tehlike seviyesi %{self.hazard_status}")

            if self.hazard_status >= 60:
                print("🚨 Acil durum! Yüzde 60 üzeri tehlike seviyesi.")
                self.latitude = 35.1856
                self.longitude = 33.3823
                location_link = f"https://maps.google.com/?q={self.latitude},{self.longitude}"

                try:
                    sms.send(
                        recipient='112',
                        message=f"Emergency! Danger level: %{self.hazard_status}\nLocation: {location_link}"
                    )
                    call.makecall(tel='112')
                    print("📲 SMS gönderildi ve arama başlatıldı.")
                except Exception as e:
                    print(f"⚠️ SMS/Call işlemi başarısız: {e}")

                App.get_running_app().root.current = "emergency"

            else:
                self.latitude = 35.1856
                self.longitude = 33.3823
                print(f"📍 Kıbrıs konumu gösteriliyor: ({self.latitude}, {self.longitude})")
                Clock.schedule_once(self._center_map, 0.5)
        else:
            print("⚠️ Görüntü alınamadı.")
            cam.release()

    def _center_map(self, *args):
        if 'mapview' in self.ids:
            print("🗺️ Harita Kıbrıs'a ortalanıyor...")
            self.ids.mapview.center_on(self.latitude, self.longitude)

    def manual_call_emergency(self):
        try:
            call.makecall(tel='112')
            print("📞 Manuel acil çağrı başlatıldı.")
        except Exception as e:
            print(f"❌ Arama başarısız: {e}")

    def manual_send_location(self):
        if self.latitude == 0 or self.longitude == 0:
            self.latitude = 35.1856
            self.longitude = 33.3823

        try:
            location_link = f"https://maps.google.com/?q={self.latitude},{self.longitude}"
            sms.send(
                recipient='112',
                message=f"Manual Emergency! Location: {location_link}"
            )
            print("📲 Manuel SMS gönderildi.")
        except Exception as e:
            print(f"❌ SMS gönderimi başarısız: {e}")