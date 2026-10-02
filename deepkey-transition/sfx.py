# 纯 numpy 合成的音效：whoosh / 钥匙清脆碰撞 / 扫光闪烁 / 蓄力 riser / 低频落点
# 不依赖外部音频素材
import math, wave
import numpy as np

SR = 48000
RNG = np.random.default_rng(7)


def _pan(mono, p):
    """等功率声像，p ∈ [-1, 1]，可为数组（随时间变化）。"""
    a = (np.asarray(p) + 1) * math.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)])


def _bandpass(x, fc, q):
    """时变 SVF 带通，fc 为逐样本中心频率数组。"""
    f = 2 * np.sin(np.pi * np.clip(fc, 20, SR / 6) / SR)
    k = 1.0 / q
    lo = bp = 0.0
    out = np.empty_like(x)
    for i in range(len(x)):
        hp = x[i] - lo - k * bp
        bp += f[i] * hp
        lo += f[i] * bp
        out[i] = bp
    return out * k


def _swell(n, peak=0.6, a=2.0, r=2.5):
    """0→1→0 的包络，peak 为峰值位置比例。"""
    u = np.linspace(0, 1, n)
    up = np.clip(u / peak, 0, 1) ** a
    down = np.clip((1 - u) / (1 - peak), 0, 1) ** r
    return np.where(u < peak, up, down)


def whoosh(dur, f0, f1, pan0=-0.6, pan1=0.6, q=1.2, peak=0.55, bright=0.0):
    n = int(dur * SR)
    fc = np.geomspace(f0, f1, n)
    noise = RNG.standard_normal(n)
    y = _bandpass(noise, fc, q)
    if bright:  # 叠一层更高、更窄的气流声
        y += bright * _bandpass(RNG.standard_normal(n), fc * 3.2, q * 2)
    y *= _swell(n, peak)
    return _pan(y, np.linspace(pan0, pan1, n))


def _bell(freqs, decays, amps, dur, detune=0.0):
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for f, d, a in zip(freqs, decays, amps):
        y += a * np.sin(2 * np.pi * f * (1 + detune) * t + RNG.uniform(0, 6.28)) * np.exp(-t / d)
    return y * np.clip(t / 0.002, 0, 1)  # 2ms 起音，去咔哒


def key_chime(dur=1.4):
    """钥匙落地：金属'叮'（非谐泛音）+ 柔和的 E6/B6 余韵。"""
    clink = [2350, 3740, 5410, 7300]
    L = _bell(clink, [0.06, 0.045, 0.03, 0.02], [0.6, 0.35, 0.25, 0.12], dur)
    R = _bell(clink, [0.06, 0.045, 0.03, 0.02], [0.6, 0.35, 0.25, 0.12], dur, detune=0.004)
    tone = [1318.5, 1975.5, 2637.0]
    L += _bell(tone, [0.5, 0.35, 0.2], [0.35, 0.22, 0.08], dur)
    R += _bell(tone, [0.5, 0.35, 0.2], [0.35, 0.22, 0.08], dur, detune=0.003)
    return np.stack([L, R])


def sparkle(dur=0.5, count=9, pan0=-0.5, pan1=0.6):
    """扫光：一串上行的细碎高音，跟着光带从左到右。"""
    out = np.zeros((2, int((dur + 0.4) * SR)))
    notes = [2637, 3136, 3520, 3951, 4699, 5274, 5920, 6272, 7040]
    for i in range(count):
        u = i / max(1, count - 1)
        st = int(u * dur * SR)
        b = _bell([notes[i % len(notes)], notes[i % len(notes)] * 2.01], [0.12, 0.05], [0.18, 0.05], 0.4)
        s = _pan(b * (0.55 + 0.45 * math.sin(math.pi * u)), lerp(pan0, pan1, u))
        out[:, st:st + s.shape[1]] += s[:, :out.shape[1] - st]
    return out


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = (t / dur) ** 2.2
    y = _bandpass(RNG.standard_normal(n), np.geomspace(500, 6000, n), 2.0) * env
    y += 0.12 * np.sin(2 * np.pi * np.cumsum(np.geomspace(220, 880, n)) / SR) * env
    return _pan(y, 0.0)


def thump(dur=0.6, f0=110, f1=42, amp=1.0):
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.05)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) * np.clip(t / 0.003, 0, 1)
    return _pan(y * amp, 0.0)


def lerp(a, b, x):
    return a + (b - a) * x


def reverb(x, rt=1.1, mix=0.18):
    n = int(rt * SR)
    t = np.arange(n) / SR
    ir = RNG.standard_normal((2, n)) * np.exp(-t * 6.9 / rt)
    ir[:, :int(0.012 * SR)] = 0  # 12ms 预延迟
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    m = x.shape[1] + n
    nfft = 1 << (m - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:, :x.shape[1]]
    return x * (1 - mix) + wet * mix * 2.2


def build(cues, total, path):
    """cues: [(开始秒, 立体声数组, 增益dB)]，混音后写 24bit WAV。"""
    buf = np.zeros((2, int(total * SR)))
    for st, sig, db in cues:
        i = int(st * SR)
        n = min(sig.shape[1], buf.shape[1] - i)
        buf[:, i:i + n] += sig[:, :n] * 10 ** (db / 20)
    buf = reverb(buf)
    buf = np.tanh(buf / np.abs(buf).max() * 1.4)       # 柔和限幅
    buf *= 10 ** (-1.0 / 20) / np.abs(buf).max()          # 峰值 -1 dBFS
    pcm = np.ascontiguousarray((buf.T * (2 ** 23 - 1)).astype(np.int32))
    raw = pcm.astype("<i4").view(np.uint8).reshape(-1, 4)[:, :3].tobytes()  # int32 取低 3 字节 = 24bit
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(raw)
