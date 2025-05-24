import requests
import polyline
from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty
from kivy.properties import StringProperty
from kivy_garden.mapview import MapMarker, MapSource, MapView, MapLayer
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.clock import Clock

# Harita karo kaynağı (Google-benzeri)
GOOGLE_MAPS = MapSource(
    name="google",
    url="http://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    attribution="© Google",
    tile_size=256,
    image_ext="png"
)

# Geocoding ve routing uç noktaları
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL      = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"

class PolylineLayer(MapLayer):
    def __init__(self, coords, **kwargs):
        super().__init__(**kwargs)
        self.coords = coords

    def reposition(self):
        mv: MapView = self.parent
        if not self.coords or not mv:
            return
        self.canvas.clear()
        with self.canvas:
            Color(0, 0.6, 1, 1)  # Google mavi
            pts = []
            for lat, lon in self.coords:
                x, y = mv.get_window_xy_from(lat, lon, mv.zoom)
                pts.extend([x, y])
            Line(points=pts, width=3)

class SeventhScreen(Screen):
    origin_text = StringProperty("")
    dest_text   = StringProperty("")
    route_info  = StringProperty("")

    def on_pre_enter(self):
        mv: MapView = self.ids.map2
        mv.map_source = GOOGLE_MAPS
        # Kıbrıs'a odakla başlangıçta
        mv.lat = 35.1856
        mv.lon = 33.3823
        mv.zoom = 10

        # Önceki widget'ları temizle
        for attr in ("origin_marker", "dest_marker", "polyline_layer"):
            w = getattr(self, attr, None)
            if w:
                mv.remove_widget(w)
            setattr(self, attr, None)
        self.origin_text = self.dest_text = self.route_info = ""

        # Haritada uzun basma ile manuel konum seçimi
        mv.unbind(on_touch_down=self._td, on_touch_move=self._tm, on_touch_up=self._tu)
        mv.bind(on_touch_down=self._td, on_touch_move=self._tm, on_touch_up=self._tu)

    def _td(self, mv, touch):
        if mv.collide_point(*touch.pos):
            touch.ud["evt"] = Clock.schedule_once(lambda dt: self._manual_origin(mv, touch), 0.6)
        return False

    def _tm(self, mv, touch):
        ev = touch.ud.get("evt")
        if ev: ev.cancel()
        return False

    def _tu(self, mv, touch):
        ev = touch.ud.get("evt")
        if ev: ev.cancel()
        return False

    def _manual_origin(self, mv, touch):
        lat, lon = mv.get_latlon_at(*touch.pos)
        # varsa eski marker'ı sil
        if getattr(self, "origin_marker", None):
            mv.remove_widget(self.origin_marker)
        self.origin_marker = MapMarker(lat=lat, lon=lon, source="assets/images/location_on.png")
        mv.add_widget(self.origin_marker)
        mv.center_on(lat, lon)
        self.origin_text = f"{lat:.4f}, {lon:.4f}"

    def set_origin(self):
        """
        IP-based otomatik konum (ipinfo.io → ip-api.com fallback)
        """
        lat = lon = None
        # 1) ipinfo.io dene
        try:
            r = requests.get("https://ipinfo.io/json", timeout=3).json()
            loc = r.get("loc","").split(",")
            lat, lon = float(loc[0]), float(loc[1])
        except Exception:
            pass
        # 2) fallback ip-api.com
        if lat is None:
            try:
                r = requests.get("http://ip-api.com/json/", timeout=3).json()
                lat, lon = float(r["lat"]), float(r["lon"])
            except Exception:
                Popup(title="Hata",
                      content=Label(text="Konum alınamadı"),
                      size_hint=(None,None), size=(dp(200),dp(120))).open()
                return

        mv = self.ids.map2
        mv.center_on(lat, lon)
        if getattr(self, "origin_marker", None):
            mv.remove_widget(self.origin_marker)
        self.origin_marker = MapMarker(lat=lat, lon=lon, source="assets/images/location_on.png")
        mv.add_widget(self.origin_marker)
        self.origin_text = f"{lat:.4f}, {lon:.4f}"  

    def on_search(self):
        mv: MapView = self.ids.map2
        if not getattr(self, "origin_marker", None):
            Popup(title="Hata",
                  content=Label(text="Önce Konumunuzu ayarlayın"),
                  size_hint=(None,None), size=(dp(200),dp(120))).open()
            return

        addr = self.ids.dest_input.text.strip()
        if not addr:
            Popup(title="Hata",
                  content=Label(text="Adres girin"),
                  size_hint=(None,None), size=(dp(200),dp(120))).open()
            return

        # 1) Geocode
        geo = requests.get(
            NOMINATIM_URL,
            params={"q": addr, "format": "json", "limit": 1},
            headers={"User-Agent": "neual-helppass"}
        ).json()
        if not geo:
            Popup(title="Hata",
                  content=Label(text="Adres bulunamadı"),
                  size_hint=(None,None), size=(dp(200),dp(120))).open()
            return
        lat2, lon2 = float(geo[0]["lat"]), float(geo[0]["lon"])
        mv.center_on(lat2, lon2)

        # 2) Hedef marker
        if getattr(self, "dest_marker", None):
            mv.remove_widget(self.dest_marker)
        self.dest_marker = MapMarker(lat=lat2, lon=lon2, source="assets/images/locationred_on.png")
        mv.add_widget(self.dest_marker)
        self.dest_text = f"{lat2:.4f}, {lon2:.4f}"

        # 3) OSRM rotası
        o = self.origin_marker
        url = OSRM_URL.format(lon1=o.lon, lat1=o.lat, lon2=lon2, lat2=lat2)
        res = requests.get(url, params={"overview":"full","geometries":"geojson"}).json()
        if res.get("code") != "Ok":
            Popup(title="Hata",
                  content=Label(text="Rota alınamadı"),
                  size_hint=(None,None), size=(dp(200),dp(120))).open()
            return

        # 4) Çizim
        coords = [(pt[1], pt[0]) for pt in res["routes"][0]["geometry"]["coordinates"]]
        if getattr(self, "polyline_layer", None):
            mv.remove_widget(self.polyline_layer)
        self.polyline_layer = PolylineLayer(coords)
        mv.add_widget(self.polyline_layer)

        # 5) Mesafe / süre
        leg = res["routes"][0]["legs"][0]
        dur = round(leg["duration"]/60)
        dist = round(leg["distance"]/1000, 2)
        self.route_info = f"{dur} dk · {dist} km"

    def zoom_map(self, mapview, direction):
        if direction == "in":
            mapview.zoom += 1
        else:
            mapview.zoom = max(1, mapview.zoom - 1)