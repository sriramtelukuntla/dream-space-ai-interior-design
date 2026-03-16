import cv2
import numpy as np
from PIL import Image
import torch
from ultralytics import YOLO

class RoomSegmenter:
    """Segments room images to identify walls, floor, ceiling, and objects"""
    
    def __init__(self):
        # Initialize YOLO for object detection
        self.model = YOLO('yolov8n-seg.pt')
        
    def segment_room(self, image_path):
        """
        Segment the room image into different components
        
        Args:
            image_path: Path to the input image
            
        Returns:
            dict: Segmentation results with masks and labels
        """
        # Load image
        image = cv2.imread(image_path)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Perform segmentation
        results = self.model(image_rgb)
        
        segmentation_data = {
            'original_image': image_rgb,
            'masks': [],
            'labels': [],
            'boxes': [],
            'room_structure': self._identify_room_structure(image_rgb)
        }
        
        # Extract masks and labels
        if len(results) > 0:
            result = results[0]
            if hasattr(result, 'masks') and result.masks is not None:
                for i, mask in enumerate(result.masks.data):
                    mask_np = mask.cpu().numpy()
                    segmentation_data['masks'].append(mask_np)
                    
                    if hasattr(result, 'boxes'):
                        box = result.boxes[i]
                        label = result.names[int(box.cls)]
                        segmentation_data['labels'].append(label)
                        segmentation_data['boxes'].append(box.xyxy[0].cpu().numpy())
        
        return segmentation_data
    
    def _identify_room_structure(self, image):
        """Identify walls, floor, and ceiling using color and position analysis"""
        height, width = image.shape[:2]
        
        # Simple heuristic: top 20% is ceiling, bottom 30% is floor
        ceiling_region = image[:int(height * 0.2), :]
        floor_region = image[int(height * 0.7):, :]
        wall_region = image[int(height * 0.2):int(height * 0.7), :]
        
        return {
            'ceiling': {
                'region': (0, int(height * 0.2)),
                'dominant_color': self._get_dominant_color(ceiling_region)
            },
            'floor': {
                'region': (int(height * 0.7), height),
                'dominant_color': self._get_dominant_color(floor_region)
            },
            'walls': {
                'north': self._analyze_wall(image, 'north'),
                'south': self._analyze_wall(image, 'south'),
                'east': self._analyze_wall(image, 'east'),
                'west': self._analyze_wall(image, 'west')
            }
        }
    
    def _analyze_wall(self, image, direction):
        """Analyze wall properties by direction"""
        height, width = image.shape[:2]
        
        # Define wall regions based on direction
        if direction == 'north':
            wall = image[:height//3, width//3:2*width//3]
        elif direction == 'south':
            wall = image[2*height//3:, width//3:2*width//3]
        elif direction == 'east':
            wall = image[height//3:2*height//3, 2*width//3:]
        else:  # west
            wall = image[height//3:2*height//3, :width//3]
        
        return {
            'dominant_color': self._get_dominant_color(wall),
            'direction': direction
        }
    
    def _get_dominant_color(self, region):
        """Extract dominant color from a region"""
        pixels = region.reshape(-1, 3)
        unique, counts = np.unique(pixels, axis=0, return_counts=True)
        dominant = unique[counts.argmax()]
        return dominant.tolist()
    
    def create_mask_overlay(self, image, masks, alpha=0.5):
        """Create visualization with segmentation masks overlaid"""
        overlay = image.copy()
        
        for mask in masks:
            # Resize mask to image dimensions
            mask_resized = cv2.resize(mask, (image.shape[1], image.shape[0]))
            
            # Create colored mask
            color = np.random.randint(0, 255, 3)
            colored_mask = np.zeros_like(image)
            colored_mask[mask_resized > 0.5] = color
            
            # Blend with overlay
            overlay = cv2.addWeighted(overlay, 1, colored_mask, alpha, 0)
        
        return overlay