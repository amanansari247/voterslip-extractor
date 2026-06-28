import base64
import json
import sys

import fitz

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None


PREVIEW_DPI = 200
MIN_CARD_WIDTH_PT = 80
MIN_CARD_HEIGHT_PT = 35
MIN_BOX_SIZE = 24


NAME_MARKERS = (
    "Name",
    "NAME",
    "ਨਾਮ",
    "नाम",
    "à¨¨à¨¾à¨®",
    "à¨¨à¨µà¨®",
    "à¤¨à¤¾à¤®",
    "à¤¨à¤ªà¤®",
)

POLLING_MARKERS = (
    "Polling Station",
    "polling station",
    "ਪੋਲਿੰਗ",
    "मतदान",
    "à¨ªà©‹à¨²à¨¿à©°à¨—",
    "à¤®à¤¤à¤¦à¤¾à¤¨",
)


def render_page(page):
    zoom = PREVIEW_DPI / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    image = base64.b64encode(pix.tobytes("jpeg")).decode("utf-8")
    return {
        "image": f"data:image/jpeg;base64,{image}",
        "width": pix.width,
        "height": pix.height,
        "scaleX": pix.width / page.rect.width,
        "scaleY": pix.height / page.rect.height,
    }, pix


def rect_to_box(rect, page_info, page_index, box_index, source):
    sx = page_info["scaleX"]
    sy = page_info["scaleY"]
    return {
        "id": f"p{page_index}-b{box_index}",
        "pageIndex": page_index,
        "x": round(rect.x0 * sx, 2),
        "y": round(rect.y0 * sy, 2),
        "width": round(rect.width * sx, 2),
        "height": round(rect.height * sy, 2),
        "source": source,
    }


def cluster_numbers(values, tolerance):
    values = sorted(values)
    clusters = []
    for value in values:
        if not clusters or abs(value - clusters[-1][-1]) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return [sum(cluster) / len(cluster) for cluster in clusters]


def cluster_weighted_positions(positions, tolerance):
    positions = sorted(positions, key=lambda item: item[0])
    clusters = []
    for value, weight in positions:
        if not clusters or abs(value - clusters[-1][-1][0]) > tolerance:
            clusters.append([(value, weight)])
        else:
            clusters[-1].append((value, weight))

    result = []
    for cluster in clusters:
        total_weight = sum(max(1, item[1]) for item in cluster)
        value = sum(item[0] * max(1, item[1]) for item in cluster) / total_weight
        weight = max(item[1] for item in cluster)
        result.append((value, weight))
    return result


def find_even_sequence(candidates, min_len, min_gap, max_gap, tolerance, prefer_earlier=True):
    if len(candidates) < min_len:
        return []

    values = [item[0] for item in candidates]
    weights = {round(item[0], 2): item[1] for item in candidates}
    best = None

    for start_index, start in enumerate(values):
        for next_index in range(start_index + 1, len(values)):
            gap = values[next_index] - start
            if gap < min_gap or gap > max_gap:
                continue

            sequence = [start, values[next_index]]
            current = values[next_index]

            while True:
                expected = current + gap
                remaining = [value for value in values if value > current + tolerance]
                if not remaining:
                    break
                closest = min(remaining, key=lambda value: abs(value - expected))
                if abs(closest - expected) > tolerance:
                    break
                sequence.append(closest)
                current = closest

            if len(sequence) < min_len:
                continue

            gaps = [b - a for a, b in zip(sequence, sequence[1:])]
            mean_gap = sum(gaps) / len(gaps)
            variance = sum((item - mean_gap) ** 2 for item in gaps) / len(gaps)
            strength = sum(weights.get(round(item, 2), 1) for item in sequence)
            start_bonus = -sequence[0] * 4 if prefer_earlier else sequence[0] * 0.05
            score = len(sequence) * 10000 + strength * 0.1 - variance * 15 + start_bonus

            if not best or score > best["score"]:
                best = {"score": score, "sequence": sequence}

    return best["sequence"] if best else []


def overlap_ratio(a, b):
    intersection = a & b
    if intersection.is_empty:
        return 0
    smaller = min(a.get_area(), b.get_area())
    if smaller <= 0:
        return 0
    return intersection.get_area() / smaller


def dedupe_rects(rects):
    deduped = []
    for rect in sorted(rects, key=lambda r: (round(r.y0, 1), round(r.x0, 1))):
        if any(overlap_ratio(rect, existing) > 0.86 for existing in deduped):
            continue
        deduped.append(rect)
    return deduped


def is_reasonable_card(rect, page):
    page_w = page.rect.width
    page_h = page.rect.height
    if rect.y0 < page_h * 0.055:
        return False
    if rect.width < MIN_CARD_WIDTH_PT or rect.height < MIN_CARD_HEIGHT_PT:
        return False
    if rect.width > page_w * 0.48 or rect.height > page_h * 0.18:
        return False
    aspect = rect.width / rect.height
    return 1.6 <= aspect <= 4.2


def detect_rectangles(page):
    rects = []
    for drawing in page.get_drawings():
        for item in drawing.get("items", []):
            if item[0] == "re":
                rect = fitz.Rect(item[1])
                if is_reasonable_card(rect, page):
                    rects.append(rect)
    return dedupe_rects(rects)


def detect_line_grid(page):
    horizontal = []
    vertical = []
    page_w = page.rect.width
    page_h = page.rect.height

    for drawing in page.get_drawings():
        for item in drawing.get("items", []):
            if item[0] != "l":
                continue
            p1, p2 = item[1], item[2]
            if abs(p1.y - p2.y) < 1.5 and abs(p1.x - p2.x) > page_w * 0.18:
                horizontal.append((min(p1.x, p2.x), max(p1.x, p2.x), p1.y))
            if abs(p1.x - p2.x) < 1.5 and abs(p1.y - p2.y) > page_h * 0.045:
                vertical.append((p1.x, min(p1.y, p2.y), max(p1.y, p2.y)))

    if len(horizontal) < 2 or len(vertical) < 2:
        return []

    xs = cluster_numbers([line[0] for line in vertical] + [line[0] for line in horizontal] + [line[1] for line in horizontal], 3)
    ys = cluster_numbers([line[2] for line in horizontal] + [line[1] for line in vertical] + [line[2] for line in vertical], 3)

    rects = []
    for y0, y1 in zip(ys, ys[1:]):
        for x0, x1 in zip(xs, xs[1:]):
            rect = fitz.Rect(x0, y0, x1, y1)
            if is_reasonable_card(rect, page):
                rects.append(rect)

    return dedupe_rects(rects)


def has_name_marker(text):
    return any(marker in text for marker in NAME_MARKERS)


def detect_text_grid(page):
    blocks = page.get_text("dict").get("blocks", [])
    points = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if has_name_marker(text):
                    x0, y0, _, _ = span["bbox"]
                    if y0 > page.rect.height * 0.075:
                        points.append((x0, y0))

    if len(points) < 3:
        return []

    xs = cluster_numbers([p[0] for p in points], 12)
    ys = cluster_numbers([p[1] for p in points], 12)
    if len(xs) < 2 or len(ys) < 2:
        return []

    xs = sorted(xs)[:3]
    row_gap = (ys[1] - ys[0]) if len(ys) > 1 else page.rect.height * 0.09
    col_gap = (xs[1] - xs[0]) if len(xs) > 1 else page.rect.width * 0.285
    card_w = min(col_gap, page.rect.width * 0.31)
    card_h = min(row_gap, page.rect.height * 0.1)
    y_offset = max(12, card_h * 0.29)

    rects = []
    for y in ys:
        for x in xs:
            rect = fitz.Rect(x - 3, y - y_offset, x - 3 + card_w, y - y_offset + card_h)
            if is_reasonable_card(rect, page):
                rects.append(rect)

    return dedupe_rects(rects)


def fallback_grid(page):
    page_w = page.rect.width
    page_h = page.rect.height
    cols = 3
    rows = 10 if page_h < 820 else 11
    start_x = page_w * 0.058
    start_y = page_h * 0.09
    card_w = page_w * 0.284
    card_h = page_h * 0.0915

    rects = []
    for row in range(rows):
        y0 = start_y + row * card_h
        if y0 + card_h > page_h - page_h * 0.02:
            continue
        for col in range(cols):
            x0 = start_x + col * card_w
            rects.append(fitz.Rect(x0, y0, x0 + card_w, y0 + card_h))
    return rects


def projection_line_clusters(values, threshold, tolerance):
    indexes = [index for index, value in enumerate(values) if value >= threshold]
    clusters = []
    for index in indexes:
        if not clusters or index - clusters[-1][-1] > tolerance:
            clusters.append([index])
        else:
            clusters[-1].append(index)

    result = []
    for cluster in clusters:
        best_index = max(cluster, key=lambda item: values[item])
        center = (cluster[0] + cluster[-1]) / 2
        result.append((center, float(values[best_index])))
    return result


def detect_image_grid(page_info, page_index, pix):
    if cv2 is None or np is None:
        return []

    try:
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        dark = (gray < 170).astype(np.uint8)

        row_counts = dark.sum(axis=1)
        row_smooth = np.convolve(row_counts, np.ones(3) / 3, mode="same")
        row_candidates = projection_line_clusters(
            row_smooth,
            threshold=page_info["width"] * 0.25,
            tolerance=5,
        )
        row_candidates = cluster_weighted_positions(row_candidates, tolerance=8)
        row_candidates = [
            item for item in row_candidates
            if page_info["height"] * 0.075 < item[0] < page_info["height"] * 0.94
        ]
        y_lines = find_even_sequence(
            row_candidates,
            min_len=3,
            min_gap=page_info["height"] * 0.07,
            max_gap=page_info["height"] * 0.115,
            tolerance=page_info["height"] * 0.018,
            prefer_earlier=True,
        )

        if len(y_lines) < 3:
            return []

        table_y0 = max(0, int(min(y_lines) - 12))
        table_y1 = min(page_info["height"], int(max(y_lines) + 12))
        column_counts = dark[table_y0:table_y1, :].sum(axis=0)
        column_smooth = np.convolve(column_counts, np.ones(3) / 3, mode="same")
        column_candidates = projection_line_clusters(
            column_smooth,
            threshold=max(20, (table_y1 - table_y0) * 0.28),
            tolerance=5,
        )
        column_candidates = cluster_weighted_positions(column_candidates, tolerance=10)
        x_lines = find_even_sequence(
            column_candidates,
            min_len=4,
            min_gap=page_info["width"] * 0.20,
            max_gap=page_info["width"] * 0.34,
            tolerance=page_info["width"] * 0.03,
            prefer_earlier=True,
        )

        if len(x_lines) < 4:
            return []

        x_lines = x_lines[:4]
        boxes = []
        box_index = 0
        for top, bottom in zip(y_lines, y_lines[1:]):
            height = bottom - top
            if height < page_info["height"] * 0.045:
                continue

            for left, right in zip(x_lines, x_lines[1:]):
                width = right - left
                if width < page_info["width"] * 0.16:
                    continue

                pad = 2
                x = clamp_number(left - pad, 0, page_info["width"] - MIN_BOX_SIZE)
                y = clamp_number(top - pad, 0, page_info["height"] - MIN_BOX_SIZE)
                x2 = clamp_number(right + pad, x + MIN_BOX_SIZE, page_info["width"])
                y2 = clamp_number(bottom + pad, y + MIN_BOX_SIZE, page_info["height"])
                boxes.append({
                    "id": f"p{page_index}-img-{box_index}",
                    "pageIndex": page_index,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "width": round(x2 - x, 2),
                    "height": round(y2 - y, 2),
                    "source": "image-grid",
                })
                box_index += 1

        return boxes
    except Exception:
        return []


def clamp_number(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def detect_boxes_for_page(page, page_info, page_index, pix, fallback_allowed):
    source = "rectangles"
    rects = detect_rectangles(page)

    if len(rects) < 3:
        source = "lines"
        rects = detect_line_grid(page)

    if len(rects) < 3:
        source = "text"
        rects = detect_text_grid(page)

    if len(rects) < 3:
        image_boxes = detect_image_grid(page_info, page_index, pix)
        if len(image_boxes) >= 3:
            return image_boxes

    if len(rects) < 3 and fallback_allowed:
        source = "fallback-grid"
        rects = fallback_grid(page)

    rects = dedupe_rects(rects)
    rects = sorted(rects, key=lambda r: (round(r.y0, 1), round(r.x0, 1)))
    return [
        rect_to_box(rect, page_info, page_index, box_index, source)
        for box_index, rect in enumerate(rects)
    ]


def likely_card_start_page(doc):
    for index, page in enumerate(doc):
        text = page.get_text("text")
        if has_name_marker(text) and index > 0:
            return index
        if len(detect_rectangles(page)) >= 3 or len(detect_line_grid(page)) >= 3:
            return index
    return 2 if len(doc) > 2 else 0


def extract_polling_station(doc):
    try:
        text = "\n".join(doc[i].get_text("text") for i in range(min(3, len(doc))))
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if any(marker in line for marker in POLLING_MARKERS):
                if ":" in line and len(line.split(":", 1)[1].strip()) > 3:
                    return line.split(":", 1)[1].strip()
                for candidate in lines[index + 1:index + 6]:
                    if len(candidate) > 3 and not candidate.isdigit():
                        return candidate
    except Exception:
        pass
    return ""


def summarize_grid(boxes):
    if not boxes:
        return {
            "cols": 3,
            "rows": 10,
            "gapX": 0,
            "gapY": 0,
            "cardWidth": 480,
            "cardHeight": 200,
        }

    first_page = boxes[0]["pageIndex"]
    page_boxes = [box for box in boxes if box["pageIndex"] == first_page]
    rows = cluster_numbers([box["y"] for box in page_boxes], 18)
    cols = cluster_numbers([box["x"] for box in page_boxes], 18)
    card_width = sum(box["width"] for box in page_boxes) / len(page_boxes)
    card_height = sum(box["height"] for box in page_boxes) / len(page_boxes)

    gap_x = 0
    if len(cols) > 1:
        gap_x = max(0, (cols[1] - cols[0]) - card_width)

    gap_y = 0
    if len(rows) > 1:
        gap_y = max(0, (rows[1] - rows[0]) - card_height)

    return {
        "cols": min(6, max(1, len(cols))),
        "rows": min(20, max(1, len(rows))),
        "gapX": round(gap_x, 2),
        "gapY": round(gap_y, 2),
        "cardWidth": round(card_width, 2),
        "cardHeight": round(card_height, 2),
    }


def extract_pdf_data(pdf_path):
    doc = fitz.open(pdf_path)
    start_page = likely_card_start_page(doc)
    pages = []
    boxes = []

    for page_index, page in enumerate(doc):
        page_info, pix = render_page(page)
        pages.append({
            "index": page_index,
            "pageNumber": page_index + 1,
            "width": page_info["width"],
            "height": page_info["height"],
            "pdfWidth": round(page.rect.width, 2),
            "pdfHeight": round(page.rect.height, 2),
            "image": page_info["image"],
        })

        page_boxes = detect_boxes_for_page(
            page,
            page_info,
            page_index,
            pix,
            fallback_allowed=page_index >= start_page,
        )
        boxes.extend(page_boxes)

    polling_station = extract_polling_station(doc)
    grid_defaults = summarize_grid(boxes)
    doc.close()

    return {
        "mode": "calibrate",
        "pollingStation": polling_station,
        "pages": pages,
        "boxes": boxes,
        "gridDefaults": grid_defaults,
        "cardStartPage": start_page,
        "summary": {
            "pageCount": len(pages),
            "boxCount": len(boxes),
            "previewDpi": PREVIEW_DPI,
        },
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: extractor.py <input.pdf> <output.json>"}))
        sys.exit(1)

    try:
        data = extract_pdf_data(sys.argv[1])
        with open(sys.argv[2], "w", encoding="utf-8") as output:
            json.dump(data, output, ensure_ascii=False, separators=(",", ":"))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
