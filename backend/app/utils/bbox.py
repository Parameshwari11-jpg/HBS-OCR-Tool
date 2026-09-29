from typing import List, Optional, Tuple, Dict

def bbox_area(bbox: List[float]) -> float:
    if not bbox or len(bbox) < 4:
        return 0.0
    x0, y0, x1, y1 = bbox
    width = max(0.0, x1 - x0)
    height = max(0.0, y1 - y0)
    return width * height

def bbox_intersection(bbox_a: List[float], bbox_b: List[float]) -> float:
    if not bbox_a or not bbox_b or len(bbox_a) < 4 or len(bbox_b) < 4:
        return 0.0
    x0 = max(bbox_a[0], bbox_b[0])
    y0 = max(bbox_a[1], bbox_b[1])
    x1 = min(bbox_a[2], bbox_b[2])
    y1 = min(bbox_a[3], bbox_b[3])
    
    if x0 < x1 and y0 < y1:
        return (x1 - x0) * (y1 - y0)
    return 0.0

def bbox_iou(bbox_a: List[float], bbox_b: List[float]) -> float:
    inter = bbox_intersection(bbox_a, bbox_b)
    if inter <= 0:
        return 0.0
    area_a = bbox_area(bbox_a)
    area_b = bbox_area(bbox_b)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0

def bbox_overlap_ratio(bbox_a: List[float], bbox_b: List[float]) -> float:
    """Returns ratio of intersection relative to bbox_a's area."""
    inter = bbox_intersection(bbox_a, bbox_b)
    if inter <= 0:
        return 0.0
    area_a = bbox_area(bbox_a)
    return inter / area_a if area_a > 0 else 0.0

def calculate_relationship(bbox_a: List[float], bbox_b: List[float]) -> Dict[str, any]:
    inter = bbox_intersection(bbox_a, bbox_b)
    if inter <= 0:
        return {"relationship": "none", "iou": 0.0, "overlap_ratio_a": 0.0, "overlap_ratio_b": 0.0}
    
    area_a = bbox_area(bbox_a)
    area_b = bbox_area(bbox_b)
    iou = bbox_iou(bbox_a, bbox_b)
    ratio_a = inter / area_a if area_a > 0 else 0.0
    ratio_b = inter / area_b if area_b > 0 else 0.0
    
    if ratio_a > 0.85 and ratio_b > 0.85:
        rel = "equal"
    elif ratio_a > 0.85:
        rel = "contained_by"
    elif ratio_b > 0.85:
        rel = "contains"
    else:
        rel = "overlaps"
        
    return {
        "relationship": rel,
        "iou": iou,
        "overlap_ratio_a": ratio_a,
        "overlap_ratio_b": ratio_b
    }
