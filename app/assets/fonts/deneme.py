import os
from kivy.core.text import LabelBase

# Font dosyasının tam yolu
font_path = "/Users/lara/Desktop/NEUAL-HELPPASS/assets/fonts/Poppins-Regular.ttf"

# Font dosyasının var olup olmadığını kontrol et
if os.path.exists(font_path):
    print(f"Font dosyası mevcut: {font_path}")
    LabelBase.register(name="Poppins", fn_regular=font_path)
else:
    print(f"Font dosyası bulunamadı: {font_path}")
