# Quick start

## notes
This program only support videos with h.264 mp4 format

## install dependencies

python -m pip install -r requirements.txt

## quick run 

```powershell
python .\warp_video.py --input ".\input\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\output\distorted_output.mp4"
```

## Parameters

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