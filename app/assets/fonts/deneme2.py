from kivy.app import App
from kivy.uix.label import Label
from kivy.core.text import LabelBase
from kivy.lang import Builder

# Font dosyasının kaydını yapıyoruz
font_path = "/Users/lara/Desktop/NEUAL-HELPPASS/assets/fonts/Poppins-Regular.ttf"
LabelBase.register(name="Poppins", fn_regular=font_path)

class TestApp(App):
    def build(self):
        # Fontu uygulamada kullanıyoruz
        label = Label(text="Hello, this is Poppins font!", font_name="Poppins")
        return label

if __name__ == "__main__":
    TestApp().run()
