import sqlite3
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapMarkerPopup, MapSource
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock
from functools import partial
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, Rectangle

from database import Database

# Google Maps karo kaynağı
google_maps = MapSource(
    name="google",
    url="http://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    attribution="© Google",
    tile_size=256,
    image_ext="png"
)

CYPRUS_LAT = 35.1856
CYPRUS_LON = 33.3823
DEFAULT_ZOOM = 10

class ScoreSystemScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Database()
        self.selected_rating = 0
        self.star_buttons = []
        self.existing_markers = []  # YENİ: Mevcut marker'ları takip et

    def on_pre_enter(self):
        map_widget = self.ids.get("map")
        if map_widget:
            # Google-benzeri harita karosu
            map_widget.map_source = google_maps
            # Kıbrıs'a odaklan
            map_widget.lat = CYPRUS_LAT
            map_widget.lon = CYPRUS_LON
            map_widget.zoom = DEFAULT_ZOOM

            # YENİ: Sayfa açıldığında tüm mevcut puanları göster
            self.load_all_existing_markers()

            # Uzun basma (long-press) algılaması için olayları bağla
            map_widget.unbind(
                on_touch_down=self._on_touch_down,
                on_touch_move=self._on_touch_move,
                on_touch_up=self._on_touch_up
            )
            map_widget.bind(
                on_touch_down=self._on_touch_down,
                on_touch_move=self._on_touch_move,
                on_touch_up=self._on_touch_up
            )

    def load_all_existing_markers(self):  # YENİ FONKSİYON
        """Veritabanındaki tüm puanları haritada göster"""
        map_widget = self.ids.get("map")
        if not map_widget:
            return
        
        # Önceki marker'ları temizle
        for marker in self.existing_markers:
            map_widget.remove_widget(marker)
        self.existing_markers.clear()
        
        # Tüm konumların ortalama puanlarını al
        all_scores = self.db.get_scores()
        
        for lat, lon, avg_score in all_scores:
            self.add_or_update_marker(lat, lon, avg_score, save_to_list=True)
        
        print(f"✅ {len(all_scores)} konum için marker'lar yüklendi")

    def _on_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            # 0.4 saniye sonra _trigger_popup çağrılsın
            touch.ud['lp_event'] = Clock.schedule_once(
                lambda dt: self._trigger_popup(instance, touch),
                0.4
            )
        return False

    def _on_touch_move(self, instance, touch):
        # Eğer hareket varsa (pinch/pan), long-press iptal et
        ev = touch.ud.get('lp_event')
        if ev:
            ev.cancel()
        return False

    def _on_touch_up(self, instance, touch):
        # Parmağı kaldırdığında da long-press iptal et
        ev = touch.ud.get('lp_event')
        if ev:
            ev.cancel()
        return False

    def _trigger_popup(self, instance, touch):
        # Uzun basma doğrulandı, haritada tıklanan koordinatları al
        lat, lon = instance.get_latlon_at(*touch.pos)
        self.show_star_rating_popup(lat, lon)

    def show_star_rating_popup(self, lat, lon):
        content = BoxLayout(
            orientation='vertical',
            padding=(20, 20, 20, 50),
            spacing=150,
            size_hint=(None, None) 
        )
        content.size = (Window.width * 0.8, Window.height * 0.6)
        with content.canvas.before:
            Color(0.5, 0, 0.5, 1)
            self.bg_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_bg, size=self._update_bg)

        # 1) Başlık
        title = Label(
            text="[b]RATE A PLACE[/b]",
            markup=True,
            font_size='30sp',
            size_hint=(1, None),
            height=50,
            halign='center',
            valign='middle'
        )
        title.bind(size=title.setter('text_size'))
        content.add_widget(title)

        # 2) Koordinatlar
        coords = Label(
            text=f"Lat: {lat:.4f}\nLon: {lon:.4f}",
            font_size='20sp',
            size_hint=(1, None),
            height=40,
            halign='center',
            valign='middle'
        )
        coords.bind(size=coords.setter('text_size'))
        content.add_widget(coords)

        # 3) Yıldız butonları
        stars = BoxLayout(
            orientation='horizontal',
            spacing=10,
            size_hint=(1, None),
            height=80
        )
        self.star_buttons.clear()
        for i in range(1, 6):
            btn = Button(
                size_hint=(None, None),
                size=(110, 110),
                background_normal="assets/images/stars.png",
                background_down="assets/images/stars-2.png",
                on_press=partial(self.on_star_press, i)
            )
            self.star_buttons.append(btn)
            stars.add_widget(btn)
        content.add_widget(stars)

        # 4) Durum etiketi
        self.status_label = Label(
            text="",
            markup=True,
            font_size='24sp',
            size_hint=(1, None),
            height=40,
            halign='center',
            valign='middle'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        content.add_widget(self.status_label)

        # 5) Tek tıkla kaydet ve kapat
        save = Button(
            text="Rate & Close",
            size_hint=(1, None),
            height=50,
            font_size='20sp'
        )
        content.add_widget(save)

        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        anchor.add_widget(content)
        popup = Popup(
            title="",
            content=anchor,
            size_hint=(None, None),
            size=(Window.width * 0.85, Window.height * 0.65),
            auto_dismiss=False
        )
        save.bind(on_release=lambda *a: self._do_save_and_close(lat, lon, popup))
        popup.open()

    def _update_bg(self, instance, _):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def on_star_press(self, rating, _):
        self.selected_rating = rating
        for idx, btn in enumerate(self.star_buttons, start=1):
            btn.background_normal = (
                "assets/images/stars-2.png" if idx <= rating else "assets/images/stars.png"
            )
        if rating >= 4:
            self.status_label.text = "[color=#00AA00]SAFE[/color]"
        elif rating <= 2:
            self.status_label.text = "[color=#AA0000]DANGER[/color]"
        else:
            self.status_label.text = "[color=#AAAA00]NORMAL[/color]"

    def _do_save_and_close(self, lat, lon, popup):
        popup.dismiss()
        
        # AKTİF KULLANICIYI AL
        app = App.get_running_app()
        user_info = app.session_manager.get_active_user()
        
        if user_info:
            user_id = user_info['id']
            score = self.selected_rating or 1
            self.db.save_score(user_id, lat, lon, score)
            avg = self.db.get_average_score(lat, lon)
            
            # YENİ: Marker'ı güncelle ve listeyi yenile
            self.refresh_marker_at_location(lat, lon, avg)
            
            print(f"✅ {score} points by user {user_id}")
        else:
            print("❌ No active users found!!")

    def refresh_marker_at_location(self, lat, lon, avg_score):  # YENİ FONKSİYON
        """Update marker in specific location"""
        map_w = self.ids.get("map")
        if not map_w:
            return
        
        # Aynı konumdaki eski marker'ı bul ve kaldır
        tolerance = 0.0001  # Koordinat toleransı
        for marker in self.existing_markers[:]:  # Liste kopyası ile iterate et
            if (abs(marker.lat - lat) < tolerance and abs(marker.lon - lon) < tolerance):
                map_w.remove_widget(marker)
                self.existing_markers.remove(marker)
                break
        
        # Yeni marker ekle
        self.add_or_update_marker(lat, lon, avg_score, save_to_list=True)

    def add_or_update_marker(self, lat, lon, avg_score, save_to_list=False):
        map_w = self.ids.get("map")
        if not map_w:
            return
            
        marker = LocationMarker(lat=lat, lon=lon)
        marker.size = (15, 15)  # Biraz daha büyük marker
        marker.size_hint = (None, None)
        marker.allow_stretch = True
        marker.keep_ratio = True
        
        # DOĞRU MARKER RESİMLERİ:
        if avg_score >= 4:
            marker.source = "assets/images/location_on.png"      # 🟢 YEŞİL - SAFE (4-5 puan)
        elif avg_score <= 2:
            marker.source = "assets/images/locationred_on.png"   # 🔴 KIRMIZI - DANGER (1-2 puan)
        else:
            marker.source = "assets/images/location.png"         # 🟠 TURUNCU - NORMAL (3 puan)

        marker.bind(on_release=lambda *a: self.show_marker_info(lat, lon))
        map_w.add_widget(marker)
        
        if save_to_list:
            self.existing_markers.append(marker)

    def show_marker_info(self, lat, lon):
        details = self.db.get_location_details(lat, lon)
        if details:
            total_ratings, avg_score, min_score, max_score = details
            
            # YENİ: Bu konuma puan veren kullanıcıların bilgilerini al
            individual_scores = self.get_location_user_details(lat, lon)
            
            box = BoxLayout(orientation='vertical', padding=20, spacing=15)
            
            # Genel bilgi
            info_text = f"""📊 Average Rating: {avg_score:.1f}/5
👥 Total Rating: {total_ratings}
📈 Lowest: {min_score} - Highest: {max_score}"""
            
            lbl = Label(text=info_text, font_size='16sp', halign='center')
            lbl.bind(size=lbl.setter('text_size'))
            box.add_widget(lbl)
            
            # YENİ: Kullanıcı detayları (son 3 puan)
            if individual_scores:
                user_info_text = "\n🔍 Recent Reviews:\n"
                for score_info in individual_scores[:3]:  # Son 3 puan
                    user_info_text += f"• User {score_info[0]}: {score_info[1]}⭐\n"
                
                user_lbl = Label(
                    text=user_info_text, 
                    font_size='14sp', 
                    halign='left',
                    color=(0.7, 0.7, 0.7, 1)
                )
                user_lbl.bind(size=user_lbl.setter('text_size'))
                box.add_widget(user_lbl)
            
            btn = Button(text="Close", size_hint=(1, None), height=40)
            pop = Popup(
                title="📍 Location Information",
                content=box,
                size_hint=(None, None),
                size=(Window.width * 0.8, Window.height * 0.5)  # Daha büyük popup
            )
            btn.bind(on_release=pop.dismiss)
            box.add_widget(btn)
            pop.open()

    def get_location_user_details(self, lat, lon):  # YENİ FONKSİYON
        """Bring the details of the users who rated this location"""
        try:
            self.db.cursor.execute("""
                SELECT u.id, s.score, s.created_at
                FROM security_scores s
                JOIN users u ON s.user_id = u.id
                WHERE s.lat = ? AND s.lon = ?
                ORDER BY s.created_at DESC
            """, (lat, lon))
            return self.db.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieveng user details: {e}")
            return []

class LocationMarker(MapMarkerPopup):
    pass
