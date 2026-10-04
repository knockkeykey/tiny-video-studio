# 简易角标

半透明斜切暗条、粗斜体白字、蓝色 V 形箭头。暗条展开、文字滑入，箭头回弹后轻推一次，适合拍摄设备说明或短提示。

![静态预览](assets/preview.png)

## 运行

先按[仓库安装说明](../README.md#安装)安装 Python 依赖和 FFmpeg。以下命令从仓库根目录执行，需已激活虚拟环境：

```bash
python simple-tag/render.py
python simple-tag/render.py "Shot on OPPO Find X10 Pro Max" topleft
python simple-tag/render.py "拍摄设备：示例相机" bottomleft
python simple-tag/render.py "示例文字" center
```

第一个参数是文字，默认 `Shot on OPPO Find X10 Pro Max`。第二个参数是位置，只接受 `topleft`（默认左上）、`bottomleft`（左下）、`center`（居中）。居中布局使用更大的角标。

## 输出

- `简易角标_左上_4K60_透明ProRes4444.mov`，或对应的左下、居中文件名。
- `预览_静止帧.png`，保留透明背景。
- 视频为 3840 × 2160、60fps、12 秒，前 1.2 秒动画，后 10.8 秒静止，无音轨。

文件写在 `simple-tag` 目录，同位置的后一次渲染会覆盖前一次文件。将透明 MOV 叠放在剪辑软件的视频上层轨道。RGB 已按 alpha 预乘；若软件需要手动指定 alpha 模式，选择 Premultiplied / 预乘。

## 修改

在 `render.py` 顶部可调整 `W`、`H`、`FPS`、`ANIM_END`、`HOLD`、`MARGIN`、颜色和缩放 `K`。入场缓动的具体时间定义在 `frame()` 内；单独调整总时长不会按比例改变全部动画节奏。修改分辨率或帧率后，输出文件名中的 `4K60` 需同步修改。

暗条宽度随文字宽度变化，过长文字仍可能超过画面。检测到中文相关字符时使用思源黑体 Bold，并做仿斜体；纯英文使用 Poppins BoldItalic。中文检测并非完整的 Unicode 字体回退，日文假名、韩文等字符尚未专门验证。

## 文件与字体

`render.py` 为完整动画脚本，`fonts` 含得意黑 Smiley Sans Oblique（中英文通用）及 OFL 许可证。字体从本目录读取，无需安装系统字体，也无需另一套角标目录或参考 PNG。

源码采用[项目 MIT 许可证](../LICENSE)，字体许可证见 `fonts/OFL-SmileySans.txt`。
