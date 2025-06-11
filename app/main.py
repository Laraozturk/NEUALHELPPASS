import os
import sqlite3
from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.lang import Builder
from kivy.config import Config
from plyer import filechooser 
from kivy.uix.image import Image
from kivy.clock import Clock
from score_system import ScoreSystemScreen
from safety_map import SeventhScreen
from face_analysis import FifthScreen
from emergency_screen import EmergencyScreen
from session_manager import SessionManager  # YENİ IMPORT


# Ekran boyutu (iPhone 13 için)
Config.set('graphics', 'width', '390')
Config.set('graphics', 'height', '844')
Config.set('graphics', 'resizable', '0')  # Kullanıcı pencereyi değiştiremez

from kivy.core.window import Window
Window.size = (390, 844)

KV_FILE = os.path.join(os.path.dirname(__file__), "ui.kv")

try:
    Builder.load_file(KV_FILE)
    print(f"✅ KV dosyası başarıyla yüklendi: {KV_FILE}")
except Exception as e:
    print(f"❌ KV dosyası yüklenirken hata oluştu: {e}")

# Ana Sayfa
class MainScreen(Screen):
    pass


# Kullanıcı Girişi Sayfası
class SecondScreen(Screen):
    def login_user(self):
        id_number = self.ids.id_input.text
        password = self.ids.password_input.text
        birth_year = self.ids.birth_input.text
        phone_number = self.ids.phone_input.text

        if id_number and password and birth_year and phone_number:
            # Kullanıcıyı veritabanına kaydetme
            user_id = self.save_user_to_db(id_number, password, birth_year, phone_number)
            
            if user_id:
                # OTURUM OLUŞTUR
                app = App.get_running_app()
                app.session_manager.create_session(user_id)
                
                print("✅ Kullanıcı giriş yaptı!")
                self.clear_fields()
                # 📌 4. sayfaya yönlendirme
                self.manager.current = "fourth"
            else:
                print("❌ Kullanıcı kaydedilemedi!")
        else:
            print("⚠️ Lütfen tüm alanları doldurun!")

    def save_user_to_db(self, id_number, password, birth_year, phone_number):
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                id_number TEXT,
                password TEXT,
                birth_year TEXT,
                phone_number TEXT
            )
        """)
        
        try:
            cursor.execute("""
                INSERT INTO users (id_number, password, birth_year, phone_number)
                VALUES (?, ?, ?, ?)
            """, (id_number, password, birth_year, phone_number))
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except Exception as e:
            print(f"Veritabanı hatası: {e}")
            conn.close()
            return None

    def clear_fields(self):
        self.ids.id_input.text = ""
        self.ids.password_input.text = ""
        self.ids.birth_input.text = ""
        self.ids.phone_input.text = ""

# Hoş Geldiniz Sayfası
class ThirdScreen(Screen):
    pass

#  Dördüncü Sayfa (Face Analysis, Score System, Safety Map)
class FourthScreen(Screen):
    pass

# Beşinci Sayfa (Face Analysis)


# Yedinci Sayfa (Safety Map)
class WelcomeInfoScreen(Screen):
    pass

class FaceInfoScreen(Screen):
    pass

class ScoreInfoScreen(Screen):
    pass

class MapInfoScreen(Screen):
    pass

# Sekizinci Sayfa (Kullanıcı Profili ve Bilgileri)
class EighthScreen(Screen):
    def on_enter(self):
        """Sayfaya girildiğinde kullanıcı bilgilerini getirir"""
        self.load_user_info()

    def load_user_info(self):
        # OTURUM YÖNETİMİ İLE KULLANICI BİLGİSİ ALMA
        app = App.get_running_app()
        user_info = app.session_manager.get_active_user()
        
        if user_info:
            self.ids.profile_id.text = user_info['id_number']
            self.ids.profile_password.text = "******"
            self.ids.profile_birth.text = user_info['birth_year']
            self.ids.profile_phone.text = user_info['phone_number']
        else:
            print("❌ Kullanıcı bilgisi bulunamadı")

    def update_phone_number(self):
        new_phone = self.ids.profile_phone.text
        if new_phone:
            # OTURUM YÖNETİMİ İLE KULLANICI GÜNCELLEMESİ
            app = App.get_running_app()
            user_info = app.session_manager.get_active_user()
            
            if user_info:
                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET phone_number = ? WHERE id = ?", 
                             (new_phone, user_info['id']))
                conn.commit()
                conn.close()
                print("✅ Telefon numarası güncellendi!")
            else:
                print("❌ Kullanıcı bulunamadı!")
        else:
            print("⚠️ Lütfen geçerli bir telefon numarası girin!")

    def select_photo(self):
        try:
            from plyer import filechooser
            file_path = filechooser.open_file(title="Choose a profile picture", 
                                        filters=[("Image files", "*.png;*.jpg;*.jpeg")])
            if file_path and file_path[0]:
                self.update_photo(file_path[0])
        except Exception as e:
            print(f"Error selecting photo: {e}")
            self.ids.profile_image.source = "assets/images/default_profile.png"

    def update_photo(self, path):
        self.ids.profile_image.source = path
    
    # YENİ: ÇIKIŞ YAPMA FONKSİYONU
    def logout_user(self):
        """Kullanıcı çıkışı"""
        app = App.get_running_app()
        app.session_manager.logout_all_sessions()
        
        # Ana sayfaya yönlendir
        self.manager.current = "main"
        print("🚪 Çıkış yapıldı")

# Ekran Yönetimi
class MyScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(MainScreen(name="main"))
        self.add_widget(SecondScreen(name="second"))
        self.add_widget(ThirdScreen(name="third"))
        self.add_widget(FourthScreen(name="fourth"))
        self.add_widget(FifthScreen(name="fifth"))
        self.add_widget(ScoreSystemScreen(name="sixth"))
        self.add_widget(SeventhScreen(name="seventh"))
        self.add_widget(EighthScreen(name="eighth"))
        self.add_widget(EmergencyScreen(name="emergency"))
        self.add_widget(WelcomeInfoScreen(name="welcome_info"))
        self.add_widget(FaceInfoScreen(name="face_info"))
        self.add_widget(ScoreInfoScreen(name="score_info"))
        self.add_widget(MapInfoScreen(name="map_info"))
        
#  Ana Uygulama
class NEUALHELPPASSApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_manager = SessionManager()  # YENİ: Oturum yöneticisi
    
    def build(self):
        sm = MyScreenManager()
        
        # OTOMATIK GİRİŞ KONTROLÜ
        self.check_auto_login(sm)
        
        return sm
    
    def check_auto_login(self, screen_manager):
        """Uygulama açılırken otomatik giriş kontrolü"""
        if self.session_manager.is_user_logged_in():
            user_info = self.session_manager.get_active_user()
            print(f"✅ Otomatik giriş: {user_info['id_number']}")
            
            # Doğrudan 4. sayfaya yönlendir
            screen_manager.current = "fourth"
        else:
            print("🔐 Kullanıcı girişi gerekli")
            # Ana sayfada kal
            screen_manager.current = "main"

if __name__ == "__main__":
    NEUALHELPPASSApp().run()
