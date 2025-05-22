import tensorflow as tf

# .h5 model yolu
keras_model_path = "models/emotion_model.h5"
# Kaydedilecek .tflite model yolu
tflite_model_path = "models/emotion_model.tflite"

# .h5 modelini yükle
model = tf.keras.models.load_model(keras_model_path)

# TFLite converter ile çevir
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# .tflite olarak kaydet
with open(tflite_model_path, "wb") as f:
    f.write(tflite_model)

print(f"✅ Dönüştürüldü: {tflite_model_path}")
