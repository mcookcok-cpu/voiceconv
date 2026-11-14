"""Voice changer lagu penuh -> suara Selena (kNN-VC, CPU). Pemakaian:
   python svc.py <lagu> <folder_keluar>            -> pisah vokal (demucs) + ubah suara + gabung -> hasil.mp3
   python svc.py --matchset                         -> bangun ulang set acuan suara Selena dari ref/*.wav
   Kemajuan ditulis ke <folder_keluar>/status.json"""
import sys, os, types, json, glob, subprocess, time, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'knn-vc'))
import numpy as np, torch, soundfile as sf, julius
torch.set_num_threads(2)

# ---- torchaudio tidak bisa dimuat (ABI beda) -> shim kecil yang cukup untuk matcher.py ----
ta = types.ModuleType('torchaudio'); fn = types.ModuleType('torchaudio.functional'); tr = types.ModuleType('torchaudio.transforms')
fn.resample = lambda x, orig_freq, new_freq: julius.resample_frac(x, orig_freq, new_freq)
fn.loudness = lambda x, sr: 10 * torch.log10((x ** 2).mean() + 1e-9) - 0.691
fn.gain = lambda x, db: x * (10 ** (db / 20))
tr.Vad = lambda **k: (lambda x: x)
ta.functional, ta.transforms = fn, tr
sys.modules.update({'torchaudio': ta, 'torchaudio.functional': fn, 'torchaudio.transforms': tr})
import hubconf  # dari knn-vc

SR = 16000
def load_mono(path, sr):
    x, s = sf.read(path, dtype='float32', always_2d=True)
    x = torch.from_numpy(x.mean(1))
    return x if s == sr else julius.resample_frac(x, s, sr)

_knn = None
def knn():
    global _knn
    if _knn is None: _knn = hubconf.knn_vc(pretrained=True, prematched=True, device='cpu')
    return _knn

@torch.inference_mode()
def feats(wav, chunk=20 * SR, cb=None):
    out = []; n = max(1, (len(wav) + chunk - 1) // chunk)
    for i in range(n):
        seg = wav[i * chunk:(i + 1) * chunk]
        if len(seg) < 4000: continue
        out.append(knn().get_features(seg[None]).cpu())
        if cb: cb((i + 1) / n)
    return torch.cat(out, 0)

def build_matchset():
    fs = []
    for p in sorted(glob.glob(os.path.join(HERE, 'ref', '*.wav'))):
        fs.append(feats(load_mono(p, SR)))
    ms = torch.cat(fs, 0); torch.save(ms, os.path.join(HERE, 'selena_matchset.pt'))
    print('matchset', tuple(ms.shape), '~%.0f dtk suara' % (ms.shape[0] * 0.02)); return ms

def matchset():
    p = os.path.join(HERE, 'selena_matchset.pt')
    return torch.load(p) if os.path.exists(p) else build_matchset()

@torch.inference_mode()
def convert(vocal16, ms, topk=4, cb=None):
    q = feats(vocal16, cb=(lambda f: cb(0.0 + 0.5 * f)) if cb else None)
    k = knn(); msn = ms / ms.norm(dim=-1, keepdim=True)
    outs = []; B = 800
    for i in range(0, len(q), B):
        qq = q[i:i + B]; sim = (qq / qq.norm(dim=-1, keepdim=True)) @ msn.T
        idx = sim.topk(topk, dim=-1).indices
        outs.append(ms[idx].mean(1))
        if cb: cb(0.5 + 0.2 * min(1, (i + B) / len(q)))
    of = torch.cat(outs, 0); wavs = []; V = 600
    for i in range(0, len(of), V):
        wavs.append(k.vocode(of[None, i:i + V]).cpu().squeeze())
        if cb: cb(0.7 + 0.3 * min(1, (i + V) / len(of)))
    return torch.cat(wavs, 0)

def status(d, stage, pct, **kw):
    json.dump({'stage': stage, 'pct': round(pct, 3), 't': time.time(), **kw}, open(os.path.join(d, 'status.json'), 'w'))

def mp3(path, wav, sr):
    import lameenc
    e = lameenc.Encoder(); e.set_bit_rate(192); e.set_in_sample_rate(sr); e.set_channels(2); e.set_quality(2)
    pcm = (np.clip(wav, -1, 1) * 32767).astype('<i2')
    open(path, 'wb').write(e.encode(pcm.tobytes()) + e.flush())

def run(song, outd):
    os.makedirs(outd, exist_ok=True); t0 = time.time()
    status(outd, 'pisah-vokal', 0.02)
    dm = os.path.join(outd, 'demucs')
    r = subprocess.run([sys.executable, '-m', 'demucs', '--two-stems=vocals', '-n', 'htdemucs', '-j', '2', '-o', dm, song], capture_output=True, text=True)
    stem = os.path.splitext(os.path.basename(song))[0]
    vp = glob.glob(os.path.join(dm, 'htdemucs', '*', 'vocals.wav')); ip = glob.glob(os.path.join(dm, 'htdemucs', '*', 'no_vocals.wav'))
    if not vp or not ip: status(outd, 'gagal', 0, err=(r.stderr or '')[-300:]); return 1
    status(outd, 'ubah-suara', 0.35)
    ms = matchset(); v16 = load_mono(vp[0], SR)
    conv = convert(v16, ms, cb=lambda f: status(outd, 'ubah-suara', 0.35 + 0.55 * f))
    status(outd, 'gabung', 0.92)
    inst, isr = sf.read(ip[0], dtype='float32', always_2d=True)
    if inst.shape[1] == 1: inst = np.repeat(inst, 2, 1)
    cv = julius.resample_frac(conv, SR, isr).numpy()
    ov = sf.read(vp[0], dtype='float32', always_2d=True)[0].mean(1)
    n = len(inst); cv = np.pad(cv, (0, max(0, n - len(cv))))[:n]
    g = float(np.clip((np.sqrt((ov ** 2).mean()) + 1e-6) / (np.sqrt((cv ** 2).mean()) + 1e-6), 0.4, 4.0))
    mix = inst + (cv * g)[:, None]
    mix = mix / max(1.0, float(np.abs(mix).max()) / 0.97)
    mp3(os.path.join(outd, 'hasil.mp3'), mix, isr)
    shutil.rmtree(dm, ignore_errors=True)
    status(outd, 'selesai', 1.0, detik=round(time.time() - t0), dur=round(n / isr, 1)); return 0

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--matchset': build_matchset(); sys.exit(0)
    sys.exit(run(sys.argv[1], sys.argv[2]))
