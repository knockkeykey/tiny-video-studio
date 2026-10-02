# Tiny Video Studio

用 Python 生成精致短动画：角标、素材署名和品牌转场。图形由代码绘制，DeepKey 音效由代码合成，无需下载参考图片、音效或调用付费生成接口。

## 三套动画

| 功能 | 预览 | 说明 | 默认输出 |
| --- | --- | --- | --- |
| 简易角标 | ![简易角标](simple-tag/assets/preview.png) | [simple-tag](simple-tag/README.md) | 4K / 60fps / 12 秒 / 透明 ProRes 4444 |
| 素材来源角标 | ![素材来源角标](source-credit/assets/preview.png) | [source-credit](source-credit/README.md) | 4K / 60fps / 12 秒 / 透明 ProRes 4444 |
| DeepKey 过场 | ![DeepKey](deepkey-transition/assets/preview.png) | [deepkey-transition](deepkey-transition/README.md) | 1080p / 60fps / 2.5 秒；透明 MOV、绿幕 MP4 和独立 WAV |

三个目录各自包含脚本、字体和字体许可证，角标之间无需相互引用。DeepKey 目录还包含绘图核心与音效模块。

## 安装

需要 Python **3.12 或更高版本**，以及加入 PATH 的 FFmpeg。FFmpeg 需支持 `prores_ks`、`libx264`、`aac`、`pcm_s24le`；FFmpeg 是独立程序，不包含在 Python 依赖中。

以下命令适用于 macOS / Linux。在已安装 Homebrew 的 macOS 上，可以先运行 `brew install ffmpeg`。

```bash
git clone https://github.com/knockkeykey/tiny-video-studio.git
cd tiny-video-studio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ffmpeg -version
```

Windows 可用 `py -m venv .venv` 创建环境，并在 PowerShell 中用 `.\.venv\Scripts\Activate.ps1` 激活，再执行同样的 pip 安装和 Python 运行命令。FFmpeg 仍需单独安装并加入 PATH。首次发布的实际渲染验证环境为 macOS；Linux、Windows 尚未实测。

## 运行

在仓库根目录、虚拟环境已激活时执行：

```bash
python simple-tag/render.py "Shot on OPPO Find X10 Pro Max" topleft
python source-credit/render.py "示例作者"
python deepkey-transition/render_v2.py
```

输出写入各自脚本所在目录；重复运行会覆盖同名文件。完整视频、音效、临时文件和运行缓存已加入 `.gitignore`。仓库包含源码、字体与静态预览，不含预渲染的完整成片。

## 使用与修改

详细参数、动画节奏、字体切换、输出文件名和剪辑软件里的透明通道设置，见各功能 README。默认参数保留原始动画效果；开源整理主要调整为目录内字体路径，并在 FFmpeg 编码失败时停止报错。

本仓库 DeepKey 源码输出 **60fps**。历史 30fps 导出文件不包含在仓库内；不同字体、依赖版本、编码器或渲染参数可能导致与历史文件存在差异，不保证逐字节相同。

## 首版验证

验证环境：macOS、Python 3.13.1、NumPy 2.5.3、Pillow 12.3.0、FFmpeg 8.1。

三套脚本均按默认参数完整渲染成功。使用 FFprobe 检查了视频尺寸、帧率、时长、编码及音轨；实际解码确认三个 MOV 含透明区域与不透明区域。另对两套角标做了中文单帧渲染，并检查了简易角标的左下与居中位置。仓库预览来自本次源码渲染，已查看静态效果。未在剪辑软件中做播放或透明叠加验收。

## 许可证

源码采用 [MIT](LICENSE)。字体采用各自的 SIL OFL 1.1，详见 [第三方字体说明](THIRD_PARTY_NOTICES.md) 和各目录 `fonts` 中的许可证文件。
