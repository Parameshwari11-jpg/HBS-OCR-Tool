import cv2
import numpy as np
from typing import List, Dict, Any
import pymupdf as fitz
import logging

logger = logging.getLogger("visual_detector")

def detect_visual_elements_from_page_image(
    page_img_path: str,
    page_rect: fitz.Rect,
    known_text_bboxes: List[List[float]],
    render_dpi: float = 150.0
) -> List[Dict[str, Any]]:
    """
    Multi-Scale Visual Element Discovery Engine.
    Scans a rendered page image to discover all discrete non-text visual elements, including:
    - National / tricolor flags (e.g. French flag blue/white/red stripes)
    - Distinct photographs and figures (e.g. portraits, monuments/palaces, landscape photos)
    - Enclosed child figure portraits and media frames (e.g. DVD frame, screen bezel, boy photograph)
    - Graphic containers, callout boxes & bordered cards (e.g. yellow Objectifs box, Video card, Online Practice card)
    - Circular badges, emblems, and globe icons
    - Long margin spine rules and divider lines (isolated so they do not swallow child elements)

    Filters out full-page and half-page container boxes so each element has its own distinct selectable path.
    """
    img = cv2.imread(page_img_path)
    if img is None:
        return []

    h, w, _ = img.shape
    pw = float(page_rect.width)
    ph = float(page_rect.height)
    if pw <= 0 or ph <= 0:
        return []

    scale_pt_to_px = w / pw
    scale_px_to_pt = pw / w

    # 1. Mask out recognized text regions with a margin so text strokes don't bleed into graphics.
    # Exclude abnormal or huge text boxes (e.g. column-spanning or full-height OCR blocks)
    # so genuine portrait photos, figures, and charts are never blacked out.
    text_mask = np.zeros((h, w), dtype=np.uint8)
    for b in known_text_bboxes:
        if len(b) >= 4:
            bw = b[2] - b[0]
            bh = b[3] - b[1]
            if bh > 0.45 * ph and bw > 0.30 * pw:
                # Column-spanning or page-spanning text region artifact — skip masking photos
                continue
            x0 = max(0, int(b[0] * scale_pt_to_px) - 2)
            y0 = max(0, int(b[1] * scale_pt_to_px) - 2)
            x1 = min(w, int(b[2] * scale_pt_to_px) + 2)
            y1 = min(h, int(b[3] * scale_pt_to_px) + 2)
            text_mask[y0:y1, x0:x1] = 255

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    elements: List[Dict[str, Any]] = []

    # =========================================================================
    # Step 2: Margin Spine Rules (Tall decorative vertical colored bars)
    # =========================================================================
    margin_w_px = int(0.12 * w)
    spine_mask = np.zeros((h, w), dtype=np.uint8)
    for side_x0, side_x1 in [(0, margin_w_px), (w - margin_w_px, w)]:
        roi_hsv = hsv[:, side_x0:side_x1]
        sat_mask = (roi_hsv[:, :, 1] > 60) & (roi_hsv[:, :, 2] > 70)
        spine_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, int(40 * scale_pt_to_px)))
        spine_opened = cv2.morphologyEx(sat_mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, spine_kernel)
        cnts, _ = cv2.findContours(spine_opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cnts:
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            if ch >= int(150 * scale_pt_to_px):
                actual_x = side_x0 + cx
                bx0 = round(actual_x * scale_px_to_pt, 2)
                by0 = round(cy * scale_px_to_pt, 2)
                bx1 = round((actual_x + cw) * scale_px_to_pt, 2)
                by1 = round((cy + ch) * scale_px_to_pt, 2)
                elements.append({
                    "type": "drawing",
                    "subtype": "line_vertical",
                    "tag": "Figure",
                    "bbox": [bx0, by0, bx1, by1],
                    "width": round(bx1 - bx0, 2),
                    "height": round(by1 - by0, 2)
                })
                # Sever horizontal bridging across margin by masking spine
                spine_mask[cy:cy+ch, max(0, actual_x-2):min(w, actual_x+cw+4)] = 255

    # =========================================================================
    # Step 3: National / Multi-Color Flags (e.g. Tricolor Flag Stripes)
    # =========================================================================
    blue_mask = (hsv[:, :, 0] >= 95) & (hsv[:, :, 0] <= 135) & (hsv[:, :, 1] >= 80) & (hsv[:, :, 2] >= 50) & (spine_mask == 0) & (text_mask == 0)
    red_mask = ((hsv[:, :, 0] <= 12) | (hsv[:, :, 0] >= 165)) & (hsv[:, :, 1] >= 80) & (hsv[:, :, 2] >= 60) & (spine_mask == 0) & (text_mask == 0)
    b_open = cv2.morphologyEx(blue_mask.astype(np.uint8)*255, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (4, 8)))
    r_open = cv2.morphologyEx(red_mask.astype(np.uint8)*255, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (4, 8)))
    b_cnts, _ = cv2.findContours(b_open, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    r_cnts, _ = cv2.findContours(r_open, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    flag_mask = np.zeros((h, w), dtype=np.uint8)
    for bc in b_cnts:
        bx, by, bw, bh = cv2.boundingRect(bc)
        if bw < 8 or bh < 15:
            continue
        for rc in r_cnts:
            rx, ry, rw, rh = cv2.boundingRect(rc)
            if rw < 8 or rh < 15:
                continue
            y_overlap = max(0, min(by+bh, ry+rh) - max(by, ry))
            if y_overlap / max(1, min(bh, rh)) > 0.70 and rx > bx:
                # French flag horizontal gap: white stripe between blue and red
                gap = rx - (bx + bw)
                if 0.3 * bw <= gap <= 2.5 * bw:
                    fx0 = min(bx, rx)
                    fx1 = max(bx+bw, rx+rw)
                    fy0 = min(by, ry)
                    fy1 = max(by+bh, ry+rh)
                    fw = (fx1 - fx0) * scale_px_to_pt
                    fh = (fy1 - fy0) * scale_px_to_pt
                    if 0.6 <= (fw / max(1.0, fh)) <= 2.2 and 18.0 <= fh <= 180.0:
                        fb = [round(fx0 * scale_px_to_pt, 2), round(fy0 * scale_px_to_pt, 2),
                              round(fx1 * scale_px_to_pt, 2), round(fy1 * scale_px_to_pt, 2)]
                        elements.append({
                            "type": "figure",
                            "subtype": "flag",
                            "tag": "Figure",
                            "bbox": fb,
                            "width": round(fw, 2),
                            "height": round(fh, 2)
                        })
                        flag_mask[fy0:fy1, fx0:fx1] = 255
                        break

    # =========================================================================
    # Step 4: Photo & Figure Detection via High-Detail Gradient & Texture Variance
    # =========================================================================
    blur = cv2.blur(gray.astype(np.float32), (11, 11))
    blur2 = cv2.blur(gray.astype(np.float32)**2, (11, 11))
    std_dev = np.sqrt(np.maximum(0, blur2 - blur**2))
    std_dev[text_mask > 0] = 0
    std_dev[spine_mask > 0] = 0
    std_dev[flag_mask > 0] = 0

    photo_seeds = (std_dev > 28.0).astype(np.uint8) * 255
    photo_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(9 * scale_pt_to_px), int(9 * scale_pt_to_px)))
    photo_closed = cv2.morphologyEx(photo_seeds, cv2.MORPH_CLOSE, photo_kernel)
    p_cnts, _ = cv2.findContours(photo_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Decompose any wide composite photo contours where a vertical background gutter separates adjacent photos
    raw_photo_boxes = []
    # Identify prominent vertical gutters across the page
    sub_page_gray = gray[int(0.05 * h):int(0.95 * h), :]
    page_white_col = (sub_page_gray > 235).mean(axis=0)
    page_gutters_px = []
    for c_px in range(int(35 * scale_pt_to_px), w - int(35 * scale_pt_to_px)):
        if page_white_col[max(0, c_px-2):min(w, c_px+3)].mean() > 0.82:
            page_gutters_px.append(c_px)

    for pc in p_cnts:
        px, py, pw_px, ph_px = cv2.boundingRect(pc)
        w_pt = pw_px * scale_px_to_pt
        h_pt = ph_px * scale_px_to_pt
        if w_pt < 25.0 or h_pt < 25.0:
            continue
        if w_pt > 0.40 * pw:
            roi_g = gray[py:py+ph_px, px:px+pw_px]
            white_col = (roi_g > 235).mean(axis=0)
            gutter_candidates = []
            for col_idx in range(int(30 * scale_pt_to_px), roi_g.shape[1] - int(30 * scale_pt_to_px)):
                w_r = white_col[max(0, col_idx-2):min(roi_g.shape[1], col_idx+3)].mean()
                if w_r > 0.70:
                    gutter_candidates.append((col_idx, w_r))
            if gutter_candidates:
                best_c = max(gutter_candidates, key=lambda x: x[1])
                split_px = best_c[0]
                raw_photo_boxes.append((px, py, split_px, ph_px))
                raw_photo_boxes.append((px + split_px, py, pw_px - split_px, ph_px))
                continue
        raw_photo_boxes.append((px, py, pw_px, ph_px))

    # Detect standing full-length human figures isolated against light backgrounds
    # Sever vertical bridging across detected gutters so standing figures (e.g. woman in dress) are isolated
    non_white_page = ((gray < 240) & (spine_mask == 0)).astype(np.uint8) * 255
    for g_px in page_gutters_px:
        non_white_page[:, max(0, g_px-2):min(w, g_px+3)] = 0

    # For each gutter-separated horizontal pane, find tall vertical figures
    gutter_bounds = [0] + [g for i, g in enumerate(page_gutters_px) if i == 0 or g - page_gutters_px[i-1] > 10] + [w]
    for p_idx in range(len(gutter_bounds) - 1):
        pane_x0 = gutter_bounds[p_idx]
        pane_x1 = gutter_bounds[p_idx + 1]
        if (pane_x1 - pane_x0) * scale_px_to_pt < 40.0:
            continue
        pane_mask = non_white_page[:, pane_x0:pane_x1]
        pane_bridge = cv2.morphologyEx(pane_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (int(20 * scale_pt_to_px), int(25 * scale_pt_to_px))))
        p_cnts_pane, _ = cv2.findContours(pane_bridge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for p_c in p_cnts_pane:
            cx, cy, cw_px, ch_px = cv2.boundingRect(p_c)
            cw_pt = cw_px * scale_px_to_pt
            ch_pt = ch_px * scale_px_to_pt
            if 40.0 <= cw_pt <= 0.55 * pw and ch_pt >= 0.45 * ph:
                p_roi = img[cy:cy+ch_px, pane_x0+cx:pane_x0+cx+cw_px]
                if p_roi.size > 0 and p_roi.std() > 30.0:
                    raw_photo_boxes.append((pane_x0 + cx, cy, cw_px, ch_px))

    # Detect tilted photo boundaries via Canny edge enclosures
    # (e.g. tilted funicular cable car photo bordered by a tilted white paper border)
    edges_all = cv2.Canny(gray, 25, 80)
    edges_all[spine_mask > 0] = 0
    tilted_cnts, _ = cv2.findContours(edges_all, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for tc in tilted_cnts:
        tx, ty, tw_px, th_px = cv2.boundingRect(tc)
        tw_pt, th_pt = tw_px * scale_px_to_pt, th_px * scale_px_to_pt
        if 80.0 <= tw_pt <= 0.55 * pw and 140.0 <= th_pt <= 0.65 * ph:
            t_roi = img[ty:ty+th_px, tx:tx+tw_px]
            if t_roi.size > 0 and t_roi.std() > 30.0:
                t_sub_gray = gray[ty:ty+th_px, tx:tx+tw_px]
                t_blur = cv2.blur(t_sub_gray.astype(np.float32), (11, 11))
                t_blur2 = cv2.blur(t_sub_gray.astype(np.float32)**2, (11, 11))
                t_std = np.sqrt(np.maximum(0, t_blur2 - t_blur**2))
                if (t_std > 20.0).mean() > 0.15:
                    raw_photo_boxes.append((tx, ty, tw_px, th_px))

    # Detect media monitor frames / TV bezels & inner child screens anywhere on page
    for fc in tilted_cnts:
        fx, fy, fw_px, fh_px = cv2.boundingRect(fc)
        fw_pt, fh_pt = fw_px * scale_px_to_pt, fh_px * scale_px_to_pt
        # Bezel / monitor frame: w ~ 45 to 75 pt, h ~ 42 to 68 pt
        if 45.0 <= fw_pt <= 75.0 and 42.0 <= fh_pt <= 68.0:
            sub_bezel = img[fy:fy+fh_px, fx:fx+fw_px]
            if sub_bezel.size > 0 and sub_bezel.std() > 20.0:
                fbx0 = round(fx * scale_px_to_pt, 2)
                fby0 = round(fy * scale_px_to_pt, 2)
                fbx1 = round((fx + fw_px) * scale_px_to_pt, 2)
                fby1 = round((fy + fh_px) * scale_px_to_pt, 2)
                elements.append({
                    "type": "figure",
                    "subtype": "frame",
                    "tag": "Figure",
                    "bbox": [fbx0, fby0, fbx1, fby1],
                    "width": round(fw_pt, 2),
                    "height": round(fh_pt, 2)
                })
                # Search for inner video screen / portrait inside this bezel
                sub_gray = gray[fy:fy+fh_px, fx:fx+fw_px]
                sub_edges = cv2.Canny(sub_gray, 20, 70)
                sub_cnts, _ = cv2.findContours(sub_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                for sc in sorted(sub_cnts, key=cv2.contourArea, reverse=True):
                    sx, sy, sw_px, sh_px = cv2.boundingRect(sc)
                    sw_pt, sh_pt = sw_px * scale_px_to_pt, sh_px * scale_px_to_pt
                    if 20.0 <= sw_pt <= 40.0 and 26.0 <= sh_pt <= 50.0:
                        sbx0 = round((fx + sx) * scale_px_to_pt, 2)
                        sby0 = round((fy + sy) * scale_px_to_pt, 2)
                        sbx1 = round(sbx0 + sw_pt, 2)
                        sby1 = round(sby0 + sh_pt, 2)
                        elements.append({
                            "type": "figure",
                            "subtype": "photo",
                            "tag": "Figure",
                            "bbox": [sbx0, sby0, sbx1, sby1],
                            "width": round(sw_pt, 2),
                            "height": round(sh_pt, 2)
                        })
                        break

    for (px, py, pw_px, ph_px) in raw_photo_boxes:
        w_pt = pw_px * scale_px_to_pt
        h_pt = ph_px * scale_px_to_pt
        if 25.0 <= w_pt < 0.65 * pw and 25.0 <= h_pt < 0.95 * ph:
            roi = img[py:py+ph_px, px:px+pw_px]
            if roi.size > 0 and roi.std() > 25.0:
                bx0 = round(px * scale_px_to_pt, 2)
                by0 = round(py * scale_px_to_pt, 2)
                bx1 = round((px + pw_px) * scale_px_to_pt, 2)
                by1 = round((py + ph_px) * scale_px_to_pt, 2)
                
                # Check for duplication with existing elements
                dup = False
                for el in elements:
                    eb = el["bbox"]
                    ow = max(0.0, min(bx1, eb[2]) - max(bx0, eb[0]))
                    oh = max(0.0, min(by1, eb[3]) - max(by0, eb[1]))
                    if (ow * oh) / max(1.0, w_pt * h_pt) > 0.70 and el["subtype"] in ("photo", "frame"):
                        dup = True
                        break
                if not dup:
                    elements.append({
                        "type": "figure",
                        "subtype": "photo",
                        "tag": "Figure",
                        "bbox": [bx0, by0, bx1, by1],
                        "width": round(w_pt, 2),
                        "height": round(h_pt, 2)
                    })
    # =========================================================================
    # Step 5: Card Containers & Boxes (e.g. Objectifs yellow box, practice cards)
    # =========================================================================
    # Yellow / tinted container box detection
    yellow_mask = (hsv[:, :, 0] >= 18) & (hsv[:, :, 0] <= 45) & (hsv[:, :, 1] >= 12) & (hsv[:, :, 2] >= 170)
    yellow_mask[spine_mask > 0] = 0
    yellow_closed = cv2.morphologyEx(yellow_mask.astype(np.uint8)*255, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
    yellow_bridged = cv2.morphologyEx(yellow_closed, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(40 * scale_pt_to_px))))
    y_cnts, _ = cv2.findContours(yellow_bridged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for yc in y_cnts:
        yx, yy, yw_px, yh_px = cv2.boundingRect(yc)
        yw_pt = yw_px * scale_px_to_pt
        yh_pt = yh_px * scale_px_to_pt
        if yw_pt >= 60.0 and yh_pt >= 120.0 and yw_pt < 0.60 * pw:
            bx0 = round(yx * scale_px_to_pt, 2)
            by0 = round(yy * scale_px_to_pt, 2)
            bx1 = round((yx + yw_px) * scale_px_to_pt, 2)
            by1 = round((yy + yh_px) * scale_px_to_pt, 2)
            elements.append({
                "type": "figure",
                "subtype": "box",
                "tag": "Figure",
                "bbox": [bx0, by0, bx1, by1],
                "width": round(yw_pt, 2),
                "height": round(yh_pt, 2)
            })

    # Bordered card boxes via Canny edges
    edges = cv2.Canny(gray, 30, 90)
    edges[text_mask > 0] = 0
    edges[spine_mask > 0] = 0
    card_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(8 * scale_pt_to_px), int(8 * scale_pt_to_px)))
    card_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, card_kernel)
    card_cnts, _ = cv2.findContours(card_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cc in card_cnts:
        cx, cy, cw_px, ch_px = cv2.boundingRect(cc)
        cw_pt = cw_px * scale_px_to_pt
        ch_pt = ch_px * scale_px_to_pt
        if 50.0 <= cw_pt <= 250.0 and 30.0 <= ch_pt <= 160.0:
            bx0 = round(cx * scale_px_to_pt, 2)
            by0 = round(cy * scale_px_to_pt, 2)
            bx1 = round((cx + cw_px) * scale_px_to_pt, 2)
            by1 = round((cy + ch_px) * scale_px_to_pt, 2)
            dup = False
            for el in elements:
                eb = el["bbox"]
                ow = max(0.0, min(bx1, eb[2]) - max(bx0, eb[0]))
                oh = max(0.0, min(by1, eb[3]) - max(by0, eb[1]))
                if (ow * oh) / max(1.0, cw_pt * ch_pt) > 0.60:
                    dup = True
                    break
            if not dup:
                elements.append({
                    "type": "figure",
                    "subtype": "card",
                    "tag": "Figure",
                    "bbox": [bx0, by0, bx1, by1],
                    "width": round(cw_pt, 2),
                    "height": round(ch_pt, 2)
                })

    # =========================================================================
    # Step 6: Divider Lines & Rules
    # =========================================================================
    non_white = ((gray < 238) & (text_mask == 0) & (spine_mask == 0)).astype(np.uint8) * 255
    vert_k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(30 * (render_dpi / 150.0))))
    horiz_k = cv2.getStructuringElement(cv2.MORPH_RECT, (int(30 * (render_dpi / 150.0)), 1))
    v_lines = cv2.morphologyEx(non_white, cv2.MORPH_OPEN, vert_k)
    h_lines = cv2.morphologyEx(non_white, cv2.MORPH_OPEN, horiz_k)
    lines_comb = cv2.bitwise_or(v_lines, h_lines)
    l_cnts, _ = cv2.findContours(lines_comb, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for lc in l_cnts:
        lx, ly, lw_px, lh_px = cv2.boundingRect(lc)
        lw_pt = lw_px * scale_px_to_pt
        lh_pt = lh_px * scale_px_to_pt
        if (lw_pt >= 35.0 and lh_pt <= 18.0) or (lh_pt >= 35.0 and lw_pt <= 18.0):
            bx0 = round(lx * scale_px_to_pt, 2)
            by0 = round(ly * scale_px_to_pt, 2)
            bx1 = round((lx + lw_px) * scale_px_to_pt, 2)
            by1 = round((ly + lh_px) * scale_px_to_pt, 2)
            st = "line_vertical" if lh_pt > lw_pt else "line_horizontal"
            elements.append({
                "type": "drawing",
                "subtype": st,
                "tag": "Figure",
                "bbox": [bx0, by0, bx1, by1],
                "width": round(lw_pt, 2),
                "height": round(lh_pt, 2)
            })

    # =========================================================================
    # Step 7: Circular Badges & Globe Icons (HoughCircles)
    # =========================================================================
    photo_mask = np.zeros((h, w), dtype=np.uint8)
    for el in elements:
        if el["subtype"] in ("photo", "flag"):
            pb = el["bbox"]
            px0 = max(0, int(pb[0] * scale_pt_to_px))
            py0 = max(0, int(pb[1] * scale_pt_to_px))
            px1 = min(w, int(pb[2] * scale_pt_to_px))
            py1 = min(h, int(pb[3] * scale_pt_to_px))
            photo_mask[py0:py1, px0:px1] = 255

    gray_icon = gray.copy()
    gray_icon[text_mask > 0] = 255
    gray_icon[spine_mask > 0] = 255
    gray_icon[photo_mask > 0] = 255

    circles = cv2.HoughCircles(
        gray_icon, cv2.HOUGH_GRADIENT, dp=1.0, minDist=25,
        param1=50, param2=22,
        minRadius=int(6 * scale_pt_to_px), maxRadius=int(18 * scale_pt_to_px)
    )
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for c in circles[0, :]:
            cx, cy, cr = c
            roi = gray_icon[max(0, cy-cr):min(h, cy+cr), max(0, cx-cr):min(w, cx+cr)]
            if roi.size > 0 and roi.std() > 25.0:
                bx0 = round((cx - cr) * scale_px_to_pt, 2)
                by0 = round((cy - cr) * scale_px_to_pt, 2)
                bx1 = round((cx + cr) * scale_px_to_pt, 2)
                by1 = round((cy + cr) * scale_px_to_pt, 2)
                elements.append({
                    "type": "figure",
                    "subtype": "icon",
                    "tag": "Figure",
                    "bbox": [bx0, by0, bx1, by1],
                    "width": round(bx1 - bx0, 2),
                    "height": round(by1 - by0, 2)
                })

    # =========================================================================
    # Step 8: Deduplicate and Filter Full-Page Container Artifacts
    # =========================================================================
    final_elements: List[Dict[str, Any]] = []
    for el in elements:
        b = el["bbox"]
        w_pt = b[2] - b[0]
        h_pt = b[3] - b[1]
        # Never allow page-spanning container boxes (> 0.65 of page width AND height)
        if w_pt > 0.65 * pw and h_pt > 0.65 * ph:
            continue
        # Deduplicate identical boxes
        is_dup = False
        for f_el in final_elements:
            fb = f_el["bbox"]
            if abs(fb[0] - b[0]) < 8 and abs(fb[1] - b[1]) < 8 and abs(fb[2] - b[2]) < 8 and abs(fb[3] - b[3]) < 8:
                is_dup = True
                break
        if not is_dup:
            final_elements.append(el)

    return final_elements
