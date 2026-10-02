# DeepKey 过场动画公共部分：画布参数、精灵、缓动、矩阵、合成
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "SmileySans-Oblique.ttf")  # 得意黑
W, H = 1920, 1080
SS = 2  # 精灵超采样，防止放大时糊掉

BLUE = (30, 110, 255)        # 主题蓝
BLUE_LIGHT = (90, 190, 255)  # 拖影浅蓝
BLUE_PALE = (170, 225, 255)  # 拖影最浅
WHITE = (255, 255, 255)


# ---------- 精灵 ----------
def text_sprite(text, size, color, stroke=0):
    f = ImageFont.truetype(FONT, size * SS)
    l, t, r, b = f.getbbox(text, stroke_width=stroke * SS)
    pad = 20 * SS
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=color + (255,),
                            stroke_width=stroke * SS, stroke_fill=color + (255,))
    return im


def key_sprite(color=WHITE):
    # 横放的钥匙：左边圆环 + 杆 + 两个齿，扮演原片里的滑板
    s = SS
    im = Image.new("RGBA", (300 * s, 90 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (255,)
    d.ellipse((6 * s, 12 * s, 72 * s, 78 * s), outline=c, width=15 * s)
    d.rounded_rectangle((64 * s, 36 * s, 290 * s, 54 * s), radius=8 * s, fill=c)
    d.rectangle((215 * s, 54 * s, 233 * s, 80 * s), fill=c)
    d.rectangle((250 * s, 54 * s, 268 * s, 72 * s), fill=c)
    return im


SPR = {
    "deep": text_sprite("DEEP", 250, WHITE, stroke=3),
    "key": text_sprite("KEY", 360, BLUE, stroke=4),
    "key_l": text_sprite("KEY", 360, BLUE_LIGHT, stroke=4),
    "key_p": text_sprite("KEY", 360, BLUE_PALE, stroke=4),
    "icon": key_sprite(),
}


# ---------- 缓动 ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def lerp(a, b, x):
    return a + (b - a) * x


def expo_out(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def sine_io(x):
    return 0.5 - 0.5 * math.cos(math.pi * x)


def back_out(x, s=1.4):
    x -= 1
    return 1 + x * x * ((s + 1) * x + s)


# ---------- 矩阵 ----------
def M_t(x, y):
    return np.array([[1, 0, x], [0, 1, y], [0, 0, 1]], np.float64)


def M_s(sx, sy=None):
    sy = sx if sy is None else sy
    return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], np.float64)


def M_r(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)


SHEAR = np.array([[1, -0.12, 0], [0, 1, 0], [0, 0, 1]], np.float64)  # 额外斜切，加速感


# ---------- 合成（premultiplied RGBA float 画布） ----------
def blit(canvas, name, M, alpha=1.0, shine=None):
    """把精灵(中心为原点)按屏幕变换 M 画到画布上；shine(xx, yy) 返回扫光强度。"""
    if alpha <= 0.003:
        return
    im = SPR[name]
    sw, sh = im.size
    full = M @ M_s(1 / SS) @ M_t(-sw / 2, -sh / 2)
    corners = full @ np.array([[0, sw, sw, 0], [0, 0, sh, sh], [1, 1, 1, 1]])
    x0, y0 = max(0, int(corners[0].min()) - 2), max(0, int(corners[1].min()) - 2)
    x1, y1 = min(W, int(corners[0].max()) + 2), min(H, int(corners[1].max()) + 2)
    if x1 <= x0 or y1 <= y0:
        return
    inv = np.linalg.inv(M_t(-x0, -y0) @ full)
    out = im.transform((x1 - x0, y1 - y0), Image.AFFINE, tuple(inv[:2].flatten()), resample=Image.BILINEAR)
    a = np.asarray(out, np.float32) / 255.0
    rgb, al = a[..., :3], a[..., 3:4] * alpha
    if shine is not None:
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        rgb = rgb + (1 - rgb) * shine(xx, yy)[..., None]
    region = canvas[y0:y1, x0:x1]
    region[..., :3] = rgb * al + region[..., :3] * (1 - al)
    region[..., 3:4] = al + region[..., 3:4] * (1 - al)


def band(canvas, cx, width, color, slant=0.45, alpha=1.0):
    """斜向色带（平行四边形），cx 为画面垂直中线处的中心 x。"""
    ys = np.arange(H, dtype=np.float32)[:, None]
    xs = np.arange(W, dtype=np.float32)[None, :]
    d = np.abs(xs - (cx + (H / 2 - ys) * slant)) - width / 2
    al = np.clip(0.5 - d / 3.0, 0, 1)[..., None] * alpha  # 边缘 3px 抗锯齿
    col = np.array(color, np.float32) / 255.0
    canvas[..., :3] = col * al + canvas[..., :3] * (1 - al)
    canvas[..., 3:4] = al + canvas[..., 3:4] * (1 - al)
