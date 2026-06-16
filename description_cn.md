# Curved Screen Image / Video Warp 工具说明

这个工具用于把普通的图片或视频转换成 **CMA Lab curved screen / naked-eye 3D 屏幕需要的预畸变画面**。

整体逻辑是：

```text
Blender 里的 warped plane
        ↓
导出 triangle UV mapping JSON
        ↓
Python / OpenCV 根据 JSON 重新采样图片或视频
        ↓
输出 distorted image / distorted video
```

---

## 1. 这个工具解决什么问题

在 curved screen 项目里，正常画面不能直接播放到曲面屏上。  
因为屏幕是弯曲的，普通画面贴上去之后会被空间几何拉伸、压缩，观众看到的画面会变形。

所以我们需要提前生成一版 **pre-warped / pre-distorted** 的画面：

```text
正常画面 → 预畸变画面 → 播放到 curved screen → 观众看到正常画面
```

这个工具就是把正常图片或正常视频转换成这种预畸变版本。

---

## 2. Blender 里导出的是什么

Blender 文件里有一个已经根据 curved screen 关系生成的 flat plane。

这个 plane 的特点是：

- 它看起来是一个平面；
- 但它的网格不是均匀的；
- 每个 face 的面积、长短、比例都不一样；
- 这些不均匀网格本身就包含了 curved screen 的畸变关系。

导出的 `curved_screen_warp_map.json` 记录的是：

```text
输出画面里的三角形位置 dst
        ↓
应该去正常画面里的哪个 UV 位置 src 取颜色
```

每个 triangle 大概长这样：

```json
{
  "dst": [[0.1, 0.8], [0.2, 0.8], [0.15, 0.7]],
  "src": [[0.1, 0.9], [0.2, 0.9], [0.15, 0.8]]
}
```

含义是：

```text
distorted output 里的 dst triangle
从 normal image / video 里的 src triangle 采样颜色
```

这就是一种基于几何的 STMap / UV Remap。

---

## 3. 文件结构

建议项目文件夹这样整理：

```text
warp/
    curved_screen_warp_map.json
    normal_image.png
    input.mp4
    img_warp.py
    warp_video.py
```

其中：

| 文件 | 说明 |
|---|---|
| `curved_screen_warp_map.json` | 从 Blender 导出的 mapping 文件 |
| `normal_image.png` | 用来测试的普通图片 |
| `input.mp4` | 需要转换的普通视频 |
| `img_warp.py` | 图片畸变脚本 |
| `warp_video.py` | 视频畸变脚本 |

---

## 4. 安装依赖

在 PowerShell / Terminal 中运行：

```powershell
pip install opencv-python numpy imageio-ffmpeg
```

说明：

- `opencv-python`：用于图片 / 视频逐帧 remap；
- `numpy`：用于数组计算；
- `imageio-ffmpeg`：提供内置 FFmpeg，不需要手动配置系统 PATH。

---

## 5. 图片测试：img_warp.py

图片测试用于确认 mapping 是否正确。  
建议先测试图片，再处理完整视频。

### 输入

```text
normal_image.png
curved_screen_warp_map.json
```

### 输出

```text
distorted_test.png
```

### 运行方式

```powershell
cd "E:\CMA curved screen\warp"

python .\img_warp.py --input ".\normal_image.png" --map ".\curved_screen_warp_map.json" --output ".\distorted_test.png"
```

如果输出结果正确，`distorted_test.png` 应该看起来像 Blender 右边那个平面上的画面：  
正常图像会被拉伸、压缩，变成 curved screen 播放前需要的畸变画面。

---

## 6. 视频转换：warp_video.py

视频转换会逐帧读取普通 MP4，然后对每一帧使用同一份 mapping 进行 remap，最后输出 H.264 MP4。

### 输入

```text
input.mp4
curved_screen_warp_map.json
```

### 输出

```text
distorted_output.mp4
```

### 先测试前 120 帧

建议先只处理前几秒，确认方向和比例没问题：

```powershell
cd "E:\CMA curved screen\warp"

python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_test.mp4" --max-frames 120
```

### 处理完整视频

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output.mp4"
```

### 输出 4K 视频

如果最终屏幕需要 3840 × 2160，可以指定输出分辨率：

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output_4k.mp4" --width 3840 --height 2160
```

### 不复制音频

```powershell
python .\warp_video.py --input ".\input.mp4" --map ".\curved_screen_warp_map.json" --output ".\distorted_output.mp4" --no-audio
```

---

## 7. 参数说明

### img_warp.py 常用参数

| 参数 | 说明 |
|---|---|
| `--input` | 输入图片 |
| `--map` | Blender 导出的 JSON mapping |
| `--output` | 输出畸变图片 |
| `--width` | 可选，指定输出宽度 |
| `--height` | 可选，指定输出高度 |

### warp_video.py 常用参数

| 参数 | 说明 |
|---|---|
| `--input` | 输入视频 |
| `--map` | Blender 导出的 JSON mapping |
| `--output` | 输出畸变视频 |
| `--width` | 可选，指定输出宽度 |
| `--height` | 可选，指定输出高度 |
| `--crf` | H.264 质量，数值越低质量越高，默认 18 (0-51) |
| `--preset` | 编码速度，例如 `fast`、`medium`、`slow` |
| `--max-frames` | 只处理前 N 帧，用于测试 |
| `--no-audio` | 不复制原视频音频 |

---

## 8. 工作原理

OpenCV 的 `cv2.remap` 会为输出画面的每个像素寻找它在原始图片 / 视频中的采样位置。

这里的 mapping 来自 Blender 导出的 plane triangle 数据：

```text
dst triangle = 输出画面中的位置
src triangle = 原始画面中的 UV 采样位置
```

Python 会把每个 triangle 转成 affine transform：

```text
output pixel position → source pixel position
```

然后生成两张内部 remap 表：

```text
map_x = 每个输出像素对应的 source x
map_y = 每个输出像素对应的 source y
```

最后每一帧执行：

```python
warped = cv2.remap(frame, map_x, map_y)
```

这样就可以把任意普通图片或普通视频转换成相同 curved screen 所需的畸变版本。

---

## 9. 注意事项

### 1. 普通视频比例要和 Blender source camera 一致

比如 Blender 里左边 camera render 是 1920 × 1080，Unity 或其他软件输出的普通视频也最好是 1920 × 1080 或同样的 16:9 比例。

如果比例不同，变形结果可能会偏。

### 2. 输出分辨率要和最终屏幕播放分辨率一致

例如最终 curved screen 播放器需要 3840 × 2160，那么脚本输出也应该设置成：

```powershell
--width 3840 --height 2160
```

### 3. Blender 里的右侧 plane 必须完整出现在 output camera 中

如果导出的画面大面积黑色，通常说明：

- output camera 没有完整拍到右侧 plane；
- 或者 JSON 中部分 `dst` 坐标超出了 0 到 1。

### 4. 如果上下反了

在脚本中找到类似：

```python
dst[:, 1] = (1.0 - dst_uv[:, 1]) * (out_h - 1)
src[:, 1] = (1.0 - src_uv[:, 1]) * (in_h - 1)
```

尝试改成：

```python
dst[:, 1] = dst_uv[:, 1] * (out_h - 1)
src[:, 1] = src_uv[:, 1] * (in_h - 1)
```

有时候只需要改其中一行，具体取决于 Blender UV、camera view 和图片读取方向。

### 5. 如果结果左右反了

检查 `src[:, 0]` 或 `dst[:, 0]` 是否需要改成：

```python
src[:, 0] = (1.0 - src_uv[:, 0]) * (in_w - 1)
```

或：

```python
dst[:, 0] = (1.0 - dst_uv[:, 0]) * (out_w - 1)
```

---

## 10. 推荐流程

完整项目建议这样做：

```text
1. 在 Blender 中确认右侧 warped plane 映射正确
2. 导出 curved_screen_warp_map.json
3. 用 img_warp.py 测试 normal_image.png
4. 确认方向、比例、边界正确
5. 用 warp_video.py 处理 input.mp4
6. 输出 distorted_output.mp4
7. 在 curved screen 或测试环境中播放确认
```

---

## 11. 常见问题

### Q: 为什么不是直接在 Premiere 里做？

Premiere 更适合剪辑、四角变形、简单 lens distortion。  
这个项目需要的是基于 curved screen 几何关系的逐像素 remap，所以用 Python / OpenCV 更准确。

### Q: 这个方法和 AE Displacement Map 有什么区别？

AE Displacement Map 是相对位移：

```text
sourceUV = currentUV + offset
```

这个工具更接近 STMap / UV Remap：

```text
sourceUV = mapUV
```

所以它更适合复杂曲面屏的预畸变输出。

### Q: 换一个视频还需要重新导出 JSON 吗？

不需要。  
只要 curved screen 几何、Blender plane、camera、输出比例没有变，同一份 `curved_screen_warp_map.json` 可以用于任意普通图片或视频。

### Q: 什么情况下需要重新导出 JSON？

以下情况需要重新导出：

- curved screen 弧度变了；
- 右侧 warped plane 变了；
- output camera 位置或镜头变了；
- 最终屏幕比例 / mapping 范围变了；
- Blender 里的 UV 关系变了。
