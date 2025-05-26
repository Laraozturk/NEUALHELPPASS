import tensorflow as tf

# Girdi dosyasının yolu
h5_model_path = "app/models/emotion_model.h5"

# Çıktı dosyasının yolu
tflite_model_path = "assets/emotion_model.tflite"

# Modeli yükle
model = tf.keras.models.load_model(h5_model_path, compile=False)

# TFLite dönüştürücü ile dönüştür
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Dosyayı yaz
with open(tflite_model_path, 'wb') as f:
    f.write(tflite_model)

print("✅ .tflite modeli başarıyla oluşturuldu:", tflite_model_path)
