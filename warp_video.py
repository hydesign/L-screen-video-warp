import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
import imageio_ffmpeg


def get_ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()


def build_remap_from_triangles(json_path, in_w, in_h, out_w, out_h):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    map_x = np.full((out_h, out_w), -1, dtype=np.float32)
    map_y = np.full((out_h, out_w), -1, dtype=np.float32)

    triangles = data["triangles"]

    for item in triangles:
        dst_uv = np.array(item["dst"], dtype=np.float32)
        src_uv = np.array(item["src"], dtype=np.float32)

        # Blender camera / UV: y 从下到上
        # OpenCV image: y 从上到下
        dst = np.zeros((3, 2), dtype=np.float32)
        dst[:, 0] = dst_uv[:, 0] * (out_w - 1)
        dst[:, 1] = (1.0 - dst_uv[:, 1]) * (out_h - 1)

        src = np.zeros((3, 2), dtype=np.float32)
        src[:, 0] = src_uv[:, 0] * (in_w - 1)
        src[:, 1] = (1.0 - src_uv[:, 1]) * (in_h - 1)

        # 跳过退化三角形
        area = cv2.contourArea(dst.astype(np.float32))
        if abs(area) < 0.001:
            continue

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

    return map_x, map_y, len(triangles)


def get_json_resolution(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "render_resolution" not in data:
        return None

    return int(data["render_resolution"][0]), int(data["render_resolution"][1])


def start_ffmpeg_encoder(output_path, out_w, out_h, fps, crf=18, preset="medium"):
    ffmpeg_exe = get_ffmpeg()

    cmd = [
        ffmpeg_exe,
        "-y",

        # input: raw frames from Python
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{out_w}x{out_h}",
        "-r", str(fps),
        "-i", "-",

        # output: H.264 mp4
        "-an",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]

    print("FFmpeg:", ffmpeg_exe)

    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE
    )


def copy_audio_if_possible(input_video, temp_video, final_output):
    ffmpeg_exe = get_ffmpeg()

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(temp_video),
        "-i", str(input_video),
        "-map", "0:v:0",
        "-map", "1:a?",
        "-c:v", "copy",
        "-c:a", "copy",
        "-shortest",
        str(final_output)
    ]

    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True, help="Input mp4 video")
    parser.add_argument("--map", required=True, help="Blender exported curved_screen_warp_map.json")
    parser.add_argument("--output", required=True, help="Output distorted mp4")

    parser.add_argument("--width", type=int, default=None, help="Output width")
    parser.add_argument("--height", type=int, default=None, help="Output height")

    parser.add_argument("--crf", type=int, default=18, help="H.264 quality. Lower = better. 18 high quality, 23 smaller")
    parser.add_argument("--preset", default="medium", help="x264 preset: ultrafast, fast, medium, slow")

    parser.add_argument("--no-audio", action="store_true", help="Do not copy audio")
    parser.add_argument("--max-frames", type=int, default=None, help="Only process first N frames for testing")

    args = parser.parse_args()

    input_video = Path(args.input)
    json_path = Path(args.map)
    final_output = Path(args.output)

    if not input_video.exists():
        raise FileNotFoundError(f"Cannot find input video: {input_video}")

    if not json_path.exists():
        raise FileNotFoundError(f"Cannot find map JSON: {json_path}")

    final_output.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(input_video))

    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot open video: {input_video}")

    in_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    in_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if not fps or fps <= 0:
        fps = 30

    if args.width is not None and args.height is not None:
        out_w, out_h = args.width, args.height
    else:
        json_res = get_json_resolution(json_path)
        if json_res is None:
            out_w, out_h = in_w, in_h
        else:
            out_w, out_h = json_res

    print("Input:", input_video)
    print("Input size:", in_w, "x", in_h)
    print("Output size:", out_w, "x", out_h)
    print("FPS:", fps)
    print("Total frames:", total_frames)

    print("Building remap...")
    map_x, map_y, tri_count = build_remap_from_triangles(
        json_path,
        in_w,
        in_h,
        out_w,
        out_h
    )

    print("Triangles:", tri_count)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_video = Path(tmpdir) / "distorted_no_audio.mp4"

        print("Encoding distorted video...")
        ffmpeg_proc = start_ffmpeg_encoder(
            temp_video,
            out_w,
            out_h,
            fps,
            crf=args.crf,
            preset=args.preset
        )

        frame_idx = 0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            warped = cv2.remap(
                frame,
                map_x,
                map_y,
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )

            ffmpeg_proc.stdin.write(warped.tobytes())

            frame_idx += 1

            if frame_idx % 30 == 0:
                if total_frames > 0:
                    print(f"Processed {frame_idx}/{total_frames}")
                else:
                    print(f"Processed {frame_idx}")

            if args.max_frames is not None and frame_idx >= args.max_frames:
                print(f"Stopped at max frames: {args.max_frames}")
                break

        cap.release()

        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()

        if ffmpeg_proc.returncode != 0:
            raise RuntimeError("FFmpeg encoding failed.")

        if args.no_audio:
            if final_output.exists():
                final_output.unlink()
            temp_video.replace(final_output)
        else:
            print("Copying audio from original video if available...")
            copy_audio_if_possible(input_video, temp_video, final_output)

    print("Done:", final_output)


if __name__ == "__main__":
    main()