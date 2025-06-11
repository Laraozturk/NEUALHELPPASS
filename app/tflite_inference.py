from jnius import autoclass, cast
import numpy as np

# Android asset erişimi için gerekli sınıflar
PythonActivity = autoclass('org.kivy.android.PythonActivity')
activity = PythonActivity.mActivity
AssetManager = activity.getAssets()

# TensorFlow Lite ile çalışma
Interpreter = autoclass('org.tensorflow.lite.Interpreter')
ByteBuffer = autoclass('java.nio.ByteBuffer')
ByteOrder = autoclass('java.nio.ByteOrder')
FileInputStream = autoclass('java.io.FileInputStream')
FileChannel = autoclass('java.nio.channels.FileChannel')

def load_tflite_model():
    try:
        fd = activity.getAssets().openFd("emotion_model.tflite")
        input_stream = FileInputStream(fd.getFileDescriptor())
        file_channel = input_stream.getChannel()
        start_offset = fd.getStartOffset()
        declared_length = fd.getDeclaredLength()
        model_buffer = file_channel.map(FileChannel.MapMode.READ_ONLY, start_offset, declared_length)
        interpreter = Interpreter(model_buffer)
        return interpreter
    except Exception as e:
        print(f"❌ Model yüklenemedi: {e}")
        return None

def run_tflite_inference(interpreter, input_data):
    try:
        input_array = np.array(input_data, dtype=np.float32).reshape(1, 64, 64, 1)
        input_buffer = ByteBuffer.allocateDirect(input_array.nbytes)
        input_buffer.order(ByteOrder.nativeOrder())
    
        for val in input_array.flatten():
            input_buffer.putFloat(val)

        output_buffer = ByteBuffer.allocateDirect(7 * 4)  # 7 sınıf x float32
        output_buffer.order(ByteOrder.nativeOrder())

        interpreter.run(input_buffer, output_buffer)
        output_buffer.rewind()

        result = []
        for _ in range(7):
            result.append(output_buffer.getFloat())

        return result
    except Exception as e:
        print(f"❌ İnferans başarısız: {e}")
        return []
