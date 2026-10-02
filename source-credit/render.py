# 素材来源角标：蓝钥匙 + 斜切暗条 + 标题/署名 + 点阵，60fps 透明通道 ProRes4444
# 用法: python3 render.py ["署名文字"]
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TITLE = "素材来源"
NAME = sys.argv[1] if len(sys.argv) > 1 else "Daniel Arenson"

W, H = 3840, 2160      # 4K 输出
FPS = 60
ANIM_END = 1.3          # 动效结束时刻(秒)
HOLD = 10.7             # 之后静止时长
TOTAL_F = round((ANIM_END + HOLD) * FPS)   # 720 帧 = 12s

SS = 2                  # 超采样
LAYOUT = "topleft"      # "topleft" 左上角 / "center" 正中
K = 1.2 if LAYOUT == "topleft" else 4.6   # 参考图(698x256)坐标 -> 成片像素的缩放
MARGIN = 40            # 左上角模式离画面边缘的距离(4K像素, 等比缩放到1080p时间线=一半)
OX, OY = 0, 0           # 由 main() 按静止帧内容包围盒自动算

BLUE = (30, 110, 255)
BAND = (18, 18, 20, 225)
WHITE = (255, 255, 255, 255)

# 字体均为 SIL OFL 开源授权，可免费商用：思源黑体(fonts/) + Poppins
FONT_DIR = os.path.join(HERE, "fonts")
CN_TITLE = os.path.join(FONT_DIR, "SourceHanSansCN-Heavy.otf")
CN_BODY = os.path.join(FONT_DIR, "SourceHanSansCN-Bold.otf")
F_CN = ImageFont.truetype(CN_TITLE, int(52 * K * SS))
# 署名含中日韩字符时 Poppins 没有字形(会显示成方框)，改用思源黑体
_HAS_CJK = any("\u2e80" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef" for ch in NAME)
F_EN = (ImageFont.truetype(CN_BODY, int(38 * K * SS)) if _HAS_CJK
        else ImageFont.truetype(os.path.join(FONT_DIR, "Poppins-Bold.ttf"), int(40 * K * SS)))

# 局部画布(参考图坐标系)尺寸
LW, LH = int(698 * K * SS), int(256 * K * SS)


def P(x, y):  # 参考坐标 -> 超采样局部像素
    return (x * K * SS, y * K * SS)


# ---------- 缓动 ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def expo_out(x):
    return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def back_out(x, s=1.7):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


# ---------- 静态素材 ----------
BAND_POLY = [P(88, 88), P(562, 88), P(514, 195), P(70, 195)]   # 上沿压在标题中线


def band_layer():
    im = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon(BAND_POLY, fill=BAND)
    return im


def key_sprite():
    # 竖放钥匙(环在上、齿在下)，之后旋转成闪电那样的 "/" 斜向
    s = K * SS * 1.15
    w, h = int(70 * s), int(190 * s)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = BLUE + (255,)
    cx = w / 2
    r_out, ring = 31 * s, 13 * s
    d.ellipse((cx - r_out, 4 * s, cx + r_out, 4 * s + 2 * r_out), fill=c)
    d.ellipse((cx - r_out + ring, 4 * s + ring, cx + r_out - ring, 4 * s + 2 * r_out - ring), fill=(0, 0, 0, 0))
    sw = 8 * s
    d.rounded_rectangle((cx - sw, 4 * s + 2 * r_out - 4 * s, cx + sw, h - 4 * s), radius=5 * s, fill=c)
    # 两个齿，朝右
    d.rectangle((cx + sw - 1, h - 46 * s, cx + 30 * s, h - 32 * s), fill=c)
    d.rectangle((cx + sw - 1, h - 22 * s, cx + 24 * s, h - 8 * s), fill=c)
    return im


KEY = key_sprite()
KEY_POS = P(84, 130)     # 钥匙中心
KEY_ROT = -28            # 顺时针倾斜成 "/"

# 点阵：两行交错，右上角
DOTS = []
for row, (y, xs) in enumerate([(62, [568, 582, 596, 610]), (76, [561, 575, 589, 603]),
                               (90, [554, 568, 582, 596]), (104, [540, 554, 568, 582])]):
    for i, x in enumerate(xs):
        DOTS.append((x, y, row + i))


def text_img(text, font):
    l, t, r, b = font.getbbox(text)
    im = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=font, fill=WHITE)
    return im


T_TITLE = text_img(TITLE, F_CN)
T_NAME = text_img(NAME, F_EN)
TITLE_POS = P(188, 66)
NAME_POS = P(172, 146)
if _HAS_CJK:  # 中文没有下伸部，按字面中心对到黑底下半部中间
    NAME_POS = (NAME_POS[0], P(0, 165)[1] - T_NAME.height / 2)
BAND_FULL = band_layer()
BAND_MASK = BAND_FULL.split()[3]


def paste_alpha(dst, src, xy, a):
    if a <= 0:
        return
    if a < 1:
        src = src.copy()
        src.putalpha(src.split()[3].point(lambda v: int(v * a)))
    dst.alpha_composite(src, (int(xy[0]), int(xy[1])))


# ---------- 单帧 ----------
def frame(t):
    im = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))

    # 1. 暗条从左往右擦出 (0.08 - 0.50s)
    pb = expo_out(seg(t, 0.08, 0.50))
    if pb > 0:
        x0, x1 = P(70, 0)[0], P(580, 0)[0]
        m = Image.new("L", (LW, LH), 0)
        ImageDraw.Draw(m).rectangle((0, 0, x0 + (x1 - x0) * pb, LH), fill=255)
        layer = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
        layer.paste(BAND_FULL, (0, 0), m)
        im.alpha_composite(layer)

    # 2. 文字：在暗条内由左滑入，标题先、署名后
    txt = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    for img, pos, a, b in ((T_TITLE, TITLE_POS, 0.28, 0.75), (T_NAME, NAME_POS, 0.40, 0.90)):
        p = expo_out(seg(t, a, b))
        dx = (1 - p) * -90 * K * SS
        paste_alpha(txt, img, (pos[0] + dx, pos[1]), min(1, p * 1.6))
    # 只显示暗条范围内的文字（暗条形状按横向放宽，避免裁到字）
    tm = Image.new("L", (LW, LH), 0)
    ImageDraw.Draw(tm).polygon([P(105, 20), P(640, 20), P(530, 215), P(70, 215)], fill=255)
    ta = np.array(txt.split()[3]).astype(np.float32) * (np.array(tm) / 255.0)
    txt.putalpha(Image.fromarray(ta.astype(np.uint8)))
    im.alpha_composite(txt)

    # 3. 点阵依次弹出 (0.55s 起)
    d = ImageDraw.Draw(im)
    for x, y, k in DOTS:
        p = back_out(seg(t, 0.55 + k * 0.035, 0.80 + k * 0.035), 2.5)
        if p <= 0:
            continue
        r = 2.6 * K * SS * p
        cx, cy = P(x, y)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE)

    # 4. 钥匙：从小放大 + 回弹旋转落位 (0.0 - 0.62s)，末尾一次扫光
    pk = seg(t, 0.0, 0.62)
    if pk > 0:
        sc = back_out(pk, 1.9)
        rot = KEY_ROT + (1 - expo_out(pk)) * -70
        kw, kh = KEY.size
        spr = KEY.resize((max(1, int(kw * sc)), max(1, int(kh * sc))), Image.BICUBIC)
        # 扫光
        ps = seg(t, 0.70, 1.15)
        if 0 < ps < 1:
            a = np.array(spr).astype(np.float32)
            hh, ww = a.shape[:2]
            yy, xx = np.mgrid[0:hh, 0:ww]
            pos = (xx * 0.5 + yy) / (ww * 0.5 + hh)
            g = np.clip(1 - np.abs(pos - (ps * 1.4 - 0.2)) / 0.09, 0, 1)[..., None]
            a[..., :3] = a[..., :3] * (1 - g * 0.75) + 255 * g * 0.75
            spr = Image.fromarray(a.astype(np.uint8))
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)  # PIL 正角度=逆时针
        a0 = min(1, pk * 4)
        paste_alpha(im, spr, (KEY_POS[0] - spr.width / 2, KEY_POS[1] - spr.height / 2), a0)

    # 合到整屏
    small = im.resize((LW // SS, LH // SS), Image.LANCZOS)
    full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    full.alpha_composite(small, (OX, OY))
    return full


def premul(img):
    # RGB 乘以 alpha：边缘半透明像素不再带满亮度颜色，剪辑软件里叠加不会出现白边
    a = np.asarray(img).astype(np.uint16)
    a[..., :3] = (a[..., :3] * a[..., 3:4] + 127) // 255
    return a.astype(np.uint8).tobytes()


def center_layout():
    # 以最终静止画面的可见内容为准居中，动效过程中的回弹不影响定位
    global OX, OY
    OX, OY = 0, 0
    l, t, r, b = frame(ANIM_END).split()[3].getbbox()
    if LAYOUT == "topleft":
        OX, OY = MARGIN - l, MARGIN - t
    else:
        OX, OY = (W - (r - l)) // 2 - l, (H - (b - t)) // 2 - t


def main():
    out = os.path.join(HERE, f"素材来源角标_{'左上' if LAYOUT == 'topleft' else '居中'}_4K60_透明ProRes4444.mov")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
           "-alpha_bits", "16", "-vendor", "apl0", out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    anim_f = int(ANIM_END * FPS)
    center_layout()
    still = None
    for i in range(TOTAL_F):
        if i < anim_f:
            buf = premul(frame(i / FPS))
        else:
            if still is None:
                f = frame(ANIM_END)
                f.save(os.path.join(HERE, "预览_静止帧.png"))
                still = premul(f)
            buf = still
        pr.stdin.write(buf)
    pr.stdin.close()
    if pr.wait() != 0:
        raise RuntimeError("FFmpeg 编码失败，请检查上方错误信息")
    print("done:", out, TOTAL_F, "frames")


if __name__ == "__main__":
    main()
