"""Hand gesture control using webcam (alimaandev/Friday pattern)."""

import cv2
import numpy as np
from typing import Optional, Tuple
from enum import Enum


class Gesture(Enum):
    """Hand gestures."""
    OPEN_PALM = "open_palm"  # Speak
    FIST = "fist"  # Send
    UNKNOWN = "unknown"


class HandGestureDetector:
    """Lightweight hand gesture detection using skin-color segmentation.
    
    No MediaPipe/ML required - uses simple color-based detection
    for open palm and fist gestures.
    """
    
    def __init__(self):
        """Initialize hand gesture detector."""
        self.cap = None
        self.lower_skin = np.array([0, 48, 80], dtype=np.uint8)
        self.upper_skin = np.array([20, 255, 255], dtype=np.uint8)
    
    def start_camera(self, camera_id: int = 0) -> bool:
        """Start webcam capture."""
        self.cap = cv2.VideoCapture(camera_id)
        return self.cap.isOpened()
    
    def stop_camera(self) -> None:
        """Stop webcam capture."""
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def detect_gesture(self) -> Tuple[Optional[Gesture], Optional[np.ndarray]]:
        """Detect hand gesture from webcam frame.
        
        Returns:
            Tuple of (gesture, frame) or (None, None) if no frame
        """
        if not self.cap or not self.cap.isOpened():
            return None, None
        
        ret, frame = self.cap.read()
        if not ret:
            return None, None
        
        # Flip frame horizontally for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Convert to HSV for skin detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create skin mask
        skin_mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
        
        # Apply morphological operations to clean up mask
        kernel = np.ones((5, 5), np.uint8)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_DILATE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return Gesture.UNKNOWN, frame
        
        # Find largest contour (assumed to be hand)
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        # Filter small contours
        if area < 1000:
            return Gesture.UNKNOWN, frame
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Calculate aspect ratio and solidity
        aspect_ratio = float(w) / h
        hull = cv2.convexHull(largest_contour)
        hull_area = cv2.contourArea(hull)
        solidity = float(area) / hull_area if hull_area > 0 else 0
        
        # Classify gesture based on features
        gesture = self._classify_gesture(aspect_ratio, solidity, area)
        
        # Draw visualization
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, gesture.value, (x, y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        return gesture, frame
    
    def _classify_gesture(self, aspect_ratio: float, solidity: float, area: float) -> Gesture:
        """Classify gesture based on features."""
        # Open palm: higher solidity, more square aspect ratio
        if solidity > 0.85 and 0.7 < aspect_ratio < 1.3:
            return Gesture.OPEN_PALM
        
        # Fist: lower solidity, more rectangular aspect ratio
        if solidity < 0.85 and aspect_ratio < 0.8:
            return Gesture.FIST
        
        return Gesture.UNKNOWN
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current frame without gesture detection."""
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if ret:
            return cv2.flip(frame, 1)
        return None


# Gesture controller for voice interaction
class GestureVoiceController:
    """Controller for voice interaction via hand gestures."""
    
    def __init__(self):
        """Initialize gesture voice controller."""
        self.detector = HandGestureDetector()
        self.current_gesture = Gesture.UNKNOWN
        self.gesture_start_time = None
        self.gesture_threshold = 1.0  # Seconds to hold gesture
        self.on_speak_callback = None
        self.on_send_callback = None
    
    def start(self, camera_id: int = 0) -> bool:
        """Start gesture detection."""
        return self.detector.start_camera(camera_id)
    
    def stop(self) -> None:
        """Stop gesture detection."""
        self.detector.stop_camera()
    
    def set_callbacks(self, on_speak, on_send):
        """Set callback functions for gestures."""
        self.on_speak_callback = on_speak
        self.on_send_callback = on_send
    
    def update(self) -> Optional[Gesture]:
        """Update gesture detection and trigger callbacks.
        
        Returns:
            Current gesture or None if no change
        """
        import time
        
        gesture, frame = self.detector.detect_gesture()
        
        if gesture != self.current_gesture:
            self.current_gesture = gesture
            self.gesture_start_time = time.time()
            return gesture
        
        # Check if gesture held long enough
        if (self.gesture_start_time and 
            time.time() - self.gesture_start_time > self.gesture_threshold):
            
            if gesture == Gesture.OPEN_PALM and self.on_speak_callback:
                self.on_speak_callback()
            elif gesture == Gesture.FIST and self.on_send_callback:
                self.on_send_callback()
            
            # Reset to prevent repeated triggers
            self.gesture_start_time = None
        
        return None
