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

# 🎯 Yüklemeler (Error handling ile)
try:
    face_cascade  = cv2.CascadeClassifier(CASCADE_PATH)
    emotion_model = load_model(MODEL_PATH, compile=False)
    print("✅ Model ve cascade dosyaları yüklendi")
except Exception as e:
    print(f"❌ Model yükleme hatası: {e}")
    face_cascade = None
    emotion_model = None

def analyze_face(image_path: str) -> int:
    """📊 Analiz kısmı (Android uyumlu geliştirilmiş sürüm)"""
    try:
        # Model kontrolü
        if face_cascade is None or emotion_model is None:
            print("❌ Model dosyaları yüklenemedi - test modu")
            return 25  # Güvenli test değeri
        
        img = cv2.imread(image_path)
        if img is None:
            print("❌ Görüntü okunamadı.")
            return 25  # Güvenli değer

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 0:
            print("😐 Yüz algılanamadı.")
            return 25  # Güvenli değer

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
        
    except Exception as e:
        print(f"❌ Analiz hatası: {e}")
        return 25  # Güvenli değer

class FifthScreen(Screen):
    hazard_status = NumericProperty(0)
    latitude = NumericProperty(35.1856)  # Kıbrıs varsayılan koordinatları
    longitude = NumericProperty(33.3823)

    def on_pre_enter(self):
        Clock.schedule_once(lambda dt: self.capture_with_opencv(), 0.5)

    def capture_with_opencv(self):
        print("📸 OpenCV ile kamera açılıyor...")
        
        try:
            cam = cv2.VideoCapture(0)
            if not cam.isOpened():
                print("❌ Kamera açılamadı! Test modu etkin.")
                # Test için rastgele değer
                self.hazard_status = 35
                self.handle_analysis_result()
                return

            time.sleep(0.5)
            for _ in range(5): 
                cam.read()  # ilk kareler siyah olabilir

            ret, frame = cam.read()
            if ret and frame is not None:
                # ✅ Android uyumlu dosya yolu
                app = App.get_running_app()
                app_dir = app.user_data_dir
                photo_path = os.path.join(app_dir, 'latest_face.jpg')
                
                cv2.imwrite(photo_path, frame)
                print(f"✅ Fotoğraf kaydedildi: {photo_path}")
                cam.release()

                self.hazard_status = analyze_face(photo_path)
                print(f"😨 Analiz sonucu: Tehlike seviyesi %{self.hazard_status}")
                
                self.handle_analysis_result()
                
            else:
                print("⚠️ Görüntü alınamadı.")
                cam.release()
                # Test değeri atayıp devam et
                self.hazard_status = 30
                self.handle_analysis_result()
                
        except Exception as e:
            print(f"⚠️ Kamera genel hatası: {e}")
            # Test modu - güvenli değer
            self.hazard_status = 25
            self.handle_analysis_result()

    def handle_analysis_result(self):
        """Analiz sonucuna göre işlem yap"""
        try:
            if self.hazard_status >= 60:
                print("🚨 Acil durum! Yüzde 60 üzeri tehlike seviyesi.")
                self.trigger_emergency()
            else:
                print(f"📍 Normal durum - Kıbrıs konumu gösteriliyor: ({self.latitude}, {self.longitude})")
                Clock.schedule_once(self._center_map, 0.5)
        except Exception as e:
            print(f"❌ Sonuç işleme hatası: {e}")

    def trigger_emergency(self):
        """Acil durum tetikleme"""
        try:
            location_link = f"https://maps.google.com/?q={self.latitude},{self.longitude}"

            # SMS gönder
            try:
                sms.send(
                    recipient='112',
                    message=f"Emergency! Danger level: %{self.hazard_status}\nLocation: {location_link}"
                )
                print("📲 Acil SMS gönderildi.")
            except Exception as sms_error:
                print(f"⚠️ SMS gönderimi başarısız: {sms_error}")

            # Arama yap
            try:
                call.makecall(tel='112')
                print("📞 Acil arama başlatıldı.")
            except Exception as call_error:
                print(f"⚠️ Arama başarısız: {call_error}")

            # Acil durum ekranına geç
            App.get_running_app().root.current = "emergency"
            
        except Exception as e:
            print(f"❌ Acil durum işlemi genel hatası: {e}")

    def _center_map(self, *args):
        try:
            if 'mapview' in self.ids:
                print("🗺️ Harita Kıbrıs'a ortalanıyor...")
                self.ids.mapview.center_on(self.latitude, self.longitude)
        except Exception as e:
            print(f"⚠️ Harita ortalama hatası: {e}")

    def manual_call_emergency(self):
        try:
            call.makecall(tel='112')
            print("📞 Manuel acil çağrı başlatıldı.")
        except Exception as e:
            print(f"❌ Manuel arama başarısız: {e}")

    def manual_send_location(self):
        try:
            # Koordinat kontrolü
            if self.latitude == 0 or self.longitude == 0:
                self.latitude = 35.1856
                self.longitude = 33.3823

            location_link = f"https://maps.google.com/?q={self.latitude},{self.longitude}"
            sms.send(
                recipient='112',
                message=f"Manual Emergency! Location: {location_link}"
            )
            print("📲 Manuel SMS gönderildi.")
        except Exception as e:
            print(f"❌ Manuel SMS gönderimi başarısız: {e}")