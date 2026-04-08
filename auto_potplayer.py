import os
import time
import subprocess
import logging
import win32gui
import win32con
import win32api
from screeninfo import get_monitors

# 播放列表文件路径
DPL_PATH = os.path.expanduser(r"~\AppData\Roaming\PotPlayerMini64\Playlist\PotPlayerMini64.dpl")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def update_video_dirs_from_dpl():
    """从 PotPlayerMini64.dpl 文件中提取最新播放视频的父目录"""
    global VIDEO_DIRS
    try:
        with open(DPL_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith("playname="):
                full_path = line.split("=", 1)[1].strip()
                parent_dir = os.path.dirname(full_path)
                if os.path.isdir(parent_dir):
                    VIDEO_DIRS = [parent_dir]
                break
    except Exception as e:
        logging.warning(f"读取 .dpl 文件失败: {e}")
        VIDEO_DIRS = []  #  fallback 为空，避免崩溃

# 初始加载一次
VIDEO_DIRS = []
update_video_dirs_from_dpl()

def ffprobe_resolution(path):
    """用 ffprobe 获取分辨率的前两行"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "default=nokey=1:noprint_wrappers=1", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2
        )
        lines = result.stdout.strip().split()
        if len(lines) >= 2:
            w, h = map(int, lines[:2])
            return w, h
        else:
            logging.warning(f"ffprobe 输出不足2行: {result.stdout.strip()}")
            return 1920, 1080
    except Exception as e:
        logging.warning(f"获取分辨率失败: {e}")
        return 1920, 1080

def get_potplayer_title():
    """获取 PotPlayer 窗口标题，只返回有效视频标题"""
    hwnds = []
    def enum_handler(h, _):
        title = win32gui.GetWindowText(h)
        if "PotPlayer" in title and " - " in title:
            # 必须包含 " - PotPlayer" 且前面有文件名
            hwnds.append((h, title))
    win32gui.EnumWindows(enum_handler, None)
    return hwnds[0] if hwnds else (None, "")
def find_video_path_from_title(title):
    """根据标题匹配本地文件路径"""
    if not title:
        return None
    # PotPlayer 标题一般是 '文件名 - PotPlayer'
    filename = title.split(" - ")[0].strip()
    for base in VIDEO_DIRS:
        for root, _, files in os.walk(base):
            for f in files:
                if f.lower().startswith(filename.lower()):
                    return os.path.join(root, f)
    return None

def move_window_to_monitor(hwnd, monitor):
    """移动窗口到目标显示器"""
    x, y, w, h = monitor.x, monitor.y, monitor.width, monitor.height
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, w, h, win32con.SWP_SHOWWINDOW)


def choose_monitor(orientation):
    """根据横竖屏选择显示器（左=横屏，右=竖屏）"""
    monitors = sorted(get_monitors(), key=lambda m: m.x)
    left = monitors[0]
    right = monitors[-1] if len(monitors) > 1 else left
    if orientation == "横屏":
        return left
    else:
        return right

def main():
    last_title = ""
    logging.info('potplayer横竖屏自动切换显示器')
    while True:
        hwnd, title = get_potplayer_title()
        if hwnd and title != last_title:
            last_title = title

            # 更新目录
            update_video_dirs_from_dpl()

            path = find_video_path_from_title(title)
            if path and os.path.exists(path):
                w, h = ffprobe_resolution(path)
                orientation = "横屏" if w >= h else "竖屏"
                mon = choose_monitor(orientation)
                move_window_to_monitor(hwnd, mon)
                logging.info(f"已移动到 {orientation} 显示器")
            else:
                logging.warning("未找到本地路径，跳过移动")
        time.sleep(1)

if __name__ == "__main__":
    main()
