"""
mp4togif — Modern Edition
Convert MP4 videos to high-quality GIFs.
Built with CustomTkinter + Impeccable Product Register design system.

Design principles:
  - Color: Restrained — dark theme + single accent hue
  - Type: Single font family (Segoe UI), hierarchy via weight & size
  - Layout: Clean sections, no nested cards
  - Interaction: All controls cover hover / active / disabled states
  - Motion: CustomTkinter built-in 150–250 ms transitions

Package: pyinstaller --onefile --windowed --add-data "ffmpeg.exe;." --add-data "ffprobe.exe;." mp4togif_modern.py
"""

import os
import sys
import re
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk

# ==================== Design tokens ====================

class C:
    """Tinted palette — no pure black or white."""
    BG           = "#1a1b1e"
    SURFACE      = "#242529"
    SURFACE_ALT  = "#2a2b30"
    BORDER       = "#34353a"
    INK          = "#e4e4ea"
    INK_SUB      = "#8e8f98"
    INK_MUTED    = "#5c5d66"
    ACCENT       = "#4a8cf0"
    ACCENT_HOVER = "#5d99f4"
    SUCCESS      = "#43a87a"
    WARNING      = "#e0a03a"
    ERROR        = "#d9505f"

class S:
    """Spacing — 4 px grid"""
    XS=4; SM=8; MD=12; LG=16; XL=20; XXL=28

class F:
    """Type scale — Product: single family, ratio ~1.15"""
    FAM = "Segoe UI"
    H1   = (FAM, 24, "bold")
    H2   = (FAM, 16, "bold")
    BODY = (FAM, 13)
    SMALL= (FAM, 12)
    TINY = (FAM, 11)

# ==================== Globals ====================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==================== FFmpeg paths ====================

def _bin(name):
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    # macOS / Linux binaries have no .exe extension
    for variant in (f"{name}.exe", name):
        local = os.path.join(base, variant)
        if os.path.exists(local):
            return f'"{local}"'
    return name

FFMPEG  = _bin("ffmpeg")
FFPROBE = _bin("ffprobe")

# Subprocess: ffprobe/ffmpeg stderr can contain binary garbage on CJK Windows.
# Suppress stderr so the internal reader thread never tries to decode it as GBK.
import subprocess as _sp  # noqa: E402 — keep after the global subprocess import above
SP_NOSTDERR = {"stderr": _sp.DEVNULL, "text": True, "timeout": 15}
SP_SILENT   = {"stdout": _sp.DEVNULL, "stderr": _sp.DEVNULL, "timeout": 300}

# ==================== Main app ====================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MP4 → GIF")
        self.geometry("620x850")
        self.minsize(620, 850)          # locked to this size; user can still maximize
        self.configure(fg_color=C.BG)

        self._set_app_icon()

        # State
        self.file_path = ""
        self.out_dir   = os.path.expanduser("~/Desktop").replace("\\", "/")
        self.v_dur     = 0.0
        self.v_w       = 0
        self.v_h       = 0
        self.v_ratio   = 1.0
        self._busy     = False

        self._ui_header()
        self._ui_select()
        self._ui_slider()
        self._ui_params()
        self._ui_quality()
        self._ui_output()
        self._ui_action()

    # ---------- helpers ----------

    @staticmethod
    def _short(s, n=48):
        return s if len(s) <= n else "..." + s[-(n-3):]

    @staticmethod
    def _hms(sec):
        h, m, s = int(sec // 3600), int((sec % 3600) // 60), int(sec % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _set_app_icon(self):
        """Load logo.png as the window / taskbar icon."""
        # Search order: desktop, script directory, cwd
        candidates = [
            os.path.expanduser("~/Desktop/logo.png"),
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "logo.png"),
            os.path.join(os.getcwd(), "logo.png"),
        ]
        logo_path = None
        for p in candidates:
            if os.path.isfile(p.replace("\\", "/")):
                logo_path = p.replace("\\", "/")
                break

        if not logo_path:
            return  # no logo found — silently keep the default icon

        try:
            img = Image.open(logo_path)
            img = img.resize((64, 64), Image.LANCZOS)
            self._icon_image = ImageTk.PhotoImage(img)
            self.iconphoto(True, self._icon_image)
        except Exception:
            pass  # anything goes wrong, just skip

    # ---------- ui sections ----------

    def _ui_header(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=S.XL, pady=(S.XL, S.SM))
        ctk.CTkLabel(f, text="MP4 → GIF", font=F.H1, text_color=C.INK).pack(side="left")
        ctk.CTkLabel(f, text="Video to GIF Converter", font=F.SMALL,
                     text_color=C.INK_MUTED).pack(side="left", padx=(S.SM, 0))

    def _ui_select(self):
        """File picker + video info"""
        self.pnl_select = ctk.CTkFrame(
            self, fg_color=C.SURFACE, corner_radius=10,
            border_width=1, border_color=C.BORDER,
        )
        self.pnl_select.pack(fill="x", padx=S.XL, pady=(S.SM, S.SM))

        inner = ctk.CTkFrame(self.pnl_select, fg_color="transparent")
        inner.pack(fill="x", padx=S.XXL, pady=S.LG)

        self.lbl_file_icon = ctk.CTkLabel(inner, text="📂", font=(F.FAM, 28),
                                          text_color=C.INK_MUTED)
        self.lbl_file_icon.pack()

        self.lbl_file_name = ctk.CTkLabel(inner, text="No file selected", font=F.SMALL,
                                          text_color=C.INK_MUTED)
        self.lbl_file_name.pack(pady=(S.XS, 0))

        self.lbl_file_meta = ctk.CTkLabel(inner, text="", font=F.H2, text_color=C.INK)

        ctk.CTkButton(
            inner, text="Select MP4 File", font=F.SMALL,
            fg_color=C.SURFACE_ALT, hover_color=C.BORDER,
            text_color=C.INK, border_width=1, border_color=C.BORDER,
            corner_radius=8, height=34, command=self._pick_file,
        ).pack(pady=(S.MD, 0))

    def _ui_slider(self):
        """Time slider"""
        self.pnl_slider = ctk.CTkFrame(
            self, fg_color=C.SURFACE, corner_radius=10,
            border_width=1, border_color=C.BORDER,
        )
        self.pnl_slider.pack(fill="x", padx=S.XL, pady=(S.SM, S.SM))

        hdr = ctk.CTkFrame(self.pnl_slider, fg_color="transparent")
        hdr.pack(fill="x", padx=S.LG, pady=(S.LG, S.SM))
        ctk.CTkLabel(hdr, text="Start Time", font=F.SMALL,
                     text_color=C.INK_SUB).pack(side="left")
        self.lbl_time = ctk.CTkLabel(hdr, text="00:00:00", font=F.H2, text_color=C.INK)
        self.lbl_time.pack(side="right")

        self.sld_time = ctk.CTkSlider(
            self.pnl_slider, from_=0, to=100, number_of_steps=100, height=20,
            progress_color=C.ACCENT, button_color=C.ACCENT,
            button_hover_color=C.ACCENT_HOVER, fg_color="#2e2f34",
            command=self._on_slider,
        )
        self.sld_time.set(0)
        self.sld_time.pack(fill="x", padx=S.LG, pady=(0, S.LG))

    def _ui_params(self):
        """Conversion parameters — two-row grid for clean alignment"""
        self.pnl_params = ctk.CTkFrame(
            self, fg_color=C.SURFACE, corner_radius=10,
            border_width=1, border_color=C.BORDER,
        )
        self.pnl_params.pack(fill="x", padx=S.XL, pady=(S.SM, S.SM))

        grid = ctk.CTkFrame(self.pnl_params, fg_color="transparent")
        grid.pack(fill="x", padx=S.LG, pady=(S.LG, S.MD))

        # Row 0 — labels (aligned over their entries)
        lbls = ctk.CTkFrame(grid, fg_color="transparent")
        ctk.CTkLabel(lbls, text="Width",     font=F.TINY, text_color=C.INK_MUTED,
                     width=64, anchor="w").pack(side="left", padx=(0, S.SM))
        ctk.CTkLabel(lbls, text="FPS",       font=F.TINY, text_color=C.INK_MUTED,
                     width=48, anchor="w").pack(side="left", padx=(0, S.SM))
        ctk.CTkLabel(lbls, text="Duration",  font=F.TINY, text_color=C.INK_MUTED,
                     width=62, anchor="w").pack(side="left", padx=(0, S.SM))
        ctk.CTkLabel(lbls, text="Start At",  font=F.TINY, text_color=C.INK_MUTED,
                     width=80, anchor="w").pack(side="left")
        lbls.pack(fill="x")

        # Row 1 — entry fields
        ents = ctk.CTkFrame(grid, fg_color="transparent")

        self.e_w = ctk.CTkEntry(ents, width=64, height=32, font=F.BODY,
                                fg_color=C.BG, border_color=C.BORDER,
                                corner_radius=6, text_color=C.INK)
        self.e_w.insert(0, "480")
        self.e_w.pack(side="left", padx=(0, S.SM), pady=(2, 0))
        self.e_w.bind("<KeyRelease>", self._est_size)

        self.e_fps = ctk.CTkEntry(ents, width=48, height=32, font=F.BODY,
                                  fg_color=C.BG, border_color=C.BORDER,
                                  corner_radius=6, text_color=C.INK)
        self.e_fps.insert(0, "12")
        self.e_fps.pack(side="left", padx=(0, S.SM), pady=(2, 0))
        self.e_fps.bind("<KeyRelease>", self._est_size)

        # Duration entry + "s" unit label
        dur_frame = ctk.CTkFrame(ents, fg_color="transparent")
        self.e_dur = ctk.CTkEntry(dur_frame, width=40, height=32, font=F.BODY,
                                  fg_color=C.BG, border_color=C.BORDER,
                                  corner_radius=6, text_color=C.INK)
        self.e_dur.insert(0, "3")
        self.e_dur.pack(side="left", pady=(2, 0))
        self.e_dur.bind("<KeyRelease>", self._est_size)
        ctk.CTkLabel(dur_frame, text="s", font=F.TINY,
                     text_color=C.INK_MUTED).pack(side="left", padx=(2, 0))
        dur_frame.pack(side="left", padx=(0, S.SM + 6))  # +6 to compensate for "s" label width

        self.e_start = ctk.CTkEntry(ents, width=80, height=32, font=F.BODY,
                                    fg_color=C.BG, border_color=C.BORDER,
                                    corner_radius=6, text_color=C.INK)
        self.e_start.insert(0, "00:00:00")
        self.e_start.pack(side="left", pady=(2, 0))

        def _sync(*_):
            p = self.e_start.get().strip().split(":")
            if len(p) == 3:
                try:
                    t = int(p[0])*3600 + int(p[1])*60 + int(p[2])
                    if t <= self.v_dur:
                        self.sld_time.set(t)
                        self.lbl_time.configure(text=App._hms(t))
                except ValueError:
                    pass
        self.e_start.bind("<KeyRelease>", _sync)

        ents.pack(fill="x")

    def _ui_quality(self):
        """Quality slider"""
        self.pnl_qual = ctk.CTkFrame(
            self, fg_color=C.SURFACE, corner_radius=10,
            border_width=1, border_color=C.BORDER,
        )
        self.pnl_qual.pack(fill="x", padx=S.XL, pady=(S.SM, S.SM))

        hdr = ctk.CTkFrame(self.pnl_qual, fg_color="transparent")
        hdr.pack(fill="x", padx=S.LG, pady=(S.LG, S.SM))
        ctk.CTkLabel(hdr, text="Color Palette", font=F.SMALL,
                     text_color=C.INK_SUB).pack(side="left")
        self.lbl_colors = ctk.CTkLabel(hdr, text="128 colors", font=F.H2, text_color=C.ACCENT)
        self.lbl_colors.pack(side="right")

        self.sld_qual = ctk.CTkSlider(
            self.pnl_qual, from_=32, to=256, number_of_steps=224, height=20,
            progress_color=C.ACCENT, button_color=C.ACCENT,
            button_hover_color=C.ACCENT_HOVER, fg_color="#2e2f34",
            command=self._on_quality,
        )
        self.sld_qual.set(128)
        self.sld_qual.pack(fill="x", padx=S.LG)

        ft = ctk.CTkFrame(self.pnl_qual, fg_color="transparent")
        ft.pack(fill="x", padx=S.LG, pady=(S.SM, S.LG))
        ctk.CTkLabel(ft, text="Est. Size", font=F.SMALL, text_color=C.INK_MUTED).pack(side="left")
        self.lbl_size = ctk.CTkLabel(ft, text="-- MB", font=F.BODY, text_color=C.INK_SUB)
        self.lbl_size.pack(side="right")

    def _ui_output(self):
        """Output settings"""
        self.pnl_out = ctk.CTkFrame(
            self, fg_color=C.SURFACE, corner_radius=10,
            border_width=1, border_color=C.BORDER,
        )
        self.pnl_out.pack(fill="x", padx=S.XL, pady=(S.SM, S.SM))

        inner = ctk.CTkFrame(self.pnl_out, fg_color="transparent")
        inner.pack(fill="x", padx=S.LG, pady=S.LG)

        # Filename row
        r1 = ctk.CTkFrame(inner, fg_color="transparent")
        ctk.CTkLabel(r1, text="Filename", font=F.SMALL, text_color=C.INK_SUB).pack(side="left")
        self.e_name = ctk.CTkEntry(r1, width=100, height=32, font=F.BODY,
                                   fg_color=C.BG, border_color=C.BORDER,
                                   corner_radius=6, text_color=C.INK)
        self.e_name.insert(0, "1")
        self.e_name.pack(side="left", padx=(S.SM, S.XS))
        ctk.CTkLabel(r1, text=".gif", font=F.BODY, text_color=C.INK_MUTED).pack(side="left")
        ctk.CTkLabel(r1, text="auto-increments after save", font=F.TINY,
                     text_color=C.INK_MUTED).pack(side="left", padx=(S.SM, 0))
        r1.pack(fill="x")

        # Output path row
        r2 = ctk.CTkFrame(inner, fg_color="transparent")
        self.lbl_path = ctk.CTkLabel(r2, text=self._short(self.out_dir),
                                     font=F.TINY, text_color=C.INK_MUTED, anchor="w")
        self.lbl_path.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            r2, text="Change", width=56, height=26, font=F.TINY,
            fg_color=C.SURFACE_ALT, hover_color=C.BORDER,
            text_color=C.INK_SUB, border_width=1, border_color=C.BORDER,
            corner_radius=6, command=self._pick_dir,
        ).pack(side="right")
        r2.pack(fill="x", pady=(S.MD, 0))

    def _ui_action(self):
        """Convert button + status"""
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=S.XL, pady=(S.XL, S.XL))

        self.btn_go = ctk.CTkButton(
            f, text="Convert", font=(F.FAM, 16, "bold"), height=48,
            fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER,
            text_color="#fff", corner_radius=10,
            command=self._convert,
        )
        self.btn_go.pack(fill="x")

        self.lbl_status = ctk.CTkLabel(f, text="", font=F.SMALL, text_color=C.INK_MUTED)
        self.lbl_status.pack(pady=(S.SM, 0))

    # ---------- callbacks ----------

    def _pick_file(self):
        p = filedialog.askopenfilename(filetypes=[("MP4 Video", "*.mp4")])
        if p:
            self._load(p)

    def _pick_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir = d.replace("\\", "/")
            self.lbl_path.configure(text=self._short(self.out_dir))

    def _load(self, path):
        path = path.replace("\\", "/")
        self.file_path = path
        self.lbl_file_icon.configure(text="⏳")
        self.lbl_file_name.configure(text="Analyzing...")

        def task():
            try:
                d = float(subprocess.check_output(
                    f'{FFPROBE} -v error -show_entries format=duration '
                    f'-of default=noprint_wrappers=1:nokey=1 "{path}"',
                    shell=True, **SP_NOSTDERR).strip())
                r = subprocess.check_output(
                    f'{FFPROBE} -v error -select_streams v:0 '
                    f'-show_entries stream=width,height -of csv=s=x:p=0 "{path}"',
                    shell=True, **SP_NOSTDERR).strip()
                w, h = map(int, r.split("x"))

                self.v_dur, self.v_w, self.v_h = d, w, h
                self.v_ratio = w / h
                fn = os.path.basename(path)

                self.after(0, lambda: self._on_loaded(fn, d, w, h))
            except Exception as e:
                self.after(0, lambda: self._load_err(str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _on_loaded(self, filename, dur, w, h):
        self.lbl_file_icon.configure(text="📹")
        self.lbl_file_name.configure(text=filename, text_color=C.INK)
        self.lbl_file_meta.configure(text=f"{self._hms(dur)}  ·  {w}×{h}")
        self.lbl_file_meta.pack(pady=(S.XS, 0))

        self.sld_time.configure(to=dur, number_of_steps=max(1, int(dur)))
        self.sld_time.set(0)
        self.lbl_time.configure(text="00:00:00")
        self.e_start.delete(0, "end")
        self.e_start.insert(0, "00:00:00")

        self.e_w.delete(0, "end")
        self.e_w.insert(0, str(min(w, 480)))

        self._est_size()

    def _load_err(self, msg):
        self.lbl_file_icon.configure(text="❌")
        self.lbl_file_name.configure(text=f"Parse error: {msg}", text_color=C.ERROR)
        self.after(3000, lambda: (
            self.lbl_file_icon.configure(text="📂"),
            self.lbl_file_name.configure(text="No file selected", text_color=C.INK_MUTED),
        ))

    def _est_size(self, *_):
        if not self.file_path or self.v_w == 0:
            return
        try:
            w = int(self.e_w.get())
            h = int(w / self.v_ratio)
            fps  = int(self.e_fps.get())
            dur  = float(self.e_dur.get())
            cols = int(self.sld_qual.get())
            k = 0.12 + (cols / 256) * 0.5
            mb = (w * h * fps * dur * k) / (1024 * 1024)
            self.lbl_size.configure(text=f"≈{round(mb + 0.1, 2)} MB")
        except (ValueError, ZeroDivisionError):
            pass

    def _on_slider(self, val):
        hms = self._hms(float(val))
        self.lbl_time.configure(text=hms)
        self.e_start.delete(0, "end")
        self.e_start.insert(0, hms)

    def _on_quality(self, val):
        self.lbl_colors.configure(text=f"{int(float(val))} colors")
        self._est_size()

    def _convert(self):
        if not self.file_path:
            self.lbl_status.configure(text="Please select a video file first", text_color=C.WARNING)
            return
        if self._busy:
            return

        start  = self.e_start.get().strip()
        cut    = self.e_dur.get().strip()
        fps    = self.e_fps.get().strip()
        width  = self.e_w.get().strip()
        colors = int(self.sld_qual.get())
        raw    = self.e_name.get().strip() or "output"
        dest   = os.path.join(self.out_dir, f"{raw}.gif").replace("\\", "/")

        self._busy = True
        self.lbl_status.configure(text="⏳ Converting...", text_color=C.WARNING)
        self.btn_go.configure(text="Converting...", state="disabled", fg_color=C.SURFACE_ALT)

        def task():
            cmd = (
                f'{FFMPEG} -ss {start} -t {cut} -i "{self.file_path}" '
                f'-vf "fps={fps},scale={width}:-1:flags=lanczos,'
                f'split[s0][s1];[s0]palettegen=max_colors={colors}[p];'
                f'[s1][p]paletteuse=dither=sierra2_4a" '
                f'-y "{dest}"'
            )
            try:
                r = subprocess.run(cmd, shell=True, **SP_SILENT)
                if r.returncode == 0:
                    sz = os.path.getsize(dest) / (1024 * 1024)
                    # auto-increment filename
                    m = re.search(r"(\d+)$", raw)
                    if m:
                        n = int(m.group(1)) + 1
                        nxt = raw[:m.start()] + str(n).zfill(len(m.group(1)))
                    else:
                        nxt = raw + "2"
                    self.after(0, lambda: self._done(True, sz, nxt))
                else:
                    self.after(0, lambda: self._done(False, 0, ""))
            except Exception:
                self.after(0, lambda: self._done(False, 0, ""))

        threading.Thread(target=task, daemon=True).start()

    def _done(self, ok, size_mb, next_name):
        self._busy = False
        if ok:
            self.lbl_status.configure(
                text=f"✓ Done · {round(size_mb, 2)} MB", text_color=C.SUCCESS)
            if next_name:
                self.e_name.delete(0, "end")
                self.e_name.insert(0, next_name)
        else:
            self.lbl_status.configure(text="✗ Failed", text_color=C.ERROR)
        self.btn_go.configure(
            text="Convert", state="normal", fg_color=C.ACCENT)


if __name__ == "__main__":
    App().mainloop()
