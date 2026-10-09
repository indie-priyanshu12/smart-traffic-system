===================================================================
  UPLOAD YOUR CAR IMAGES HERE
===================================================================

1. Drop/paste all your car photos directly into this folder:
   c:\Users\utkar\Documents\WORKSPACE\smart-traffic-system\my_car_images

   Supported formats: .jpg, .jpeg, .png, .webp

2. Tips for best accuracy:
   - 20 to 50 photos is ideal.
   - Include different angles (front, back, sides, 45-degree angle, top).
   - Include different distances (close-up, medium).
   - Include the lighting where you will test the car.

3. Once your photos are in this folder, run:
   py -3.12 python_vision/label_uploaded_images.py
   (or double-click python_vision/label_and_train.bat)

   It will automatically box your car, split into train/val,
   and train your model on your NVIDIA RTX 3050 GPU!
===================================================================
