import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re  # 必须导入，用于处理文件名递增

# ===================== FFmpeg 路径检测 =====================
def get_ffmpeg_bin(name):
    """优先查找脚本同级目录下的 exe，找不到则使用系统全局变量"""
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    local_path = os.path.join(base_path, f"{name}.exe")
    if os.path.exists(local_path):
        return f'"{local_path}"'
    return name

FFMPEG_PATH = get_ffmpeg_bin("ffmpeg")
FFPROBE_PATH = get_ffmpeg_bin("ffprobe")

# ===================== 全局业务变量 =====================
file_path = ""
output_folder = r"C:\Users\Administrator\Desktop"
video_total_sec = 0
video_width = 0
video_height = 0
aspect_ratio = 1.0

# ===================== 界面创建 =====================
root = tk.Tk()
root.title("MP4转GIF 终极增强版")
root.geometry("680x620")
root.resizable(False, False)
root.configure(bg="#f5f7fa")

font_norm = ("微软雅黑", 10)
font_bold = ("微软雅黑", 11, "bold")

# 顶部：选择文件及信息显示
frame_top = tk.Frame(root, bg="#f5f7fa")
frame_top.pack(padx=20, pady=15, fill=tk.X)

btn_sel_file = tk.Button(frame_top, text="选择MP4文件", bg="#0078d7", fg="white", font=("微软雅黑", 10, "bold"), relief=tk.FLAT, cursor="hand2")
btn_sel_file.grid(row=0, column=0, sticky="w")

tk.Label(frame_top, text="视频信息：", font=font_norm, bg="#f5f7fa").grid(row=0, column=1, padx=(30,0))
lbl_duration = tk.Label(frame_top, text="等待选择文件", font=font_bold, fg="#0066cc", bg="#f5f7fa")
lbl_duration.grid(row=0, column=2, sticky="w")

tk.Label(frame_top, text="文件路径：", font=font_norm, bg="#f5f7fa").grid(row=1, column=0, sticky="w", pady=(10,2))
lbl_filepath = tk.Label(frame_top, text="未选择", bg="white", anchor="w", relief=tk.SUNKEN)
lbl_filepath.grid(row=2, column=0, columnspan=3, sticky="ew", ipadx=5, ipady=4)

# 进度条
frame_slider = tk.LabelFrame(root, text=" 进度定位 (拖动更改开始时间) ", font=font_bold, bg="#f5f7fa")
frame_slider.pack(padx=20, pady=5, fill=tk.X)
slider_time = ttk.Scale(frame_slider, from_=0, to=100, orient=tk.HORIZONTAL)
slider_time.pack(padx=10, pady=8, fill=tk.X)

# 参数设置区
frame_opt = tk.LabelFrame(root, text=" 转换设置 ", font=font_bold, bg="#f5f7fa")
frame_opt.pack(padx=20, pady=10, fill=tk.X)

# 第一行：开始时间 + 截取时长
tk.Label(frame_opt, text="开始时间：", font=font_norm, bg="#f5f7fa").grid(row=0, column=0, padx=10, pady=8)
entry_start = ttk.Entry(frame_opt, width=15)
entry_start.grid(row=0, column=1)
entry_start.insert(0, "00:00:00")

tk.Label(frame_opt, text="截取时长：", font=font_norm, bg="#f5f7fa").grid(row=0, column=2, padx=10)
entry_cut = ttk.Entry(frame_opt, width=10)
entry_cut.grid(row=0, column=3)
entry_cut.insert(0, "3")
tk.Label(frame_opt, text="秒", bg="#f5f7fa").grid(row=0, column=4, sticky="w")

# 第二行：输出宽度 + 帧数
tk.Label(frame_opt, text="输出宽度：", font=font_norm, bg="#f5f7fa").grid(row=1, column=0, padx=10, pady=8)
entry_width = ttk.Entry(frame_opt, width=15)
entry_width.grid(row=1, column=1)
entry_width.insert(0, "480") 

tk.Label(frame_opt, text="每秒帧数：", font=font_norm, bg="#f5f7fa").grid(row=1, column=2, padx=10)
entry_fps = ttk.Entry(frame_opt, width=10)
entry_fps.grid(row=1, column=3)
entry_fps.insert(0, "12")
tk.Label(frame_opt, text="FPS", bg="#f5f7fa").grid(row=1, column=4, sticky="w")

# 第三行：文件名递增设置
tk.Label(frame_opt, text="GIF文件名：", font=font_norm, bg="#f5f7fa").grid(row=2, column=0, padx=10, pady=8)
entry_out_name = ttk.Entry(frame_opt, width=15)
entry_out_name.grid(row=2, column=1)
entry_out_name.insert(0, "1")
tk.Label(frame_opt, text=".gif (完成后自动递增)", font=("微软雅黑", 9), fg="#999", bg="#f5f7fa").grid(row=2, column=2, columnspan=3, sticky="w")

# 质量与体积
frame_quality = tk.LabelFrame(root, text=" 质量与体积平衡 ", font=font_bold, bg="#f5f7fa")
frame_quality.pack(padx=20, pady=10, fill=tk.X)

tk.Label(frame_quality, text="压缩强度：", font=font_norm, bg="#f5f7fa").grid(row=0, column=0, padx=10, pady=10)
slider_quality = ttk.Scale(frame_quality, from_=32, to=256, orient=tk.HORIZONTAL, length=200)
slider_quality.set(128)
slider_quality.grid(row=0, column=1)

lbl_quality_val = tk.Label(frame_quality, text="128色", font=font_bold, fg="#0066cc", bg="#f5f7fa")
lbl_quality_val.grid(row=0, column=2, padx=10)

tk.Label(frame_quality, text="预计大小：", font=font_norm, bg="#f5f7fa").grid(row=0, column=3, padx=10)
lbl_file_size = tk.Label(frame_quality, text="-- MB", font=font_bold, fg="#e63946", bg="#f5f7fa")
lbl_file_size.grid(row=0, column=4)

# 底部保存路径和按钮
frame_path = tk.Frame(root, bg="#f5f7fa")
frame_path.pack(padx=20, pady=10, fill=tk.X)
btn_set_out = ttk.Button(frame_path, text="更改保存目录")
btn_set_out.pack(side=tk.LEFT)
lbl_save_path = tk.Label(frame_path, text=output_folder, bg="white", anchor="w", font=("Consolas", 9))
lbl_save_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, ipady=3)

lbl_status = tk.Label(root, text="就绪", font=font_bold, bg="#f5f7fa", fg="#666")
lbl_status.pack(pady=5)

btn_convert = tk.Button(root, text="开始转换", bg="#28a745", fg="white", font=("微软雅黑", 14, "bold"), width=16, height=1, relief=tk.FLAT, cursor="hand2")
btn_convert.pack(pady=7)

# ===================== 业务逻辑函数 =====================

def seconds_to_hms(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def run_in_thread(func):
    t = threading.Thread(target=func, daemon=True)
    t.start()

def get_video_info(path):
    try:
        cmd_dur = f'{FFPROBE_PATH} -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{path}"'
        duration = float(subprocess.check_output(cmd_dur, shell=True, text=True, timeout=10).strip())
        cmd_res = f'{FFPROBE_PATH} -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "{path}"'
        res = subprocess.check_output(cmd_res, shell=True, text=True, timeout=10).strip()
        w, h = map(int, res.split('x'))
        return duration, w, h
    except Exception as e:
        print(f"Probe Error: {e}")
        return 0, 0, 0

def calculate_file_size(*args):
    if not file_path or video_width == 0: return
    try:
        w = int(entry_width.get())
        h = int(w / aspect_ratio)
        fps = int(entry_fps.get())
        dur = float(entry_cut.get())
        colors = int(slider_quality.get())
        # 高精度系数
        pixel_factor = 0.12 + (colors / 256) * 0.5
        size_mb = (w * h * fps * dur * pixel_factor) / (1024 * 1024)
        lbl_file_size.config(text=f"{round(size_mb + 0.1, 2)} MB")
    except: pass

def load_video_file(path):
    global file_path, video_total_sec, video_width, video_height, aspect_ratio
    if not path: return
    file_path = path.replace("\\", "/")
    lbl_filepath.config(text=file_path)
    lbl_duration.config(text="解析中...")

    def task():
        global video_total_sec, video_width, video_height, aspect_ratio
        sec, w, h = get_video_info(file_path)
        if sec > 0:
            video_total_sec, video_width, video_height = sec, w, h
            aspect_ratio = w / h
            hms = seconds_to_hms(sec)
            slider_time.config(to=sec)
            entry_width.delete(0, tk.END)
            entry_width.insert(0, str(min(w, 480)))
            # 格式：00:00:00 | 原尺寸:1920x1080
            lbl_duration.after(0, lambda: lbl_duration.config(text=f"{hms} | 原尺寸:{w}x{h}"))
            calculate_file_size()
    run_in_thread(task)

def do_convert():
    if not file_path:
        messagebox.showwarning("提示", "请先选择视频文件")
        return

    start_t = entry_start.get().strip()
    cut_t = entry_cut.get().strip()
    fps = entry_fps.get().strip()
    width = entry_width.get().strip()
    colors = int(slider_quality.get())
    
    raw_name = entry_out_name.get().strip() or "output"
    save_path = os.path.join(output_folder, f"{raw_name}.gif").replace("\\", "/")

    lbl_status.config(text="转换中...", fg="#ff9800")
    btn_convert.config(state=tk.DISABLED, bg="#ccc")

    def task():
        cmd = (
            f'{FFMPEG_PATH} -ss {start_t} -t {cut_t} -i "{file_path}" '
            f'-vf "fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors={colors}[p];[s1][p]paletteuse=dither=sierra2_4a" '
            f'-y "{save_path}"'
        )
        try:
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            if process.returncode == 0:
                actual_size = os.path.getsize(save_path) / (1024*1024)
                lbl_status.after(0, lambda: lbl_status.config(text=f"成功！大小: {round(actual_size, 2)} MB", fg="#28a745"))
                
                # 智能递增文件名逻辑
                try:
                    match = re.search(r'(\d+)$', raw_name)
                    if match:
                        num_part = match.group(1)
                        new_num = int(num_part) + 1
                        new_name = raw_name[:match.start()] + str(new_num).zfill(len(num_part))
                    else:
                        new_name = raw_name + "1"
                    
                    entry_out_name.delete(0, tk.END)
                    entry_out_name.insert(0, new_name)
                except: pass
            else:
                lbl_status.after(0, lambda: lbl_status.config(text="转换失败", fg="red"))
        except Exception as e:
            lbl_status.after(0, lambda: lbl_status.config(text="程序异常", fg="red"))
        finally:
            btn_convert.after(0, lambda: btn_convert.config(state=tk.NORMAL, bg="#28a745"))

    run_in_thread(task)

def on_slider_move(val):
    entry_start.delete(0, tk.END)
    entry_start.insert(0, seconds_to_hms(float(val)))

# ===================== 事件绑定 =====================
btn_sel_file.config(command=lambda: load_video_file(filedialog.askopenfilename(filetypes=[("MP4", "*.mp4")])))
btn_set_out.config(command=lambda: [globals().update(output_folder=filedialog.askdirectory()), lbl_save_path.config(text=output_folder)])
btn_convert.config(command=do_convert)
slider_time.config(command=on_slider_move)
slider_quality.config(command=lambda v: [lbl_quality_val.config(text=f"{int(float(v))}色"), calculate_file_size()])
entry_width.bind("<KeyRelease>", calculate_file_size)
entry_fps.bind("<KeyRelease>", calculate_file_size)
entry_cut.bind("<KeyRelease>", calculate_file_size)

root.mainloop()