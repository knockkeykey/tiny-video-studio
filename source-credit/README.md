# 素材来源角标

蓝色钥匙、斜切暗条、“素材来源”标题、作者署名和点阵。钥匙旋转回弹，文字依次滑入，点阵弹出并加入一次扫光，适合给引用素材标注来源。

![静态预览](assets/preview.png)

## 运行

先按[仓库安装说明](../README.md#安装)安装 Python 依赖和 FFmpeg。以下命令从仓库根目录执行，需已激活虚拟环境：

```bash
python source-credit/render.py
python source-credit/render.py "Daniel Arenson"
python source-credit/render.py "示例作者"
```

第一个参数是署名，默认 `Daniel Arenson`。标题默认“素材来源”，可以在脚本顶部修改 `TITLE`。

## 位置与输出

默认左上角。如需居中，在 `render.py` 顶部将 `LAYOUT = "topleft"` 改为 `LAYOUT = "center"`，再重新运行；这个脚本的位置由代码配置，不能通过第二个命令行参数指定。

- `素材来源角标_左上_4K60_透明ProRes4444.mov`，或对应的居中文件名。
- `预览_静止帧.png`，保留透明背景。
- 视频为 3840 × 2160、60fps、12 秒，前 1.3 秒动画，后 10.7 秒静止，无音轨。

文件写在 `source-credit` 目录，同布局的后一次渲染会覆盖前一次文件。将透明 MOV 叠放在剪辑软件的视频上层轨道。RGB 已按 alpha 预乘；若软件需要手动指定 alpha 模式，选择 Premultiplied / 预乘。

## 修改

在脚本顶部可修改 `TITLE`、`LAYOUT`、`MARGIN`、颜色、缩放和输出规格。入场时间分段写在 `frame()` 内，调整总时长不会自动缩放全部动作。修改分辨率或帧率后，输出文件名中的 `4K60` 需同步修改。

署名检测到中文相关字符时使用思源黑体 Bold，否则使用 Poppins Bold。暗条及局部画布宽度固定，较长署名可能被裁切，需要缩小字体或调整画布和遮罩；不承诺任意长度都能自动适配。日文假名、韩文等字符的字体回退尚未专门验证。

## 文件与字体

`render.py` 为完整动画脚本。`fonts` 包含得意黑 Smiley Sans Oblique（标题与署名通用）及 OFL 许可证。无需安装系统字体或提供参考 PNG。

源码采用[项目 MIT 许可证](../LICENSE)，字体许可证见 `fonts/OFL-SmileySans.txt`。
