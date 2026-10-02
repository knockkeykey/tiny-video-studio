# DeepKey 过场动画 v2：60fps、更柔和的缓动、扫光、同步音效
# 输出: 绿幕 MP4(带音效) + ProRes 4444 透明通道 MOV(带音效) + 单独的音效 WAV(带混响尾巴)
# 用法: python3 render_v2.py
import math, os, subprocess
import numpy as np
from dk_core import *
import sfx

FPS = 60
DUR = 2.5
N_FRAMES = int(DUR * FPS)
SUB = 8  # 每帧子帧数（运动模糊）
GREEN = np.array([0, 1, 0], np.float32)

KEY_POS = (175, 0)
DEEP_POS = (-330, 38)
ICON_POS = (-240, 215)

# 转场色带
BAND_W = 3600
WIPE_T0, WIPE_T1 = 1.85, 2.45
SLANT_OFF = H / 2 * 0.45


# ---------- 各元素的运动曲线（时间单位：秒） ----------
def key_x(t):
    return lerp(-1600, KEY_POS[0], expo_out(seg(t, 0.0, 0.55)))


def deep_x(t):
    return lerp(-1100, DEEP_POS[0], expo_out(seg(t, 0.10, 0.65)))


def wipe_cx(t):
    return lerp(W + BAND_W / 2 + 700, -BAND_W / 2 - 700, sine_io(seg(t, WIPE_T0, WIPE_T1)))


def covered(t):
    """主色带是否已盖满整屏（左边缘越过画面左侧）。"""
    return seg(t, WIPE_T0, WIPE_T1) > 0 and wipe_cx(t) + SLANT_OFF - BAND_W / 2 <= 0


COVER_T = next(i / 1000 for i in range(int(WIPE_T0 * 1000), int(WIPE_T1 * 1000)) if covered(i / 1000))


def camera(t):
    breath = 1.3 * lerp(0.97, 1.03, sine_io(seg(t, 0.0, 1.8)))  # 缓慢推近
    z = seg(t, 1.75, 2.15) ** 3                                   # 末段加速冲镜头
    s = breath * lerp(1.0, 3.0, z)
    return M_t(W / 2 - 120 * z, H / 2 - 30 + 40 * z) @ M_s(s) @ M_t(-KEY_POS[0] * z * 0.35, 0) @ SHEAR


def icon_matrix(t):
    s_in = expo_out(seg(t, 0.25, 0.75))
    x, y = lerp(-800, ICON_POS[0], s_in), ICON_POS[1]
    rot = lerp(-30, 0, s_in)
    sy = 1.0
    fl = seg(t, 0.85, 1.25)
    if 0 < fl < 1:
        e = sine_io(fl)
        y -= 110 * math.sin(math.pi * fl)   # 起跳抛物线
        sy = math.cos(2 * math.pi * e)       # 绕长轴翻一圈，首尾慢中间快
        rot += 40 * math.sin(math.pi * fl)
        x += 40 * math.sin(math.pi * fl)
    land = seg(t, 1.25, 1.42)
    if 0 < land < 1:                         # 落地轻压，回弹
        sy *= 1 - 0.2 * math.sin(math.pi * land) * (1 - land)
    return M_t(x, y) @ M_r(rot) @ M_s(0.85, 0.85 * max(0.05, abs(sy)))


def shine_fn(t):
    u = seg(t, 1.35, 1.80)
    if not 0 < u < 1:
        return None
    p = lerp(150, 1800, sine_io(u))
    a = 0.8 * math.sin(math.pi * u)
    return lambda xx, yy: a * np.exp(-(((xx + (yy - H / 2) * 0.35) - p) / 55.0) ** 2)


def render(t):
    c = np.zeros((H, W, 4), np.float32)
    cam = camera(t)
    if not (covered(t) or t > WIPE_T1):
        sh = shine_fn(t)
        # KEY 拖影：用过去时刻的位置画浅色残影，速度越快越明显，静止时自然消失
        for lag, name, a0 in ((0.07, "key_p", 0.5), (0.035, "key_l", 0.75)):
            v = abs(key_x(t) - key_x(t - lag)) / 250
            blit(c, name, cam @ M_t(key_x(t - lag), KEY_POS[1]), a0 * clamp(v))
        blit(c, "key", cam @ M_t(key_x(t), KEY_POS[1]), shine=sh)
        dv = abs(deep_x(t) - deep_x(t - 0.05)) / 250
        blit(c, "deep", cam @ M_t(deep_x(t - 0.05), DEEP_POS[1]), 0.35 * clamp(dv) * seg(t, 0.1, 0.3))
        blit(c, "deep", cam @ M_t(deep_x(t), DEEP_POS[1]), sine_io(seg(t, 0.10, 0.30)), shine=sh)
        if t >= 0.25:
            blit(c, "icon", cam @ icon_matrix(t), sine_io(seg(t, 0.25, 0.40)), shine=sh)
    if 0 < seg(t, WIPE_T0, WIPE_T1) < 1:
        cx = wipe_cx(t)
        band(c, cx + BAND_W / 2 + 220, 240, BLUE_LIGHT, alpha=0.9)  # 前导细带
        band(c, cx, BAND_W, BLUE)                                   # 主色带
        band(c, cx - BAND_W / 2 - 160, 170, WHITE, alpha=0.85)      # 尾部白色高光
    return c


def build_sfx(path):
    cues = [
        (0.00, sfx.whoosh(0.50, 4500, 700, -0.8, 0.3, peak=0.22, bright=0.3), -4),   # KEY 冲入
        (0.08, sfx.whoosh(0.50, 2000, 400, -0.9, 0.0, peak=0.28), -9),               # DEEP 跟进
        (0.22, sfx.whoosh(0.35, 6000, 1800, -0.7, -0.2, q=2.0, peak=0.35), -15),     # 钥匙滑入
        (0.83, sfx.whoosh(0.40, 1500, 5000, -0.3, 0.1, q=1.8, peak=0.55), -15),      # 翻转
        (1.25, sfx.key_chime(), -6),                                                 # 落地 叮
        (1.25, sfx.thump(0.4, 170, 80, 0.5), -16),
        (1.35, sfx.sparkle(0.45), -13),                                              # 扫光
        (1.62, sfx.riser(COVER_T - 1.62), -13),                                      # 蓄力
        (COVER_T - 0.30, sfx.whoosh(0.60, 5000, 300, 0.9, -0.9, peak=0.5, bright=0.25), -2),  # 色带扫过
        (COVER_T, sfx.thump(), -3),                                                  # 盖满
    ]
    sfx.build(cues, DUR + 1.2, path)


def main():
    out = lambda n: os.path.join(HERE, n)
    wav = out("DeepKey过场_v2_音效.wav")
    build_sfx(wav)
    tmp_g, tmp_a = out(".tmp_green.mp4"), out(".tmp_alpha.mov")
    common = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-s", f"{W}x{H}", "-r", str(FPS)]
    p_g = subprocess.Popen(common + ["-pix_fmt", "rgb24", "-i", "-", "-c:v", "libx264", "-crf", "12",
                                     "-preset", "slow", "-pix_fmt", "yuv420p", tmp_g], stdin=subprocess.PIPE)
    p_a = subprocess.Popen(common + ["-pix_fmt", "rgba", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                                     "-pix_fmt", "yuva444p10le", tmp_a], stdin=subprocess.PIPE)
    for i in range(N_FRAMES):
        acc = np.zeros((H, W, 4), np.float32)
        for s in range(SUB):  # 快门 180°
            acc += render((i + (s / SUB - 0.5) * 0.5) / FPS)
        acc /= SUB
        a = acc[..., 3:4]
        p_g.stdin.write((np.clip(acc[..., :3] + GREEN * (1 - a), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        straight = np.where(a > 1e-4, acc[..., :3] / np.maximum(a, 1e-4), 0)
        p_a.stdin.write((np.clip(np.concatenate([straight, a], 2), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        print(f"\rframe {i + 1}/{N_FRAMES}", end="", flush=True)
    for p in (p_g, p_a):
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError("FFmpeg 编码失败，请检查上方错误信息")
    af = f"atrim=0:{DUR},afade=t=out:st={DUR - 0.12}:d=0.12"
    for src, dst, acodec in ((tmp_g, "DeepKey过场_v2_绿幕_1080p60.mp4", ["aac", "-b:a", "320k"]),
                             (tmp_a, "DeepKey过场_v2_透明通道_ProRes4444.mov", ["pcm_s24le"])):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", wav, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-af", af, "-c:a", *acodec, out(dst)], check=True)
        os.remove(src)
    print(f"\ncover at {COVER_T:.3f}s — done")


if __name__ == "__main__":
    main()
