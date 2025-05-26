import requests
import json
import math
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy_garden.mapview import MapMarker, MapSource, MapView, MapLayer
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.clock import Clock

try:
    from plyer import gps
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False

# Harita karo kaynağı
GOOGLE_MAPS = MapSource(
    name="google",
    url="http://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    attribution="© Google",
    tile_size=256,
    image_ext="png"
)

# API URL'leri
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

class StreetLampManager:
    def __init__(self):
        self.street_lamps = []
        self.loaded = False
    
    def load_street_lamps_for_area(self, lat_min, lat_max, lon_min, lon_max):
        """Belirtilen alan için sokak lambası verilerini çek"""
        overpass_query = f"""
        [out:json][timeout:25];
        (
          node["highway"="street_lamp"]({lat_min},{lon_min},{lat_max},{lon_max});
          node["amenity"="lighting"]({lat_min},{lon_min},{lat_max},{lon_max});
          way["lit"="yes"]["highway"]({lat_min},{lon_min},{lat_max},{lon_max});
        );
        out geom;
        """
        
        try:
            response = requests.post(OVERPASS_URL, data=overpass_query, timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.street_lamps = []
                
                for element in data.get('elements', []):
                    if element['type'] == 'node':
                        self.street_lamps.append({
                            'lat': element['lat'],
                            'lon': element['lon'],
                            'type': element.get('tags', {}).get('highway', 'lighting')
                        })
                    elif element['type'] == 'way' and 'geometry' in element:
                        # Aydınlatmalı yolların geometrisini ekle
                        for coord in element['geometry']:
                            self.street_lamps.append({
                                'lat': coord['lat'],
                                'lon': coord['lon'],
                                'type': 'way_lighting'
                            })
                
                self.loaded = True
                print(f"Yüklenen sokak lambası sayısı: {len(self.street_lamps)}")
                return True
            else:
                print(f"Overpass API hatası: {response.status_code}")
                return False
        except Exception as e:
            print(f"Sokak lambası veri çekme hatası: {e}")
            return False
    
    def get_lamps_near_point(self, lat, lon, radius=0.001):
        """Belirtilen noktaya yakın sokak lambalarını getir"""
        nearby_lamps = []
        for lamp in self.street_lamps:
            distance = self.haversine_distance(lat, lon, lamp['lat'], lamp['lon'])
            if distance <= radius:
                nearby_lamps.append(lamp)
        return nearby_lamps
    
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """İki nokta arasındaki mesafeyi hesapla (km)"""
        R = 6371  # Dünya'nın yarıçapı (km)
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
            math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

class SafePolylineLayer(MapLayer):
    def __init__(self, coords, safety_scores=None, **kwargs):
        super().__init__(**kwargs)
        self.coords = coords
        self.safety_scores = safety_scores or []

    def reposition(self):
        mv: MapView = self.parent
        if not self.coords or not mv:
            return
        self.canvas.clear()
        
        with self.canvas:
            if self.safety_scores:
                # Güvenlik skoruna göre renk
                max_score = max(self.safety_scores) if self.safety_scores else 1
                for i, (lat, lon) in enumerate(self.coords[:-1]):
                    score = self.safety_scores[i] if i < len(self.safety_scores) else 0
                    normalized_score = score / max_score if max_score > 0 else 0
                    
                    # Yeşil (güvenli) -> Kırmızı (güvensiz)
                    Color(1 - normalized_score, normalized_score, 0, 1)
                    
                    x1, y1 = mv.get_window_xy_from(lat, lon, mv.zoom)
                    x2, y2 = mv.get_window_xy_from(self.coords[i+1][0], self.coords[i+1][1], mv.zoom)
                    Line(points=[x1, y1, x2, y2], width=4)
            else:
                # Varsayılan mavi renk
                Color(0, 0.6, 1, 1)
                pts = []
                for lat, lon in self.coords:
                    x, y = mv.get_window_xy_from(lat, lon, mv.zoom)
                    pts.extend([x, y])
                Line(points=pts, width=3)

class SeventhScreen(Screen):
    origin_text = StringProperty("")
    dest_text = StringProperty("")
    route_info = StringProperty("")
    loading_status = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gps_enabled = False
        self.current_lat = None
        self.current_lon = None
        self.lamp_manager = StreetLampManager()

    def on_pre_enter(self):
        mv: MapView = self.ids.map2
        mv.map_source = GOOGLE_MAPS
        mv.lat = 35.1856  # Lefkoşa koordinatları
        mv.lon = 33.3823
        mv.zoom = 12

        # Önceki işaretleri temizle
        for attr in ("origin_marker", "dest_marker", "polyline_layer"):
            w = getattr(self, attr, None)
            if w:
                mv.remove_widget(w)
            setattr(self, attr, None)
        
        self.origin_text = self.dest_text = self.route_info = self.loading_status = ""

        if GPS_AVAILABLE:
            self.start_gps()

        # Touch olaylarını bağla
        mv.unbind(on_touch_down=self._td, on_touch_move=self._tm, on_touch_up=self._tu)
        mv.bind(on_touch_down=self._td, on_touch_move=self._tm, on_touch_up=self._tu)

    def start_gps(self):
        if not GPS_AVAILABLE:
            print("GPS modülü bulunamadı")
            return
        try:
            gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
            gps.start(minTime=1000, minDistance=1)  # Daha sık güncelleme
            print("GPS başlatıldı")
        except Exception as e:
            print(f"GPS hatası: {e}")
            self.gps_enabled = False

    def on_gps_location(self, **kwargs):
        self.current_lat = kwargs.get('lat')
        self.current_lon = kwargs.get('lon')
        self.gps_enabled = True
        print(f"GPS konumu alındı: {self.current_lat:.6f}, {self.current_lon:.6f}")

    def on_gps_status(self, stype, status):
        print(f"GPS durumu: {stype} - {status}")
        if stype == 'provider-disabled':
            self.gps_enabled = False
            print("GPS devre dışı")
        elif stype == 'provider-enabled':
            self.gps_enabled = True
            print("GPS etkinleştirildi")

    def _td(self, mv, touch):
        # Sadece harita widget'ı içindeki touch'ları kabul et
        if mv.collide_point(*touch.pos):
            # Long press için zamanlayıcı başlat ama touch'ı consume etme
            touch.ud["map_touch"] = True
            touch.ud["start_pos"] = touch.pos[:]
            touch.ud["evt"] = Clock.schedule_once(lambda dt: self._manual_origin(mv, touch), 0.8)
        return False  # Touch'ı consume etme, harita da kullanabilsin

    def _tm(self, mv, touch):
        # Touch hareket ettirilirse long press iptal et
        if touch.ud.get("map_touch"):
            start_pos = touch.ud.get("start_pos", touch.pos)
            # Eğer touch pozisyonu çok değiştiyse (sürükleme) long press'i iptal et
            if abs(touch.pos[0] - start_pos[0]) > 10 or abs(touch.pos[1] - start_pos[1]) > 10:
                ev = touch.ud.get("evt")
                if ev: 
                    ev.cancel()
                    touch.ud["evt"] = None
                touch.ud["map_touch"] = False
        return False  # Touch'ı consume etme

    def _tu(self, mv, touch):
        # Touch bırakıldığında long press iptal et
        if touch.ud.get("map_touch"):
            ev = touch.ud.get("evt")
            if ev: 
                ev.cancel()
                touch.ud["evt"] = None
            touch.ud["map_touch"] = False
        return False  # Touch'ı consume etme

    def _manual_origin(self, mv, touch):
        # Long press sadece touch hareket etmemişse çalışsın
        if not touch.ud.get("map_touch"):
            return
            
        try:
            # Touch pozisyonunu MapView'ın yerel koordinat sistemine çevir
            local_x = touch.x - mv.x
            local_y = touch.y - mv.y
            
            # MapView'ın get_latlon_at metodunu doğru parametrelerle çağır
            lat, lon = mv.get_latlon_at(local_x, local_y, mv.zoom)
            
            if getattr(self, "origin_marker", None):
                mv.remove_widget(self.origin_marker)
                
            self.origin_marker = MapMarker(lat=lat, lon=lon, source="assets/images/location_on.png")
            mv.add_widget(self.origin_marker)
            self.origin_text = f"{lat:.6f}, {lon:.6f} (Manuel)"
            print(f"Manuel konum seçildi: Lat: {lat:.6f}, Lon: {lon:.6f}")
            
        except Exception as e:
            print(f"Manuel konum seçme hatası: {e}")
            # Hata durumunda harita merkezini kullan
            if getattr(self, "origin_marker", None):
                mv.remove_widget(self.origin_marker)
            self.origin_marker = MapMarker(lat=mv.lat, lon=mv.lon, source="assets/images/location_on.png")
            mv.add_widget(self.origin_marker)
            self.origin_text = f"{mv.lat:.6f}, {mv.lon:.6f} (Merkez)"

    def set_origin(self):
        mv = self.ids.map2
        if self.gps_enabled and self.current_lat and self.current_lon:
            lat, lon = self.current_lat, self.current_lon
            source_text = "(GPS)"
        else:
            lat = lon = None
            try:
                r = requests.get("https://ipinfo.io/json", timeout=5).json()
                loc = r.get("loc", "").split(",")
                if len(loc) == 2:
                    lat, lon = float(loc[0]), float(loc[1])
                    source_text = "(IP)"
                else:
                    raise ValueError("Geçersiz konum verisi")
            except Exception as e:
                print(f"Konum alma hatası: {e}")
                Popup(title="Hata", content=Label(text="Konum alınamadı"), 
                      size_hint=(None,None), size=(dp(250),dp(120))).open()
                return

        mv.center_on(lat, lon)
        if getattr(self, "origin_marker", None):
            mv.remove_widget(self.origin_marker)
        self.origin_marker = MapMarker(lat=lat, lon=lon, source="assets/images/location_on.png")
        mv.add_widget(self.origin_marker)
        self.origin_text = f"{lat:.6f}, {lon:.6f} {source_text}"

    def calculate_route_safety(self, coords):
        """Rota boyunca güvenlik skoru hesapla"""
        safety_scores = []
        lamp_radius = 0.0005  # ~50 metre
        
        for lat, lon in coords:
            nearby_lamps = self.lamp_manager.get_lamps_near_point(lat, lon, lamp_radius)
            safety_score = len(nearby_lamps)
            safety_scores.append(safety_score)
        
        return safety_scores

    def on_search(self):
        mv: MapView = self.ids.map2
        if not getattr(self, "origin_marker", None):
            Popup(title="Hata", content=Label(text="Önce konumunuzu ayarlayın"), 
                  size_hint=(None,None), size=(dp(250),dp(120))).open()
            return

        addr = self.ids.dest_input.text.strip()
        if not addr:
            Popup(title="Hata", content=Label(text="Hedef adres girin"), 
                  size_hint=(None,None), size=(dp(250),dp(120))).open()
            return

        # Nominatim ile adres arama (daha spesifik)
        search_params = {
            "q": f"{addr}, Lefkoşa, Kuzey Kıbrıs",
            "format": "json",
            "limit": 5,
            "countrycodes": "cy",
            "bounded": 1,
            "viewbox": "32.8,35.0,34.0,35.4"  # Kıbrıs sınırları
        }
        
        try:
            geo = requests.get(NOMINATIM_URL, params=search_params, 
                             headers={"User-Agent": "SafetyMapApp/1.0"}, timeout=10).json()
            
            if not geo:
                # Alternatif arama
                search_params["q"] = f"{addr}, Cyprus"
                geo = requests.get(NOMINATIM_URL, params=search_params, 
                                 headers={"User-Agent": "SafetyMapApp/1.0"}, timeout=10).json()
            
            if not geo:
                Popup(title="Hata", content=Label(text="Adres bulunamadı. Lütfen daha spesifik bir adres girin."), 
                      size_hint=(None,None), size=(dp(300),dp(120))).open()
                return

        except Exception as e:
            print(f"Adres arama hatası: {e}")
            Popup(title="Hata", content=Label(text="Adres arama sırasında hata oluştu"), 
                  size_hint=(None,None), size=(dp(300),dp(120))).open()
            return

        # En iyi sonucu seç
        best_result = geo[0]
        lat2, lon2 = float(best_result["lat"]), float(best_result["lon"])
        
        # Hedef marker'ı ekle
        if getattr(self, "dest_marker", None):
            mv.remove_widget(self.dest_marker)
        self.dest_marker = MapMarker(lat=lat2, lon=lon2, source="assets/images/locationred_on.png")
        mv.add_widget(self.dest_marker)
        mv.center_on(lat2, lon2)
        self.dest_text = f"{lat2:.6f}, {lon2:.6f}"

        # Sokak lambası verilerini yükle
        o = self.origin_marker
        lat_min = min(o.lat, lat2) - 0.01
        lat_max = max(o.lat, lat2) + 0.01
        lon_min = min(o.lon, lon2) - 0.01
        lon_max = max(o.lon, lon2) + 0.01
        
        self.loading_status = "Sokak lambası verileri yükleniyor..."
        print("Sokak lambası verileri yükleniyor...")
        if not self.lamp_manager.load_street_lamps_for_area(lat_min, lat_max, lon_min, lon_max):
            print("Sokak lambası verileri yüklenemedi, varsayılan rota gösterilecek")
            self.loading_status = "Varsayılan rota hesaplanıyor..."
        else:
            self.loading_status = "Güvenli rota hesaplanıyor..."

        # OSRM ile rota hesapla
        url = OSRM_URL.format(lon1=o.lon, lat1=o.lat, lon2=lon2, lat2=lat2)
        try:
            res = requests.get(url, params={
                "alternatives": "true",
                "overview": "full", 
                "geometries": "geojson",
                "annotations": "true"
            }, timeout=15).json()
            
            if res.get("code") != "Ok":
                Popup(title="Hata", content=Label(text="Rota hesaplanamadı"), 
                      size_hint=(None,None), size=(dp(250),dp(120))).open()
                return

        except Exception as e:
            print(f"Rota hesaplama hatası: {e}")
            Popup(title="Hata", content=Label(text="Rota hesaplama sırasında hata oluştu"), 
                  size_hint=(None,None), size=(dp(300),dp(120))).open()
            return

        # En güvenli rotayı seç
        best_route = None
        best_safety_score = -1
        
        for route in res["routes"]:
            coords = [(pt[1], pt[0]) for pt in route["geometry"]["coordinates"]]
            safety_scores = self.calculate_route_safety(coords)
            total_safety = sum(safety_scores)
            
            if total_safety > best_safety_score:
                best_safety_score = total_safety
                best_route = route
        
        if not best_route:
            best_route = res["routes"][0]  # Varsayılan rota
        
        coords = [(pt[1], pt[0]) for pt in best_route["geometry"]["coordinates"]]
        safety_scores = self.calculate_route_safety(coords)

        # Polyline ekle
        if getattr(self, "polyline_layer", None):
            mv.remove_widget(self.polyline_layer)
        self.polyline_layer = SafePolylineLayer(coords, safety_scores)
        mv.add_widget(self.polyline_layer)

        # Rota bilgisini güncelle
        leg = best_route["legs"][0]
        dur = round(leg["duration"]/60)
        dist = round(leg["distance"]/1000, 2)
        avg_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 0
        self.route_info = f"{dur} dk · {dist} km "
        self.loading_status = ""  # Loading durumunu temizle

        print(f"Rota hesaplandı: {dur} dk, {dist} km, Ortalama güvenlik: {avg_safety:.1f}")

    def zoom_map(self, mapview, direction):
        if direction == "in":
            mapview.zoom = min(18, mapview.zoom + 1)
        else:
            mapview.zoom = max(1, mapview.zoom - 1)

    def stop_gps(self):
        if GPS_AVAILABLE:
            try:
                gps.stop()
            except:
                pass