"""
Custom YOLOv8 Model Trainer for Your Specific Car / Vehicle Model.
Trains a high-accuracy custom YOLO detector using the images collected with capture_dataset.py.
"""

import os
import sys
import shutil
import yaml

def train():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(base_dir, "dataset")
    train_img_dir = os.path.join(dataset_dir, "images", "train")
    val_img_dir = os.path.join(dataset_dir, "images", "val")

    # 1. Check if dataset exists and has samples
    train_images = [f for f in os.listdir(train_img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))] if os.path.exists(train_img_dir) else []
    val_images = [f for f in os.listdir(val_img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))] if os.path.exists(val_img_dir) else []
    total_images = len(train_images) + len(val_images)

    if total_images < 10:
        print("\n[ERROR] Not enough dataset samples found!")
        print(f"  Current samples: {total_images} (Need at least 15-30 for good accuracy)")
        print("  Please first run: python capture_dataset.py\n")
        return

    print("==============================================================")
    print("   Starting YOLOv8 Custom Car Model Training")
    print("==============================================================")
    print(f"  Training samples:   {len(train_images)}")
    print(f"  Validation samples: {len(val_images)}")
    print(f"  Base Model:         yolov8n.pt (Transfer Learning)")
    print("==============================================================\n")

    # 2. Write dataset.yaml configuration file
    dataset_yaml_path = os.path.join(base_dir, "dataset.yaml")
    # Use forward slashes for cross-platform YOLO path parsing
    clean_dataset_path = dataset_dir.replace("\\", "/")
    
    dataset_config = {
        "path": clean_dataset_path,
        "train": "images/train",
        "val": "images/val",
        "names": {
            0: "car"
        }
    }

    with open(dataset_yaml_path, "w") as f:
        yaml.dump(dataset_config, f, sort_keys=False)

    print(f"[CONFIG] Generated {dataset_yaml_path}")

    # 3. Import Ultralytics and start training
    try:
        from ultralytics import YOLO
        import torch
    except ImportError:
        print("[ERROR] ultralytics or torch not installed.")
        return

    has_cuda = torch.cuda.is_available()
    device = "0" if has_cuda else "cpu"
    device_name = torch.cuda.get_device_name(0) if has_cuda else "Intel CPU"
    print(f"  Device Selected:    {device_name} ({'CUDA GPU Acceleration' if has_cuda else 'CPU Mode'})")
    if not has_cuda:
        print("  [NOTE] PyTorch in Python 3.14 only has CPU builds. Use Python 3.12 to enable your NVIDIA RTX 3050.")
    print("==============================================================\n")

    # Use pretrained YOLOv8 nano as the starting weights for fast transfer learning
    model = YOLO("yolov8n.pt")

    print("[TRAINING] Commencing fine-tuning for 25 epochs...")
    results = model.train(
        data=dataset_yaml_path,
        epochs=25,
        imgsz=640,
        batch=8,
        device=device,
        workers=0,  # Avoid Windows multiprocessing issues
        project=os.path.join(base_dir, "runs"),
        name="custom_car_train",
        exist_ok=True,
        verbose=True
    )

    # 4. Locate best.pt and deploy as custom_car_model.pt
    best_weights = os.path.join(base_dir, "runs", "custom_car_train", "weights", "best.pt")
    target_custom_model = os.path.join(base_dir, "custom_car_model.pt")

    if os.path.exists(best_weights):
        shutil.copy2(best_weights, target_custom_model)
        print("\n==============================================================")
        print("  🎉 TRAINING COMPLETED SUCCESSFULLY!")
        print(f"  Best Weights Saved To: {target_custom_model}")
        print("==============================================================")
        print("  Your custom car model is ready to use!")
        print("  Run 'python main_vision.py' to run with your newly trained model.")
        print("==============================================================\n")
    else:
        print(f"[WARN] Could not find weights at {best_weights}.")

if __name__ == "__main__":
    train()
