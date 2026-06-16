import json
import cv2
import numpy as np
from pathlib import Path

MAP_JSON = "curved_screen_warp_map.json"
INPUT_IMAGE = "normal_image.png"
OUTPUT_IMAGE = "distorted_test.png"

# 如果你想强制输出尺寸，可以改这里。
# None = 使用 Blender JSON 里的 render_resolution。
FORCE_OUT_SIZE = None
# FORCE_OUT_SIZE = (1920, 1080)


def build_remap_from_triangles(json_path, in_w, in_h, out_w, out_h):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    map_x = np.full((out_h, out_w), -1, dtype=np.float32)
    map_y = np.full((out_h, out_w), -1, dtype=np.float32)

    for item in data["triangles"]:
        dst_uv = np.array(item["dst"], dtype=np.float32)
        src_uv = np.array(item["src"], dtype=np.float32)

        # dst_uv 来自 Blender camera view:
        # x: 0 left -> 1 right
        # y: 0 bottom -> 1 top
        #
        # OpenCV:
        # x: 0 left -> width
        # y: 0 top -> height

        dst = np.zeros((3, 2), dtype=np.float32)
        dst[:, 0] = dst_uv[:, 0] * (out_w - 1)
        dst[:, 1] = (1.0 - dst_uv[:, 1]) * (out_h - 1)

        # src_uv 来自 Blender UV:
        # u: 0 left -> 1 right
        # v: 0 bottom -> 1 top
        #
        # OpenCV image y 方向相反，所以这里也 flip v
        src = np.zeros((3, 2), dtype=np.float32)
        src[:, 0] = src_uv[:, 0] * (in_w - 1)
        src[:, 1] = (1.0 - src_uv[:, 1]) * (in_h - 1)

        # 计算从 output triangle 到 source triangle 的 affine
        affine = cv2.getAffineTransform(dst, src)

        x_min = max(int(np.floor(dst[:, 0].min())), 0)
        x_max = min(int(np.ceil(dst[:, 0].max())), out_w - 1)
        y_min = max(int(np.floor(dst[:, 1].min())), 0)
        y_max = min(int(np.ceil(dst[:, 1].max())), out_h - 1)

        if x_max < x_min or y_max < y_min:
            continue

        xs, ys = np.meshgrid(
            np.arange(x_min, x_max + 1, dtype=np.float32),
            np.arange(y_min, y_max + 1, dtype=np.float32)
        )

        local_mask = np.zeros(
            (y_max - y_min + 1, x_max - x_min + 1),
            dtype=np.uint8
        )

        local_poly = dst.copy()
        local_poly[:, 0] -= x_min
        local_poly[:, 1] -= y_min

        cv2.fillConvexPoly(
            local_mask,
            np.round(local_poly).astype(np.int32),
            255
        )

        src_x = affine[0, 0] * xs + affine[0, 1] * ys + affine[0, 2]
        src_y = affine[1, 0] * xs + affine[1, 1] * ys + affine[1, 2]

        region_x = map_x[y_min:y_max + 1, x_min:x_max + 1]
        region_y = map_y[y_min:y_max + 1, x_min:x_max + 1]

        inside = local_mask > 0
        region_x[inside] = src_x[inside]
        region_y[inside] = src_y[inside]

    return map_x, map_y


def main():
    json_path = Path(MAP_JSON)
    input_path = Path(INPUT_IMAGE)

    if not json_path.exists():
        raise FileNotFoundError(f"找不到 map json: {json_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"找不到输入图片: {input_path}")

    img = cv2.imread(str(input_path), cv2.IMREAD_COLOR)

    if img is None:
        raise RuntimeError(f"OpenCV 无法读取图片: {input_path}")

    in_h, in_w = img.shape[:2]

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if FORCE_OUT_SIZE is None:
        out_w, out_h = data["render_resolution"]
    else:
        out_w, out_h = FORCE_OUT_SIZE

    print("Input image:", in_w, "x", in_h)
    print("Output image:", out_w, "x", out_h)
    print("Triangles:", len(data["triangles"]))

    map_x, map_y = build_remap_from_triangles(
        MAP_JSON,
        in_w,
        in_h,
        out_w,
        out_h
    )

    warped = cv2.remap(
        img,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0)
    )

    cv2.imwrite(OUTPUT_IMAGE, warped)
    print("Saved:", OUTPUT_IMAGE)


if __name__ == "__main__":
    main()