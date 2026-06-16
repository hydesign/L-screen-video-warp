# Curved Screen Image / Video Warp Tool

This tool converts normal images or videos into a **pre-distorted / pre-warped output** for CMA Lab L curved screen playback.

The overall workflow is:

```text
Warped plane in Blender
        ↓
Export triangle UV mapping as JSON
        ↓
Python / OpenCV remaps the image or video based on the JSON
        ↓
Output distorted image / distorted video
```

---

## 1. What problem does this solve?

For a curved screen project, a normal flat image or video should not be played directly on the curved screen.

Because the screen surface is curved, the image will be stretched and compressed by the screen geometry. The audience will see a distorted result if the content is not pre-corrected.

So the content needs to be converted in advance:

```text
Normal image / video
        ↓
Pre-distorted image / video
        ↓
Played on curved screen
        ↓
Audience sees the correct image
```

This tool performs that pre-distortion step.

---

## 2. What is exported from Blender?

The Blender scene contains a flat plane that has already been generated according to the curved screen geometry.

This plane has these characteristics:

- It is a flat output plane.
- Its grid is not uniform.
- Each face may have a different area, width, height, or proportion.
- This non-uniform mesh stores the distortion relationship needed for the curved screen.

The exported file:

```text
curved_screen_warp_map.json
```

stores this relationship:

```text
Destination triangle in the distorted output
        ↓
Source UV triangle in the normal image / video
```

Each triangle in the JSON looks like this:

```json
{
  "dst": [[0.1, 0.8], [0.2, 0.8], [0.15, 0.7]],
  "src": [[0.1, 0.9], [0.2, 0.9], [0.15, 0.8]]
}
```

Meaning:

```text
The dst triangle in the distorted output
samples color from the src triangle in the normal input image / video
```

This is essentially a geometry-based STMap / UV remap.

---

## 3. Recommended folder structure

A simple project folder can look like this:

```text
warp/
    curved_screen_warp_map.json
    normal_image.png
    input.mp4
    img_warp.py
    warp_video.py
```

| File | Description |
|---|---|
| `curved_screen_warp_map.json` | Mapping file exported from Blender |
| `normal_image.png` | Normal test image |
| `input.mp4` | Normal input video |
| `img_warp.py` | Image warp script |
| `warp_video.py` | Video warp script |

---

## 4. Install dependencies

Run this in PowerShell or Terminal:

```powershell
pip install opencv-python numpy imageio-ffmpeg
```

Dependency notes:

- `opencv-python`: image / video frame remapping
- `numpy`: array calculation
- `imageio-ffmpeg`: bundled FFmpeg executable, so you do not need to configure FFmpeg in the system PATH manually

---

## 5. Image test: img_warp.py

The image test is used to verify that the mapping is correct before processing the full video.

### Input

```text
normal_image.png
curved_screen_warp_map.json
```

### Output

```text
distorted_test.png
```

### Run command

```powershell
cd "E:\CMA curved screen\warp"

python .\img_warp.py --input ".\normal_image.png" --map ".\curved_screen_warp_map.json" --output ".\distorted_test.png"
```

If the mapping is correct, `distorted_test.png` should look similar to the image shown on the warped plane in Blender.

A circular object in the normal image may become stretched or compressed in the output. This is expected, because the output is the pre-warped image for curved screen playback.

---

## 6. Video conversion: warp_video.py

The video script reads the input MP4 frame by frame, applies the same remap to each frame, and then encodes the result as an H.264 MP4 file.

### Input

```text
input.mp4
curved_screen_warp_map.json
```

### Output

```text
distorted_output.mp4
```

### Test the first 120 frames

It is recommended to test a short segment first:

```powershell
cd "E:\CMA curved screen\warp"

python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_test.mp4" --max-frames 120
```

### Process the full video

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output.mp4"
```

### Export 4K video

If the final screen playback resolution is 3840 × 2160, specify the output resolution:

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output_4k.mp4" --width 3840 --height 2160
```

### Disable audio copy

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output.mp4" --no-audio
```

---

## 7. Parameters

### img_warp.py parameters

| Parameter | Description |
|---|---|
| `--input` | Input image |
| `--map` | Blender-exported JSON mapping file |
| `--output` | Output distorted image |
| `--width` | Optional output width |
| `--height` | Optional output height |

### warp_video.py parameters

| Parameter | Description |
|---|---|
| `--input` | Input video |
| `--map` | Blender-exported JSON mapping file |
| `--output` | Output distorted video |
| `--width` | Optional output width |
| `--height` | Optional output height |
| `--crf` | H.264 quality value. Lower means higher quality and larger file size. Default is 18 in this script |
| `--preset` | Encoding speed / compression preset, such as `fast`, `medium`, or `slow` |
| `--max-frames` | Only process the first N frames for testing |
| `--no-audio` | Do not copy audio from the original video |

---

## 8. CRF notes

This script encodes video using H.264 via `libx264`.

For `libx264`, the CRF scale is:

```text
0  = lossless, very large file
18 = very high quality, often visually close to lossless
23 = x264 default
51 = worst quality, smallest file
```

Common practical values:

| CRF | Typical use |
|---|---|
| `14–16` | Very high quality, large file |
| `18` | High quality, good for final output preview or production testing |
| `20–23` | Smaller file, still acceptable for many previews |
| `28+` | Low quality preview only |
| `51` | Maximum CRF value for x264, worst quality |

Example:

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output.mp4" --crf 18
```

Smaller file:

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output_small.mp4" --crf 23
```

Higher quality:

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output_hq.mp4" --crf 14
```

---

## 9. How it works

OpenCV `cv2.remap` creates an output image where each output pixel samples from a specific position in the input image.

The mapping comes from the triangle data exported from Blender:

```text
dst triangle = position in the distorted output
src triangle = UV sampling position in the normal input
```

For each triangle, the script calculates an affine transform:

```text
output pixel position → source pixel position
```

Then it builds two internal remap arrays:

```text
map_x = source x coordinate for every output pixel
map_y = source y coordinate for every output pixel
```

Each image frame is then processed with:

```python
warped = cv2.remap(frame, map_x, map_y)
```

This makes it possible to apply the same curved screen distortion to any normal image or video.

---

## 10. Important notes

### 1. The normal input aspect ratio should match the Blender source camera

For example, if the Blender source render is 1920 × 1080, the Unity render or input video should ideally also be 1920 × 1080 or at least the same 16:9 aspect ratio.

If the aspect ratio is different, the remap result may not align correctly.

### 2. The output resolution should match the final screen playback resolution

For example, if the curved screen player requires 3840 × 2160, run the script with:

```powershell
--width 3840 --height 2160
```

### 3. The warped plane in Blender must be fully visible to the output camera

If the result contains a large black area, common causes are:

- The output camera does not fully capture the warped plane.
- Some `dst` coordinates in the JSON are outside the 0–1 range.

### 4. If the result is vertically flipped

Find these lines in the script:

```python
dst[:, 1] = (1.0 - dst_uv[:, 1]) * (out_h - 1)
src[:, 1] = (1.0 - src_uv[:, 1]) * (in_h - 1)
```

Try changing them to:

```python
dst[:, 1] = dst_uv[:, 1] * (out_h - 1)
src[:, 1] = src_uv[:, 1] * (in_h - 1)
```

Depending on Blender UV direction, camera view direction, and image read direction, you may need to change only one of the two lines.

### 5. If the result is horizontally flipped

Check whether `src[:, 0]` or `dst[:, 0]` should be flipped:

```python
src[:, 0] = (1.0 - src_uv[:, 0]) * (in_w - 1)
```

or:

```python
dst[:, 0] = (1.0 - dst_uv[:, 0]) * (out_w - 1)
```

---

## 11. Recommended workflow

```text
1. Confirm the warped plane mapping in Blender
2. Export curved_screen_warp_map.json
3. Test normal_image.png with img_warp.py
4. Confirm direction, scale, and boundary
5. Process input.mp4 with warp_video.py
6. Export distorted_output.mp4
7. Test the output on the curved screen or preview environment
```

---

## 12. FAQ

### Q: Why not do this directly in Premiere?

Premiere is good for editing, corner pinning, perspective transforms, and simple lens distortion.

This project needs pixel-level remapping based on curved screen geometry, so Python / OpenCV is more accurate and more reusable.

### Q: How is this different from After Effects Displacement Map?

After Effects Displacement Map is generally based on relative pixel offset:

```text
sourceUV = currentUV + offset
```

This tool is closer to STMap / UV Remap:

```text
sourceUV = mapUV
```

That makes it more suitable for complex curved screen pre-distortion.

### Q: Do I need to export a new JSON for every new video?

No.

As long as the curved screen geometry, Blender warped plane, output camera, and output aspect ratio do not change, the same `curved_screen_warp_map.json` can be reused for different images and videos.

### Q: When do I need to export a new JSON?

You need to export a new JSON if any of the following changes:

- Curved screen geometry
- Warped plane geometry
- Output camera position or lens
- Final output aspect ratio or mapping range
- UV mapping relationship in Blender
