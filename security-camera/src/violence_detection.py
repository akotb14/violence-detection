import cv2
import numpy as np
from tensorflow.keras.models import load_model
import tensorflow as tf
# Load the pre-trained model
model = load_model('inception_resnet_model.h5')
class_label = ['non-violence' , 'violence']
# Function to preprocess frames
def preprocess_frame(frame):
    frame = cv2.resize(frame,(224,224))
    frame = np.array(frame) /255.0
    return frame

# Open video stream
cap = cv2.VideoCapture(1)  # 0 for default camera, or specify a video file
co=0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    if co >100:
        break
    co +=1
    # Preprocess frame
    processed_frame = preprocess_frame(frame)

    # Perform prediction
    prediction = model.predict(np.expand_dims(processed_frame, axis=0))
    print(prediction)
    print(class_label[np.argmax(prediction)])
    
    if(class_label[np.argmax(prediction)] == 'violence'):
        cv2.imwrite('vol' +str(co)+ '.jpeg',frame)
    cv2.imshow('Video Stream', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()