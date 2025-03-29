import os
import shutil

from ultralytics import YOLO


def analyze_images(folder_path):
    """Анализ изображений с помощью ИИ."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    weights_path = os.path.join(current_dir, "weight", "best.pt")

    model = YOLO(weights_path)

    confidence_threshold = 0.7  # Допустимая точность

    image_files = os.listdir(folder_path)

    bad_result_folder = os.path.join(os.path.dirname(folder_path), "bad_results")

    if not os.path.exists(bad_result_folder):
        os.makedirs(bad_result_folder)

    all_detected = True

    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        results = model(image_path)

        filtered_boxes = [
            box for box in results[0].boxes if box.conf[0].item() > confidence_threshold
        ]

        num_detected_objects = len(filtered_boxes)

        if num_detected_objects == 0:
            all_detected = False
            result_image_path = os.path.join(bad_result_folder, image_file)
            shutil.copy(image_path, result_image_path)

    return all_detected
