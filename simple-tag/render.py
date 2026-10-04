# 简易角标：半透明箭头暗条 + 粗斜体白字 + 蓝色 V 形箭头，60fps 透明通道 ProRes4444
# 用法: python3 render.py ["角标文字"] [topleft|bottomleft|center]
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT = sys.argv[1] if len(sys.argv) > 1 else "Shot on OPPO Find X10 Pro Max"
LAYOUT = sys.argv[2] if len(sys.argv) > 2 else "topleft"   # topleft / bottomleft / center

W, H = 3840, 2160      # 4K 输出
FPS = 60
ANIM_END = 1.2          # 动效结束时刻(秒)
HOLD = 10.8             # 之后静止时长
TOTAL_F = round((ANIM_END + HOLD) * FPS)   # 720 帧 = 12s

SS = 2                  # 超采样
K = 1.4 if LAYOUT != "center" else 4.0     # 参考图(760x162)坐标 -> 成片像素的缩放
MARGIN = 60             # 贴边模式离画面边缘的距离(4K像素)
OX, OY = 0, 0           # 由 layout() 按静止帧内容包围盒自动算

BAND = (22, 22, 24, 180)    # 参考图里暗条约 65-70% 不透明，透出底下画面
RED = (30, 110, 255, 255)   # 蓝箭头，和素材来源角标的蓝钥匙同色 #1E6EFF
WHITE = (255, 255, 255, 255)

# 字体 SIL OFL 可免费商用：得意黑 Smiley Sans Oblique，中英文通用(中文另做仿斜)
FONT_DIR = os.path.join(HERE, "fonts")
_HAS_CJK = any("⺀" <= ch <= "鿿" or "＀" <= ch <= "￯" for ch in TEXT)
FONT = ImageFont.truetype(os.path.join(FONT_DIR, "SmileySans-Oblique.ttf"), int(36 * K * SS))


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
def text_img(text, font):
    l, t, r, b = font.getbbox(text)
    pad = int(6 * K * SS)
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=WHITE)
    if _HAS_CJK:  # 得意黑只有英文是斜体，中文字形基本直立，水平错切 ~12° 仿斜
        sh = 0.21
        w2 = int(im.width + im.height * sh)
        im = im.transform((w2, im.height), Image.AFFINE, (1, sh, -im.height * sh, 0, 1, 0), Image.BICUBIC)
    return im, pad


T_TEXT, _PAD = text_img(TEXT, FONT)
TEXT_X, TEXT_CY = 57, 74            # 参考图：文字左缘 x=57，竖直中心 y≈74
tw_ref = (T_TEXT.width - 2 * _PAD) / (K * SS)
R = TEXT_X + tw_ref                 # 文字右缘(参考坐标)，暗条/箭头按文字宽度自适应

# 暗条：左边 "/" 斜切，右边是跟斜体同向倾斜的箭头尖 (参考图 y=26..126，尖在 y≈72)
# 参考图右端：上角 x=622、尖 x=650、下角 x=604，下边比上边短，两条斜边与蓝箭头平行
TOP, MID, BOT = 26, 72, 126
BAND_POLY = [P(57, TOP), P(R, TOP), P(R + 28, MID), P(R - 18, BOT), P(27, BOT)]
# 文字遮罩：比暗条略宽，滑入时只在暗条范围内出现
TEXT_CLIP = [P(57, 0), P(R + 60, 0), P(R + 60, 162), P(20, 162)]
# 蓝色 V 形箭头(粗，同样倾斜)：外沿尖 x≈R+86，内沿尖 x≈R+57
CHEV = [P(R + 27, 20), P(R + 55, 20), P(R + 86, 72), P(R + 42, 125), P(R + 10, 125), P(R + 57, 72)]
LW, LH = int((R + 110) * K * SS), int(162 * K * SS)


def poly_layer(poly, fill, dx=0):
    im = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(x + dx, y) for x, y in poly], fill=fill)
    return im


BAND_FULL = poly_layer(BAND_POLY, BAND)


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

    # 1. 暗条：箭头尖带着暗条从左往右伸出 (0.05 - 0.55s)
    pb = expo_out(seg(t, 0.05, 0.55))
    if pb > 0:
        full_w = (R + 28 - 27) * K * SS
        dx = -(1 - pb) * full_w
        layer = poly_layer(BAND_POLY, BAND, dx)
        m = Image.new("L", (LW, LH), 0)   # 左端斜边不动，只露出 >= 左斜边的部分
        ImageDraw.Draw(m).polygon([P(57, TOP), (LW, P(0, TOP)[1]), (LW, P(0, BOT)[1]), P(27, BOT)], fill=255)
        clipped = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
        clipped.paste(layer, (0, 0), Image.fromarray(np.minimum(np.array(m), np.array(layer.split()[3]))))
        im.alpha_composite(clipped)

    # 2. 文字：由左滑入，裁在暗条范围内 (0.25 - 0.85s)
    p = expo_out(seg(t, 0.25, 0.85))
    if p > 0:
        txt = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
        x = P(TEXT_X, 0)[0] - _PAD - (1 - p) * 120 * K * SS
        y = P(0, TEXT_CY)[1] - T_TEXT.height / 2
        paste_alpha(txt, T_TEXT, (x, y), min(1, p * 1.5))
        tm = Image.new("L", (LW, LH), 0)
        ImageDraw.Draw(tm).polygon(TEXT_CLIP, fill=255)
        ta = np.array(txt.split()[3]).astype(np.float32) * (np.array(tm) / 255.0)
        txt.putalpha(Image.fromarray(ta.astype(np.uint8)))
        im.alpha_composite(txt)

    # 3. 蓝箭头：跟在暗条尖后面冲出，回弹落位 + 一次轻微 "顶一下" (0.35 - 0.95s)
    pc = seg(t, 0.35, 0.80)
    if pc > 0:
        dx = -(1 - back_out(pc, 2.2)) * 70 * K * SS
        nudge = seg(t, 0.85, 1.15)          # 落位后向右轻顶一下再回来，像在指向
        dx += np.sin(nudge * np.pi) * 8 * K * SS
        paste_alpha(im, poly_layer(CHEV, RED, dx), (0, 0), min(1, pc * 3))

    # 合到整屏
    small = im.resize((LW // SS, LH // SS), Image.LANCZOS)
    full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    full.alpha_composite(small, (OX, OY))
    return full


def premul(img):
    # RGB 乘以 alpha：边缘半透明像素不带满亮度颜色，剪辑软件里叠加不出白边
    a = np.asarray(img).astype(np.uint16)
    a[..., :3] = (a[..., :3] * a[..., 3:4] + 127) // 255
    return a.astype(np.uint8).tobytes()


def layout():
    # 以最终静止画面的可见内容为准定位，动效中的回弹不影响位置
    global OX, OY
    OX, OY = 0, 0
    l, t, r, b = frame(ANIM_END).split()[3].getbbox()
    if LAYOUT == "topleft":
        OX, OY = MARGIN - l, MARGIN - t
    elif LAYOUT == "bottomleft":
        OX, OY = MARGIN - l, H - MARGIN - b
    else:
        OX, OY = (W - (r - l)) // 2 - l, (H - (b - t)) // 2 - t


def main():
    tag = {"topleft": "左上", "bottomleft": "左下", "center": "居中"}[LAYOUT]
    out = os.path.join(HERE, f"简易角标_{tag}_4K60_透明ProRes4444.mov")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
           "-alpha_bits", "16", "-vendor", "apl0", out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    anim_f = int(ANIM_END * FPS)
    layout()
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
