"""Felo Listener - always-on "Hey Felo" for Daniel's work PC (2026-10-25).

Say "Hey Felo" (or "Oye Felo"), then talk. Felo answers out loud through the PC speakers, then keeps listening a few
seconds for a follow-up (no wake word needed). "Stop" / "bye" / "para" / "gracias" ends the conversation.
"Hey Felo, stop listening" pauses; "Hey Felo, start listening" resumes.

Privacy: the microphone is checked ONLY on this PC by a tiny wake-word model (hey_felo.onnx, trained for Felo).
Nothing is recorded to disk and no audio leaves this PC until it hears "Hey Felo". After that, only what you say to
Felo goes to Felo HQ (your private Tailscale address) - the same as talking to Felo in Felo HQ.

It talks to Felo HQ the same way Felo HQ in the browser does (Tailscale signs you in):
  POST /api/hq/listen  speech -> text            POST /api/hq/ask  Felo answers (General chat)
  POST /api/hq/speak   text -> Felo's voice

  python felo_listener.py                  normal
  python felo_listener.py --devices        list microphones and speakers
  python felo_listener.py --mic 3          use microphone number 3
  python felo_listener.py --level          show the live wake-word score while you speak (to check the mic)
"""
import argparse, io, json, logging, os, queue, re, sys, tempfile, threading, time, urllib.error, urllib.request, wave
import numpy as np
import sounddevice as sd

FELO = "https://felo-orchestrator.tail0ff06a.ts.net:8443"
RATE = 16000
BLOCK = 1280                                   # 80 ms, what the wake-word model reads
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "hey_felo.onnx")
THRESHOLD = 0.3                                # tested 2026-10-26: unseen voices, clean speech ~2 in 3 caught
STOP = re.compile(r"^\W*(?:stop|bye|goodbye|that'?s all|thanks|thank you|para|adi[oó]s|gracias|listo)\W*$", re.I)
PAUSE = re.compile(r"\bstop listening\b|\bdeja de escuchar\b", re.I)
RESUME = re.compile(r"\bstart listening\b|\bempieza a escuchar\b|\bescucha de nuevo\b", re.I)
HOME = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "FeloListener")
os.makedirs(HOME, exist_ok=True)
logging.basicConfig(filename=os.path.join(HOME, "felo-listener.log"), level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("felo")


def say(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True); log.info(msg)


# ---------------- Felo HQ ----------------
def felo(path, body, ctype="application/json", timeout=120):
    data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode()
    req = urllib.request.Request(FELO + path, data=data, method="POST",
                                 headers={"Content-Type": ctype, "Origin": FELO, "User-Agent": "felo-listener/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return raw if r.headers.get_content_type().startswith("audio/") else json.loads(raw or b"{}")


def to_wav(pcm):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes((np.clip(pcm, -1, 1) * 32767).astype("<i2").tobytes())
    return buf.getvalue()


def transcribe(pcm):
    if pcm is None: return ""
    try: return (felo("/api/hq/listen", to_wav(pcm), "audio/wav", 90).get("text") or "").strip()
    except Exception as e: say("could not understand on Felo HQ: %s" % e); return ""


# ---------------- sound out ----------------
_mixer = None


def play_mp3(mp3):
    global _mixer
    if _mixer is None:
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame; pygame.mixer.init(); _mixer = pygame.mixer
    path = os.path.join(HOME, "reply.mp3")
    with open(path, "wb") as f: f.write(mp3)
    _mixer.music.load(path); _mixer.music.play()
    while _mixer.music.get_busy(): time.sleep(0.05)
    _mixer.music.unload()


def beep(kind="wake"):
    tones = {"wake": [(880, .08), (1320, .1)], "error": [(330, .25)], "pause": [(660, .1), (440, .14)], "no": [(440, .12)]}[kind]
    for hz, dur in tones:
        t = np.linspace(0, dur, int(RATE * dur), False)
        sd.play((0.22 * np.sin(2 * np.pi * hz * t) * np.hanning(t.size)).astype("float32"), RATE, blocking=True)


def speak(text):
    try: play_mp3(felo("/api/hq/speak", {"text": text[:1500]}, timeout=60))
    except Exception as e: say("Felo's voice is unavailable (%s). Reply: %s" % (e, text)); beep("error")


# ---------------- microphone ----------------
class Mic:
    """Continuous microphone; while Felo speaks, input is ignored (no echo)."""
    def __init__(self, device=None):
        self.q = queue.Queue(maxsize=600); self.muted = threading.Event()
        self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=BLOCK, device=device, callback=self._cb)
        self.stream.start()
        vals = [float(np.sqrt(np.mean(self.q.get() ** 2))) for _ in range(12)]
        self.floor = max(float(np.median(vals)), 0.002); say("microphone ready (noise level %.4f)" % self.floor)

    def _cb(self, data, frames, t, status):
        if not self.muted.is_set():
            try: self.q.put_nowait(data[:, 0].copy())
            except queue.Full: pass

    def block(self): return self.q.get()

    def flush(self):
        while not self.q.empty():
            try: self.q.get_nowait()
            except queue.Empty: break

    def utterance(self, wait=7.0, end_silence=0.9, max_len=20.0):
        """What you say next (float32 audio), or None if you say nothing within `wait` seconds."""
        thr = max(self.floor * 3.2, 0.012); pre = []; got = []; quiet = 0; start = time.time()
        while True:
            try: b = self.q.get(timeout=0.5)
            except queue.Empty:
                if time.time() - start > wait: return None
                continue
            loud = float(np.sqrt(np.mean(b ** 2))) > thr
            if not got:
                pre = (pre + [b])[-4:]
                if loud: got = pre[:]
                elif time.time() - start > wait: return None
                continue
            got.append(b); quiet = 0 if loud else quiet + 1
            if quiet * BLOCK / RATE >= end_silence or len(got) * BLOCK / RATE >= max_len:
                audio = np.concatenate(got)
                return audio if audio.size / RATE >= 0.4 else None


# ---------------- wake word (local only) ----------------
class Wake:
    def __init__(self):
        import openwakeword
        from openwakeword.model import Model
        try: openwakeword.utils.download_models(model_names=["embedding_model", "melspectrogram"])
        except Exception: pass
        self.m = Model(wakeword_models=[MODEL], inference_framework="onnx"); self.key = list(self.m.models)[0]
        say("wake-word model ready (%s)" % os.path.basename(MODEL))

    def score(self, block):
        return float(self.m.predict((np.clip(block, -1, 1) * 32767).astype(np.int16))[self.key])

    def reset(self): self.m.reset()


# ---------------- conversation ----------------
def ask(text):
    say("you: " + text)
    try: out = felo("/api/hq/ask", {"text": text, "thread": "general", "voice": True}, timeout=600)
    except urllib.error.HTTPError as e:
        say("Felo HQ refused (%s): %s" % (e.code, e.read()[:200])); beep("error"); return None
    except Exception as e: say("Felo HQ unreachable: %s" % e); beep("error"); return None
    reply = (out.get("reply") or "").strip()
    say("felo: " + reply); return reply


def conversation(mic, text):
    while text:
        if STOP.match(text): say("conversation ended"); return
        reply = ask(text)
        if not reply: return
        mic.muted.set(); speak(reply); time.sleep(0.35); mic.flush(); mic.muted.clear()
        text = transcribe(mic.utterance(wait=8))            # follow-up without the wake word


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--devices", action="store_true"); ap.add_argument("--mic", type=int)
    ap.add_argument("--level", action="store_true"); a = ap.parse_args()
    if a.devices: print(sd.query_devices()); return
    if not os.path.exists(MODEL): sys.exit("hey_felo.onnx is missing next to felo_listener.py")
    say("Felo Listener starting (Felo HQ: %s)" % FELO)
    mic = Mic(a.mic); wake = Wake(); paused = False
    say("say 'Hey Felo' to talk")
    while True:
        s = wake.score(mic.block())
        if a.level and s > 0.05: say("wake score %.2f" % s)
        if s < THRESHOLD: continue                            # not for Felo: nothing leaves the PC
        wake.reset(); beep("wake" if not paused else "no")
        text = transcribe(mic.utterance(wait=6))
        if paused:
            if RESUME.search(text): paused = False; beep("wake"); say("listening again")
            mic.flush(); wake.reset(); continue
        if PAUSE.search(text): paused = True; beep("pause"); say("paused - say 'Hey Felo, start listening'")
        elif text: conversation(mic, text)
        mic.flush(); wake.reset(); say("waiting for 'Hey Felo'")


if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: pass
    except Exception as e:
        log.exception("Felo Listener stopped"); print("Felo Listener stopped:", e); time.sleep(5); raise
