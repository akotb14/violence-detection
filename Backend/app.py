# from flask import Flask, render_template
# from flask import Flask, request, jsonify
# from flask_socketio import SocketIO, emit
# from werkzeug.utils import secure_filename
# import os
# import tensorflow as tf
# from tensorflow import keras
# from tensorflow.keras.preprocessing import image
# from tensorflow.keras.applications.densenet import preprocess_input, decode_predictions

# app = Flask(__name__)
# socketio = SocketIO(app, cors_allowed_origins="*")

# # Specify the folder where uploaded images will be stored
# UPLOAD_FOLDER = 'uploads'
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def classify_image(file_path):
#     # Load your trained model
#     model = keras.models.load_model(r'D:\scu\security-camera\src\inception_resnet_model.h5')

#     # Load and preprocess the image
#     img = image.load_img(file_path, target_size=(224, 224))
#     img_array = image.img_to_array(img)
#     img_array = preprocess_input(img_array)
#     img_array = tf.expand_dims(img_array, 0)  # Create a batch

#     # Make predictions
#     predictions = model.predict(img_array)

#     # Assuming your model outputs probabilities for binary classification
#     probability = predictions[0][0]

#     # Classify as violence if the probability is above a certain threshold (adjust as needed)
#     threshold = 0.5
#     result = 'Violence' if probability > threshold else 'Non-Violence'

#     return result

# @app.route('/')
# def index():
#     return render_template('index.html')


# @app.route('/upload', methods=['POST'])
# def upload_file():
#     # Check if the POST request has the file part
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'})

#     file = request.files['file']

#     # If the user does not select a file, the browser submits an empty file without a filename
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'})

#     if file and allowed_file(file.filename):
#         filename = secure_filename(file.filename)
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(file_path)

#         # Now you can send the image to your machine learning model for processing
#         # Replace the following line with code to invoke your model
#         result = classify_image(file_path)

#         return jsonify({'result': result})

#     return jsonify({'error': 'File not allowed'})

# @socketio.on('image_upload')
# def handle_image_upload(data):
#     file_data = data['file']
#     filename = secure_filename(file_data['filename'])
#     file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#     with open(file_path, 'wb') as f:
#         f.write(file_data['content'])

#     # Now you can send the image to your machine learning model for processing
#     result = classify_image(file_path)

#     emit('result', {'result': result})
#     print('result:', result)
#     return jsonify({'result': result})

# # if __name__ == '__main__':
# #     app.run(debug=True)
    
# if __name__ == '__main__':
#     socketio.run(app, debug=True)

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.densenet import preprocess_input, decode_predictions

app = Flask(__name__)

# Specify the folder where uploaded images will be stored
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
model = keras.models.load_model(r'D:\scu\security-camera\src\inception_resnet_model.h5')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def classify_image(file_path):
    # Load your trained model
    class_label = ['non-violence' , 'violence']
    # Load and preprocess the image
    img = image.load_img(file_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = preprocess_input(img_array)
    img_array = tf.expand_dims(img_array, 0)  # Create a batch

    # Make predictions
    predictions = model.predict(img_array)

    # Assuming your model outputs probabilities for binary classification
    # probability = predictions[0][0]
        
    # # Classify as violence if the probability is above a certain threshold (adjust as needed)
    # threshold = 0.5
    result = class_label[np.argmax(predictions)]

    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the POST request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    # If the user does not select a file, the browser submits an empty file without a filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Now you can send the image to your machine learning model for processing
        result = classify_image(file_path)

        return jsonify({'result': result})

    return jsonify({'error': 'File not allowed'})

if __name__ == '__main__':
    app.run(debug=True)
