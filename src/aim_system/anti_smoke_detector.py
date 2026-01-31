"""
Anti-Smoke Detector Module
Advanced anti-smoke system - Filters smoke particles and noise
Enhanced with shape analysis and time-motion tracking system
"""

import numpy as np
import time
from collections import defaultdict

try:
    from scipy.spatial import ConvexHull
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not found. Convexity analysis will be done with simple method.")


class AntiSmokeDetector:
    """
    Advanced anti-smoke detector class
    Filters smoke particles, noise and invalid targets
    """
    
    def __init__(self):
        self.enabled = False
        
        # Anti-smoke parameters
        self.min_pixel_count = 15      # Minimum pixel count
        self.max_pixel_count = 500     # Maximum pixel count
        self.min_area = 50             # Minimum area
        self.max_width = 80            # Maximum width
        self.max_height = 80           # Maximum height
        self.max_aspect_ratio = 1.3    # Aspect ratio limit
        self.max_pixel_density = 0.7   # Pixel density limit
        self.continuous_strip_threshold = 0.6  # Continuous strip threshold
        
        # New advanced parameters
        self.min_convexity_ratio = 0.85  # Convexity ratio threshold
        
        # Time and motion tracking system
        self.canli_hedefler = {}       # Active targets {id: target_info}
        self.olu_ikonlar = []          # Dead target icons
        self.sonraki_hedef_id = 1      # New target ID counter
        self.frame_counter = 0         # Frame counter
        self.max_hedef_mesafe = 30     # Target matching distance
        self.hedef_kayip_suresi = 6    # How many frames until target is considered lost
        self.olu_ikon_suresi = 120     # Dead icon memory time (frames)
        
    def set_enabled(self, enabled):
        """Enable/disable anti-smoke feature"""
        self.enabled = enabled
        
    def is_enabled(self):
        """Return anti-smoke feature status"""
        return self.enabled
        
    def is_shape_plausible(self, cluster):
        """
        Section 1: Enhanced Shape Analysis (Pre-filtering)
        Shape analysis enhanced with convexity ratio
        
        Args:
            cluster: Pixel coordinates list [(x, y), ...]
            
        Returns:
            bool: True = shape plausible, False = smoke/noise
        """
        if not cluster or not self.enabled:
            return True
            
        pixel_count = len(cluster)
        
        # 1. Too few pixels = small particle (filter)
        if pixel_count < self.min_pixel_count:
            return False
        
        # 2. Too many pixels = large smoke area (filter)
        if pixel_count > self.max_pixel_count:
            return False
            
        # 3. Calculate cluster dimensions
        x_coords = [point[0] for point in cluster]
        y_coords = [point[1] for point in cluster]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        area = width * height
        
        # 4. Too small area = particle (filter)
        if area < self.min_area:
            return False
        
        # 5. Filter very large shapes (could be smoke)
        if width > self.max_width or height > self.max_height:
            return False
        
        # 6. Calculate aspect ratio
        if height == 0:
            return False
            
        aspect_ratio = width / height
        
        # 7. Advanced anti-smoke rules:
        
        # Long on Y axis but not large on X axis = enemy (valid)
        if height > width * 1.5:
            return True
        
        # Large on X axis = smoke (filter)
        if width > height * self.max_aspect_ratio:
            return False
        
        # 8. Count adjacent pixel groups (connected component analysis)
        connected_components = self._count_connected_components(cluster)
        pixel_density = len(cluster) / area
        
        # If too few connected components = dense smoke
        if connected_components < 3 and pixel_count > 50:
            return False
        
        # 9. If pixel density inside rectangle is too high = smoke
        if pixel_density > self.max_pixel_density:
            # Additional check: adjacent connection check
            if self._check_horizontal_density(cluster, width, height):
                return False
        
        # 10. Medium pixel count check
        if 100 <= pixel_count <= 300:
            # Tighter control for targets in this range
            if pixel_density > 0.5 and connected_components < 5:
                return False
        
        # 11. NEW: Convexity Ratio Control (Strongest Filter)
        convexity_ratio = self._calculate_convexity_ratio(cluster)
        if convexity_ratio < self.min_convexity_ratio:
            return False  # Very holey/frayed shape = smoke
        
        return True
    
    def _calculate_convexity_ratio(self, cluster):
        """
        Calculate convexity ratio
        Ratio = (Cluster's Actual Area) / (Convex Hull Area)
        
        Args:
            cluster: Pixel coordinates list
            
        Returns:
            float: Convexity ratio (0.0 - 1.0)
        """
        if len(cluster) < 3:
            return 0.0
            
        try:
            if SCIPY_AVAILABLE:
                # Advanced calculation with Scipy
                points = np.array(cluster)
                hull = ConvexHull(points)
                convex_area = hull.volume  # In 2D, volume = area
            else:
                # Simple alternative: Bounding box area
                x_coords = [point[0] for point in cluster]
                y_coords = [point[1] for point in cluster]
                
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                convex_area = (max_x - min_x + 1) * (max_y - min_y + 1)
            
            # Cluster's actual area (pixel count)
            actual_area = len(cluster)
            
            # Convexity ratio
            if convex_area > 0:
                ratio = actual_area / convex_area
                return min(ratio, 1.0)  # Maksimum 1.0
            else:
                return 0.0
                
        except Exception:
            # In case of calculation error
            return 0.0
    
    def _count_connected_components(self, cluster):
        """Calculate connected component count"""
        if not cluster:
            return 0
            
        # Convert coordinates to set (for fast lookup)
        pixel_set = set(cluster)
        visited = set()
        components = 0
        
        # 8-connected neighborhood
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        
        for pixel in cluster:
            if pixel not in visited:
                # New component found, scan with DFS
                components += 1
                stack = [pixel]
                
                while stack:
                    current = stack.pop()
                    if current in visited:
                        continue
                        
                    visited.add(current)
                    
                    # Check neighbors
                    for dx, dy in directions:
                        neighbor = (current[0] + dx, current[1] + dy)
                        if neighbor in pixel_set and neighbor not in visited:
                            stack.append(neighbor)
        
        return components
    
    def _check_horizontal_density(self, cluster, width, height):
        """Horizontal density check - for smoke detection"""
        if not cluster or height == 0:
            return False
            
        # Normalize coordinates
        x_coords = [point[0] for point in cluster]
        y_coords = [point[1] for point in cluster]
        
        min_x, min_y = min(x_coords), min(y_coords)
        
        # Group pixels in each horizontal strip
        horizontal_strips = defaultdict(list)
        
        for x, y in cluster:
            strip_y = y - min_y
            pixel_x = x - min_x
            horizontal_strips[strip_y].append(pixel_x)
        
        # If continuous pixel sequence exists in 80% of horizontal strips = smoke
        continuous_strips = 0
        total_strips = len(horizontal_strips)
        
        for strip_y, x_positions in horizontal_strips.items():
            if len(x_positions) < 3:  # Don't check if too few pixels
                continue
                
            # Sort X positions
            x_positions.sort()
            
            # Count continuous sequences
            continuous_count = 1
            for i in range(1, len(x_positions)):
                if x_positions[i] - x_positions[i-1] <= 2:  # 2 piksel tolerans
                    continuous_count += 1
                else:
                    break
            
            # If 70% of strip is continuous
            if continuous_count >= len(x_positions) * 0.7:
                continuous_strips += 1
        
        # If continuous sequence exists in 60% of strips = smoke
        return continuous_strips >= total_strips * self.continuous_strip_threshold
    
    def get_debug_info(self, cluster):
        """Return debug information"""
        if not cluster:
            return "Empty cluster"
            
        pixel_count = len(cluster)
        
        if not self.enabled:
            return f"Anti-Smoke: Off | Pixel: {pixel_count}"
            
        # Calculate dimensions
        x_coords = [point[0] for point in cluster]
        y_coords = [point[1] for point in cluster]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        area = width * height
        
        aspect_ratio = width / height if height > 0 else 0
        pixel_density = pixel_count / area if area > 0 else 0
        connected_components = self._count_connected_components(cluster)
        convexity_ratio = self._calculate_convexity_ratio(cluster)
        
        is_valid = self.is_shape_plausible(cluster)
        tracking_info = self.get_tracking_info()
        
        debug_info = f"""Advanced Anti-Smoke Debug:
├─ Status: {'On' if self.enabled else 'Off'}
├─ Pixel Count: {pixel_count}
├─ Dimensions: {width}x{height} (Area: {area})
├─ Aspect Ratio: {aspect_ratio:.2f}
├─ Pixel Density: {pixel_density:.2f}
├─ Connected Components: {connected_components}
├─ Convexity Ratio: {convexity_ratio:.3f}
├─ Tracking System:
│  ├─ Frame: {tracking_info['frame']}
│  ├─ Live Targets: {tracking_info['canli_hedefler']}
│  └─ Dead Icons: {tracking_info['olu_ikonlar']}
└─ Result: {'✅ VALID TARGET' if is_valid else '❌ SMOKE/NOISE'}"""
        
        return debug_info
    
    # ===== SECTION 2: TIME AND MOTION ANALYSIS (INTELLIGENT TRACKING SYSTEM) =====
    
    def update_frame(self, clusters):
        """
        Section 2: Time and Motion Analysis - Main update function
        Intelligent tracking system that runs on each frame
        
        Args:
            clusters: All pixel clusters detected in current frame
            
        Returns:
            list: Valid target clusters (filtered)
        """
        self.frame_counter += 1
        valid_targets = []
        
        # Step A: Input and Pre-filtering
        shape_valid_clusters = []
        for cluster in clusters:
            if self.is_shape_plausible(cluster):
                shape_valid_clusters.append(cluster)
        
        # Step B: Matching (Finding Current Targets)
        matched_clusters = []
        unmatched_clusters = []
        
        for cluster in shape_valid_clusters:
            center = self._get_cluster_center(cluster)
            matched_target_id = self._find_matching_target(center)
            
            if matched_target_id is not None:
                # Update current target
                self.canli_hedefler[matched_target_id]['pozisyon'] = center
                self.canli_hedefler[matched_target_id]['son_gorulme_ani'] = self.frame_counter
                self.canli_hedefler[matched_target_id]['cluster'] = cluster
                matched_clusters.append(cluster)
            else:
                unmatched_clusters.append(cluster)
        
        # Step C: Loss Detection (Is Target Dead?)
        kayip_hedefler = []
        for hedef_id, hedef_info in list(self.canli_hedefler.items()):
            if self.frame_counter - hedef_info['son_gorulme_ani'] > self.hedef_kayip_suresi:
                # Target lost, convert to dead icon
                self.olu_ikonlar.append({
                    'pozisyon': hedef_info['pozisyon'],
                    'olum_ani': self.frame_counter
                })
                kayip_hedefler.append(hedef_id)
        
        # Delete lost targets
        for hedef_id in kayip_hedefler:
            del self.canli_hedefler[hedef_id]
        
        # Step D: Decision Making (New Target or Dead Icon?)
        for cluster in unmatched_clusters:
            center = self._get_cluster_center(cluster)
            
            if not self._is_near_dead_icon(center):
                # New valid target
                self.canli_hedefler[self.sonraki_hedef_id] = {
                    'pozisyon': center,
                    'son_gorulme_ani': self.frame_counter,
                    'cluster': cluster
                }
                valid_targets.append(cluster)
                self.sonraki_hedef_id += 1
        
        # Also add current live targets
        for hedef_info in self.canli_hedefler.values():
            if 'cluster' in hedef_info:
                valid_targets.append(hedef_info['cluster'])
        
        # Step E: Memory Cleanup
        self._cleanup_memory()
        
        return valid_targets
    
    def _get_cluster_center(self, cluster):
        """Calculate cluster center coordinates"""
        if not cluster:
            return (0, 0)
        
        x_coords = [point[0] for point in cluster]
        y_coords = [point[1] for point in cluster]
        
        center_x = sum(x_coords) // len(x_coords)
        center_y = sum(y_coords) // len(y_coords)
        
        return (center_x, center_y)
    
    def _find_matching_target(self, center):
        """Is there a current target near the given center position?"""
        for hedef_id, hedef_info in self.canli_hedefler.items():
            distance = self._calculate_distance(center, hedef_info['pozisyon'])
            if distance <= self.max_hedef_mesafe:
                return hedef_id
        return None
    
    def _is_near_dead_icon(self, center):
        """Is the given position near a dead icon?"""
        for olu_ikon in self.olu_ikonlar:
            distance = self._calculate_distance(center, olu_ikon['pozisyon'])
            if distance <= self.max_hedef_mesafe:
                return True
        return False
    
    def _calculate_distance(self, pos1, pos2):
        """Euclidean distance between two points"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return (dx * dx + dy * dy) ** 0.5
    
    def _cleanup_memory(self):
        """Clean up old dead icon records"""
        current_frame = self.frame_counter
        self.olu_ikonlar = [
            ikon for ikon in self.olu_ikonlar
            if current_frame - ikon['olum_ani'] <= self.olu_ikon_suresi
        ]
    
    def is_valid_target(self, cluster):
        """
        Old function name for backward compatibility
        Now only performs shape check
        """
        return self.is_shape_plausible(cluster)
    
    def get_tracking_info(self):
        """Debug information about tracking system"""
        return {
            'frame': self.frame_counter,
            'canli_hedefler': len(self.canli_hedefler),
            'olu_ikonlar': len(self.olu_ikonlar),
            'sonraki_id': self.sonraki_hedef_id
        }
    
    def set_parameters(self, **kwargs):
        """Update anti-smoke parameters"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_parameters(self):
        """Return current parameters"""
        return {
            'enabled': self.enabled,
            'min_pixel_count': self.min_pixel_count,
            'max_pixel_count': self.max_pixel_count,
            'min_area': self.min_area,
            'max_width': self.max_width,
            'max_height': self.max_height,
            'max_aspect_ratio': self.max_aspect_ratio,
            'max_pixel_density': self.max_pixel_density,
            'continuous_strip_threshold': self.continuous_strip_threshold,
            'min_convexity_ratio': self.min_convexity_ratio,
            'max_hedef_mesafe': self.max_hedef_mesafe,
            'hedef_kayip_suresi': self.hedef_kayip_suresi,
            'olu_ikon_suresi': self.olu_ikon_suresi
        }


# Usage example
if __name__ == "__main__":
    # Create anti-smoke detector
    detector = AntiSmokeDetector()
    detector.set_enabled(True)
    
    # Test cluster
    test_cluster = [(100, 100), (101, 100), (102, 100), (100, 101), (101, 101)]
    
    # Test et
    is_valid = detector.is_valid_target(test_cluster)
    debug_info = detector.get_debug_info(test_cluster)
    
    print(f"Test sonucu: {is_valid}")
    print(debug_info)