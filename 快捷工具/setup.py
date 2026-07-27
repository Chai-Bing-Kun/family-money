#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║     🏠 家庭报销管理系统 — 一键部署引导程序          ║
╚══════════════════════════════════════════════════════╝

用法：
    setup                  正常交互式引导
    setup --quick          快速模式（全部默认值）

本程序将引导您完成：环境检测 → 端口配置 → 依赖安装
         → 管理员设置 → 可选功能 → 生成启动脚本 → 启动服务
"""

import os
import sys
import json
import re
import subprocess
import socket
import webbrowser
import shutil
import locale
import platform as pf_module
from pathlib import Path
from datetime import datetime
from string import Template

# ============================================================
# 多语言支持
# ============================================================

_TR = {}
_LANG = 'en'

def detect_language():
    """自动检测系统语言"""
    global _LANG
    # 1) Windows UI language
    if os.name == 'nt':
        try:
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            # Chinese LCIDs: 0x0804(zh-CN), 0x0404(zh-TW), 0x0C04(zh-HK)
            if (lang_id & 0xFF) == 0x04 or (lang_id >> 8) == 0x04:
                _LANG = 'zh'
                return
        except Exception:
            pass
    # 2) locale fallback
    try:
        lc, _ = locale.getdefaultlocale()
        if lc and lc.startswith('zh'):
            _LANG = 'zh'
            return
    except Exception:
        pass
    # 3) LANG env var
    try:
        if os.environ.get('LANG', '').startswith('zh'):
            _LANG = 'zh'
            return
    except Exception:
        pass
    _LANG = 'en'


def T(key: str) -> str:
    """翻译查询"""
    return _TR.get(key, key)


def _load_translations():
    """加载全部翻译"""
    global _TR
    detect_language()

    if _LANG == 'zh':
        _TR = {
            # ---- 应用名称/横幅 ----
            'app_name':      '家庭报销管理系统',
            'setup_wizard':  '一键部署引导',
            'guide_desc':    '本程序将引导您完成：环境检测 → 端口配置 → 依赖安装\n'
                             '         → 管理员设置 → 可选功能 → 生成启动脚本 → 启动服务',

            # ---- 步骤标题 ----
            'step_env':        '环境检测',
            'step_port':       '端口配置',
            'step_deps':       '安装依赖',
            'step_admin':      '管理员设置',
            'step_features':   '可选功能',
            'step_apply':      '应用配置',
            'step_start':      '启动服务',

            # ---- 环境检测 ----
            'current_dir':     '当前目录',
            'python_ver_ok':   'Python 版本合格',
            'python_ver_warn': 'Python 版本偏低，推荐',
            'pip_ok':          'pip 可用',
            'pip_missing':     'pip 不可用，将跳过依赖安装',
            'git_info':        'Git',
            'git_missing':     'Git 未安装（非必需）',
            'file_ok':         '存在',
            'file_missing':    '缺失',
            'struct_ok':       '项目结构完整',
            'struct_warn':     '部分文件缺失，可能影响运行',
            'venv_detected':   '检测到虚拟环境',
            'venv_explain':    '虚拟环境是一个独立的 Python 运行空间，可避免与系统全局 Python 包冲突',
            'use_venv':        '使用虚拟环境？',
            'venv_found':      '使用虚拟环境 Python',
            'venv_not_found':  '虚拟环境 Python 未找到，使用系统 Python',
            'no_venv':         '未检测到虚拟环境，使用系统 Python',

            # ---- 端口配置 ----
            'current_port':    '当前端口',
            'port_in_use':     '端口已被占用！',
            'port_available':  '端口可用',
            'change_port':     '修改端口？',
            'enter_port':      '输入新端口号',
            'port_range_err':  '端口号必须在 1~65535 之间',
            'still_use_port':  '仍然使用此端口？',
            'selected_port':   '已选择端口',
            'enter_valid_num': '请输入有效数字',
            'lan_desc':        '局域网访问：允许同 WiFi 下的其他设备访问',
            'allow_lan':       '允许局域网访问？',
            'listen_addr':     '监听地址',

            # ---- 依赖安装 ----
            'deps_title':      '所需依赖',
            'deps_installed':  '已安装',
            'deps_missing':    '未安装',
            'all_deps_ready':  '所有依赖已就绪',
            'pip_unavail':     'pip 不可用，请手动安装：',
            'install_deps_q':  '安装缺失的依赖？',
            'skip_deps':       '跳过依赖安装',
            'installing':      '正在安装依赖，请稍候...',
            'deps_success':    '所有依赖安装成功！',
            'install_failed':  '安装失败：',
            'manual_install':  '请手动运行：pip install -r backend/requirements.txt',
            'install_timeout': '安装超时，请手动安装',

            # ---- 管理员 ----
            'admin_desc':      '管理员账号用于登录后台管理面板',
            'admin_exists':    '管理员已配置',
            'reset_admin':     '重置管理员密码？',
            'keep_admin':      '保留现有管理员配置',
            'admin_username':  '管理员用户名',
            'admin_password':  '管理员密码（至少4位）',
            'pwd_min_err':     '密码至少需要4位字符',
            'confirm_pwd':     '确认密码',
            'pwd_mismatch':    '两次密码不一致',
            'admin_ok':        '管理员配置成功！',

            # ---- 可选功能 ----
            'debug_desc':      '调试模式：修改代码后自动重载，适合开发',
            'enable_debug':    '启用 Flask 调试模式？',
            'debug_on':        '调试模式：开',
            'debug_off':       '调试模式：关',
            'auto_start_desc': '开机自启：系统启动时自动运行服务器',
            'add_startup':     '添加到开机自启？',
            'shortcut_desc':   '桌面快捷方式：快速启动服务器',
            'create_shortcut': '创建桌面快捷方式？',
            'auto_browser':    '启动时自动打开浏览器？',
            'browser_on':      '自动打开浏览器：是',
            'browser_off':     '自动打开浏览器：否',

            # ---- 开机自启 ----
            'autostart_win':     '开机自启仅支持 Windows',
            'autostart_novbs':   '启动脚本不存在，无法创建开机自启',
            'task_exists':       '开机自启任务已存在',
            'task_update':       '是否更新？',
            'autostart_ok':      '开机自启已添加（登录时启动）',
            'autostart_fail':    '开机自启添加失败',

            # ---- 桌面快捷方式 ----
            'shortcut_ok':     '桌面快捷方式已创建！',
            'shortcut_fail':   '创建桌面快捷方式失败',

            # ---- 应用配置 ----
            'app_not_found':   '文件不存在',
            'backup_created':  '原始文件已备份',
            'app_updated':     '已更新',
            'no_apprun_found': '未找到 app.run() 调用，请手动配置',

            # ---- 生成脚本 ----
            'updated':         '已更新',
            'created':         '已创建',

            # ---- 启动服务器 ----
            'start_info':      '正在启动服务器，请稍候...',
            'start_failed':    '服务器启动失败！',
            'manual_start':    '请手动启动：',
            'start_ok':        '服务器已启动！',
            'admin_label':     '管理员',
            'stop_hint':       '停止服务：运行 快捷工具\\close.bat 或按 Ctrl+C',
            'open_browser':    '正在打开浏览器...',
            'start_err':       '启动失败',

            # ---- 总结 ----
            'summary_title':  '配置总结',
            'project':        '项目',
            'python':         'Python',
            'listen':         '监听',
            'lan_accessible': '（局域网可访问）',
            'local_only':     '（仅本机）',
            'admin':          '管理员',
            'dependencies':   '依赖',
            'autostart':      '开机自启',
            'shortcuts':      '桌面快捷方式',
            'status_installed':  '已安装',
            'status_none':       '未安装',
            'status_added':      '已添加',
            'status_not_added':  '未添加',
            'status_created':    '已创建',
            'status_not_created':'未创建',
            'quick_start':    '快速启动',
            'double_click':   '双击',
            'or_run':         '或运行',
            'stop_server':    '停止服务',
            'config_applied': '配置已应用到所有文件',
            'later_hint':     '稍后可通过以下方式启动：',
            'goodbye':        '再见！',

            # ---- 配置确认 ----
            'confirm_title':     '配置确认',
            'confirm_apply':     '确认无误，开始应用以上配置？',
            'applying_config':   '正在应用配置...',
            'apply_complete':    '所有配置已应用完成！',
            'config_python':     'Python 路径',
            'config_port':       '端口',
            'config_host':       '监听地址',
            'config_debug':      '调试模式',
            'config_admin':      '管理员账号',
            'config_deps':       '依赖安装',
            'config_autostart':  '开机自启',
            'config_shortcut':   '桌面快捷方式',
            'config_browser':    '自动打开浏览器',
            'will_install':      '将安装',
            'will_skip':         '将跳过',
            'will_apply':        '将应用',
            'will_not_apply':    '将不应用',
            'will_create':       '将创建',
            'will_not_create':   '将不创建',

            # ---- 一般提示 ----
            'user_cancelled': '用户取消',
            'field_empty':    '此项不能为空',
            'enter_continue': '按 Enter 继续...',
            'start_now':      '立即启动服务器？',
            'chinese_input':  '请输入',
            'default':        '默认',

            # ---- 启动/停止脚本 ----
            'launch_sent':      '启动指令已发送，窗口即将自动关闭...',
            'frontend_url':     '前端地址',
            'admin_url':        '账号管理',
            'finding_port':     '正在查找占用端口',
            'found_pid':        '找到进程 PID',
            'killed_ok':        '主进程已终止',
            'cleaning_python':  '正在清理残留的 Python 进程',
            'cleaned_ok':       '残留进程已清理',
            'no_process_found': '未找到相关进程，服务可能未启动',
            'all_cleaned':      '所有进程已终止',
            'done_press_any':   '操作完成，按任意键退出...',
        }
    else:
        # English (default)
        _TR = {
            'app_name':      'Family Expense Manager',
            'setup_wizard':  'Setup Wizard',
            'guide_desc':    'This wizard will guide you through:\n'
                             '    Environment Check -> Port Config -> Install Dependencies\n'
                             '    -> Admin Setup -> Optional Features -> Generate Scripts -> Start Server',

            'step_env':        'Environment Check',
            'step_port':       'Port Configuration',
            'step_deps':       'Install Dependencies',
            'step_admin':      'Admin Setup',
            'step_features':   'Optional Features',
            'step_apply':      'Apply Configuration',
            'step_start':      'Start Server',

            'current_dir':     'Current directory',
            'python_ver_ok':   'Python version OK',
            'python_ver_warn': 'Python version low, recommended',
            'pip_ok':          'pip is available',
            'pip_missing':     'pip not available, will skip dependency installation',
            'git_info':        'Git',
            'git_missing':     'Git not installed (optional)',
            'file_ok':         'OK',
            'file_missing':    'MISSING',
            'struct_ok':       'Project structure is complete',
            'struct_warn':     'Some files are missing, may affect operation',
            'venv_detected':   'Virtual env detected',
            'venv_explain':    'A virtual env is an isolated Python environment that avoids conflicts with system-wide packages',
            'use_venv':        'Use virtual environment?',
            'venv_found':      'Using venv Python',
            'venv_not_found':  'venv Python not found, using system Python',
            'no_venv':         'No virtual environment detected, using system Python',

            'current_port':    'Current port',
            'port_in_use':     'Port is already in use!',
            'port_available':  'Port is available',
            'change_port':     'Change port?',
            'enter_port':      'Enter new port number',
            'port_range_err':  'Port must be between 1 and 65535',
            'still_use_port':  'Still use this port?',
            'selected_port':   'Selected port',
            'enter_valid_num': 'Please enter a valid number',
            'lan_desc':        'LAN access: allows other devices (e.g. phones) on same WiFi to access',
            'allow_lan':       'Allow LAN access?',
            'listen_addr':     'Listen address',

            'deps_title':      'Required dependencies',
            'deps_installed':  'installed',
            'deps_missing':    'not installed',
            'all_deps_ready':  'All dependencies are ready',
            'pip_unavail':     'pip not available. Please install manually:',
            'install_deps_q':  'Install missing dependencies?',
            'skip_deps':       'Skipping dependency installation',
            'installing':      'Installing dependencies, please wait...',
            'deps_success':    'All dependencies installed successfully!',
            'install_failed':  'Installation failed:',
            'manual_install':  'Please run manually: pip install -r backend/requirements.txt',
            'install_timeout': 'Installation timed out, please install manually',

            'admin_desc':      'Admin account is used to login to the admin panel',
            'admin_exists':    'Admin already configured',
            'reset_admin':     'Reset admin credentials?',
            'keep_admin':      'Keeping existing admin configuration',
            'admin_username':  'Admin username',
            'admin_password':  'Admin password (min 4 chars)',
            'pwd_min_err':     'Password must be at least 4 characters',
            'confirm_pwd':     'Confirm password',
            'pwd_mismatch':    'Passwords do not match',
            'admin_ok':        'Admin configured successfully!',

            'debug_desc':      'Debug mode: auto-reload on code change, suitable for development',
            'enable_debug':    'Enable Flask debug mode?',
            'debug_on':        'Debug mode: On',
            'debug_off':       'Debug mode: Off',
            'auto_start_desc': 'Auto-start: automatically run server on system startup',
            'add_startup':     'Add to startup?',
            'shortcut_desc':   'Desktop shortcut: quick access to start the server',
            'create_shortcut': 'Create desktop shortcuts?',
            'auto_browser':    'Auto-open browser on start?',
            'browser_on':      'Auto-open browser: Yes',
            'browser_off':     'Auto-open browser: No',

            'autostart_win':     'Auto-start is only supported on Windows',
            'autostart_novbs':   'start_backend.vbs not found, cannot create auto-start',
            'task_exists':       'Startup task already exists',
            'task_update':       'Update it?',
            'autostart_ok':      'Auto-start added (runs on login)',
            'autostart_fail':    'Failed to add auto-start',

            'shortcut_ok':     'Desktop shortcuts created!',
            'shortcut_fail':   'Failed to create shortcuts',

            'app_not_found':   'not found',
            'backup_created':  'Backed up original',
            'app_updated':     'updated',
            'no_apprun_found': 'Could not find app.run() call, please configure manually',

            'updated':         'Updated',
            'created':         'Created',

            'start_info':      'Starting server, please wait...',
            'start_failed':    'Server failed to start!',
            'manual_start':    'Please try starting manually:',
            'start_ok':        'Server started!',
            'admin_label':     'Admin',
            'stop_hint':       'Stop: Run 快捷工具\\close.bat or press Ctrl+C',
            'open_browser':    'Opening browser...',
            'start_err':       'Failed to start',

            'summary_title':   'Configuration Summary',
            'project':         'Project',
            'python':          'Python',
            'listen':          'Listen',
            'lan_accessible':  '(LAN accessible)',
            'local_only':      '(local only)',
            'admin':           'Admin',
            'dependencies':    'Dependencies',
            'autostart':       'Auto-start',
            'shortcuts':       'Shortcuts',
            'status_installed':   'Installed',
            'status_none':        'Not installed',
            'status_added':       'Added',
            'status_not_added':   'Not added',
            'status_created':     'Created',
            'status_not_created': 'Not created',
            'quick_start':    'Quick Start',
            'double_click':   'Double-click',
            'or_run':         'Or run',
            'stop_server':    'Stop Server',
            'config_applied': 'Configuration applied to all files',
            'later_hint':     'You can start later via:',
            'goodbye':        'Goodbye!',

            # ---- Config Review ----
            'confirm_title':     'Configuration Review',
            'confirm_apply':     'Confirm and apply the above configuration?',
            'applying_config':   'Applying configuration...',
            'apply_complete':    'All configuration has been applied!',
            'config_python':     'Python Path',
            'config_port':       'Port',
            'config_host':       'Listen Address',
            'config_debug':      'Debug Mode',
            'config_admin':      'Admin Account',
            'config_deps':       'Dependencies',
            'config_autostart':  'Auto-start',
            'config_shortcut':   'Desktop Shortcut',
            'config_browser':    'Auto-open Browser',
            'will_install':      'Will install',
            'will_skip':         'Will skip',
            'will_apply':        'Will apply',
            'will_not_apply':    'Will not apply',
            'will_create':       'Will create',
            'will_not_create':   'Will not create',

            'user_cancelled': 'User cancelled',
            'field_empty':    'This field cannot be empty',
            'enter_continue': 'Press Enter to continue...',
            'start_now':      'Start server now?',
            'chinese_input':  'Please enter',
            'default':        'default',

            # ---- Start/Stop scripts ----
            'launch_sent':      'Launch command sent, window will auto-close...',
            'frontend_url':     'Frontend URL',
            'admin_url':        'Admin Panel',
            'finding_port':     'Looking for port',
            'found_pid':        'Found PID',
            'killed_ok':        'Process terminated',
            'cleaning_python':  'Cleaning up Python processes...',
            'cleaned_ok':       'Residual processes cleaned',
            'no_process_found': 'No related processes found',
            'all_cleaned':      'All processes terminated',
            'done_press_any':   'Done, press any key to exit...',
        }

# 加载翻译（必须在常量定义前调用，因为 T() 在常量之后才使用）
_load_translations()

# ============================================================
# 全局常量
# ============================================================
# 检测是否为 PyInstaller 打包的 exe
if getattr(sys, 'frozen', False):
    # __file__ 指向临时解压目录，不可用
    # sys.executable 才是 exe 的真实路径
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / 'backend'
FRONTEND_DIR = PROJECT_ROOT / 'frontend'
TOOLS_DIR = PROJECT_ROOT / '快捷工具'
DOCS_DIR = PROJECT_ROOT / 'docs'

APP_PY = BACKEND_DIR / 'app.py'
REQUIREMENTS = BACKEND_DIR / 'requirements.txt'
SETTINGS_JSON = BACKEND_DIR / 'settings.json'
USERS_JSON = BACKEND_DIR / 'users.json'
BILLS_JSON = BACKEND_DIR / 'bills.json'
CLAIMS_JSON = BACKEND_DIR / 'claims.json'

START_BAT = TOOLS_DIR / 'start.bat'
CLOSE_BAT = TOOLS_DIR / 'close.bat'
START_VBS = TOOLS_DIR / 'start_backend.vbs'

APP_PY_BAK = BACKEND_DIR / 'app.py.setup.bak'

# 默认值
DEFAULT_PORT = 3000
MIN_PYTHON_VERSION = (3, 8)

# ============================================================
# ANSI 颜色（只用于终端输出，会自动降级）
# ============================================================
class C:
    RESET = ''
    BOLD = ''
    DIM = ''
    RED = ''
    GREEN = ''
    YELLOW = ''
    BLUE = ''
    MAGENTA = ''
    CYAN = ''
    WHITE = ''
    BG_DARK = ''
    BOLD_RED = ''
    BOLD_GREEN = ''
    BOLD_YELLOW = ''
    BOLD_CYAN = ''


def init_console():
    """初始化控制台（Windows ANSI + UTF-8 支持）"""
    # 1) 设置终端编码为 UTF-8
    if os.name == 'nt':
        os.system('color')
        os.system('chcp 65001 >nul 2>nul')
        # 尝试设置环境变量确保子进程也用 UTF-8
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

    # 2) 尝试 reconfigure stdout/stderr 为 utf-8
    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8')
            except Exception:
                pass

    # 3) 检测终端是否支持 ANSI 颜色
    # 如果不支持则颜色类保持空字符串（已经在类定义中设好了）
    if sys.stdout and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        try:
            # Windows Terminal / VS Code / 大多数现代终端都支持
            C.RESET = '\033[0m'
            C.BOLD = '\033[1m'
            C.DIM = '\033[2m'
            C.RED = '\033[91m'
            C.GREEN = '\033[92m'
            C.YELLOW = '\033[93m'
            C.BLUE = '\033[94m'
            C.MAGENTA = '\033[95m'
            C.CYAN = '\033[96m'
            C.WHITE = '\033[97m'
            C.BG_DARK = '\033[48;5;236m'
            C.BOLD_RED = '\033[1;91m'
            C.BOLD_GREEN = '\033[1;92m'
            C.BOLD_YELLOW = '\033[1;93m'
            C.BOLD_CYAN = '\033[1;96m'
        except Exception:
            pass


def get_real_python() -> str:
    """获取真实的 Python 解释器路径（兼容 PyInstaller 打包）"""
    # 非打包模式直接用 sys.executable
    if not getattr(sys, 'frozen', False):
        return sys.executable

    # 打包为 exe 时，sys.executable 指向 exe 本身
    # 1) 优先使用项目内的 .venv
    venv_python = PROJECT_ROOT / '.venv' / 'Scripts' / 'python.exe'
    if venv_python.exists():
        return str(venv_python)

    # 2) 从 sys.base_prefix 查找（部分 PyInstaller 版本保留此值）
    base_python = Path(sys.base_prefix) / 'python.exe'
    if base_python.exists():
        return str(base_python)

    # 3) 从 PATH 查找，排除 setup.exe 自身
    try:
        r = subprocess.run(
            ['where', 'python'],
            capture_output=True, text=True, timeout=5, shell=True
        )
        for line in r.stdout.strip().splitlines():
            p = line.strip()
            if p and 'setup.exe' not in p.lower():
                return p
    except Exception:
        pass

    # 4) 最后回退
    return 'python'


def safe_print(*args, **kwargs):
    """安全打印，自动处理编码错误"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 回退：用纯文本替代 emoji
        text = ' '.join(str(a) for a in args)
        replacements = {
            '🏠': '[House]', '📦': '[Package]', '📌': '[Pin]',
            '✅': '[OK]', '✔': '[OK]', '✘': '[FAIL]', '❌': '[FAIL]',
            '⚠': '[Warn]', 'ℹ': '[Info]', '🛑': '[Stop]',
            '🖥️': '[PC]', '📋': '[List]', '📂': '[Folder]',
            '🔗': '[Link]', '👤': '[User]', '🔐': '[Lock]',
            '⚡': '[Fast]', '💾': '[Save]', '🔄': '[Refresh]',
            '🔧': '[Tool]', '🚀': '[Start]', '🌐': '[Net]',
            '▶': '>', '❯': '>', '●': '*', '▪': '*',
            '💰': '[Money]', '🏆': '[Award]',
            '⚙': '[Gear]', '💥': '[Boom]', '🗑': '[Trash]',
            '📊': '[Chart]', '🔍': '[Search]', '🎯': '[Target]',
        }
        for emoji, alt in replacements.items():
            text = text.replace(emoji, alt)
        try:
            print(text, **kwargs)
        except UnicodeEncodeError:
            # 极端情况：全 ASCII 回退
            ascii_text = text.encode('ascii', errors='replace').decode('ascii')
            print(ascii_text, **kwargs)


# ============================================================
# 打印函数（全部使用 safe_print）
# ============================================================
def print_banner():
    """打印欢迎横幅"""
    banner = f"""
{C.BOLD_CYAN}
{'='*54}
     {C.BOLD}[House]{C.RESET}{C.BOLD_CYAN}  {T('app_name')}  v1.0
     {C.BOLD}[Package]{C.RESET}{C.BOLD_CYAN}  {T('setup_wizard')}
{'='*54}{C.RESET}

{C.YELLOW}[Guide]{C.RESET} {T('guide_desc')}
"""
    safe_print(banner)


def print_step(step: int, total: int, title: str):
    safe_print(f'\n{C.BOLD}{C.BLUE}--- [{step}/{total}] {title} ---{C.RESET}\n')


def print_info(msg: str):
    safe_print(f'  {C.BLUE}i{C.RESET} {msg}')


def print_ok(msg: str):
    safe_print(f'  {C.GREEN}v{C.RESET} {msg}')


def print_warn(msg: str):
    safe_print(f'  {C.YELLOW}*{C.RESET} {msg}')


def print_error(msg: str):
    safe_print(f'  {C.RED}x{C.RESET} {msg}')


def print_result(msg: str):
    safe_print(f'  {C.BOLD_GREEN}[OK]{C.RESET} {msg}')


def input_ask(prompt: str, default: str = '', validate=None,
              allow_empty: bool = True) -> str:
    """
    带默认值和验证的输入函数。
    返回 stripped 字符串，空值返回 default。
    """
    while True:
        if default:
            full_prompt = f'{C.CYAN}>{C.RESET} {prompt} [{C.YELLOW}{default}{C.RESET}]: '
        else:
            full_prompt = f'{C.CYAN}>{C.RESET} {prompt}: '

        try:
            value = input(full_prompt).strip()
        except (EOFError, KeyboardInterrupt):
            safe_print()
            print_warn(T('user_cancelled'))
            sys.exit(0)

        if not value:
            if default:
                return default
            if allow_empty:
                return ''
            print_warn(T('field_empty'))
            continue

        if validate:
            err_msg = validate(value)
            if err_msg:
                print_error(err_msg)
                continue

        return value


def input_yes_no(prompt: str, default: bool = True) -> bool:
    """是/否 选择"""
    hint = f'{C.YELLOW}Y{C.RESET}/n' if default else f'y/{C.YELLOW}N{C.RESET}'
    full = f'{C.CYAN}>{C.RESET} {prompt} [{hint}]: '
    try:
        value = input(full).strip().lower()
    except (EOFError, KeyboardInterrupt):
        safe_print()
        return default
    if not value:
        return default
    if value in ('y', 'yes', '1'):
        return True
    if value in ('n', 'no', '0'):
        return False
    return default


def input_select(prompt: str, options: list, default_index: int = 0) -> int:
    """选项选择器，返回选中项的 index"""
    safe_print(f'  {C.CYAN}>{C.RESET} {prompt}')
    for i, opt in enumerate(options):
        marker = f'{C.YELLOW}>{C.RESET} ' if i == default_index else '  '
        safe_print(f'    {marker} {C.BOLD}{i+1}{C.RESET}. {opt}')
    while True:
        try:
            raw = input(f'  {T("chinese_input")} (1-{len(options)}, {T("default")} {default_index+1}): ').strip()
        except (EOFError, KeyboardInterrupt):
            safe_print()
            return default_index
        if not raw:
            return default_index
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print_warn(f'{T("chinese_input")} {T("enter_valid_num")} (1-{len(options)})')


# ============================================================
# 检测函数
# ============================================================
def detect_python() -> tuple:
    """检测系统中的 Python 信息。返回 (python_path, version_str, version_tuple)"""
    python_path = get_real_python()
    version_str = sys.version
    version_tuple = sys.version_info[:3]
    return python_path, version_str, version_tuple


def detect_pip(python_path: str) -> bool:
    """检测 pip 是否可用"""
    try:
        r = subprocess.run([python_path, '-m', 'pip', '--version'],
                           capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def detect_git() -> str:
    """检测 git 是否可用，返回路径或空字符串"""
    try:
        r = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ''


def is_port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_process_on_port(port: int) -> list:
    """尝试查找占用端口的进程信息"""
    if os.name == 'nt':
        try:
            r = subprocess.run(
                f'netstat -ano | findstr ":{port} "',
                capture_output=True, text=True, shell=True, timeout=5
            )
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
            pids = set()
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    pids.add(parts[-1])
            result = []
            for pid in pids:
                try:
                    r2 = subprocess.run(
                        f'tasklist /FI "PID eq {pid}" /FO CSV /NH',
                        capture_output=True, text=True, shell=True, timeout=5
                    )
                    if r2.stdout.strip():
                        result.append(f'PID={pid} ({r2.stdout.strip()})')
                except Exception:
                    result.append(f'PID={pid}')
            return result
        except Exception:
            return [f'PID unknown (port {port} is in use)']
    else:
        try:
            r = subprocess.run(
                ['lsof', '-i', f':{port}'],
                capture_output=True, text=True, timeout=5
            )
            return r.stdout.splitlines() if r.stdout.strip() else []
        except Exception:
            return []


# ============================================================
# 核心功能模块
# ============================================================

def step_environment_check(config: dict) -> dict:
    """步骤1: 环境检测"""
    print_step(1, 7, T('step_env'))

    # Python
    python_path, version_str, version_tuple = detect_python()
    current_dir = str(PROJECT_ROOT)

    print_info(f'{T("current_dir")}: {C.YELLOW}{current_dir}{C.RESET}')
    print_info(f'{T("python")}: {C.YELLOW}{python_path}{C.RESET}')

    ver_ok = version_tuple[:2] >= MIN_PYTHON_VERSION
    if ver_ok:
        print_ok(f'Python {version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]} (>= {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]})')
    else:
        print_warn(f'Python {version_tuple[0]}.{version_tuple[1]} ({T("python_ver_warn")} >= {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]})')

    # pip
    pip_ok = detect_pip(python_path)
    if pip_ok:
        print_ok(T('pip_ok'))
    else:
        print_warn(T('pip_missing'))

    # Git
    git_info = detect_git()
    if git_info:
        print_ok(f'{T("git_info")}: {git_info}')
    else:
        print_info(T('git_missing'))

    # 项目结构
    checks = {
        'backend/app.py': APP_PY.exists(),
        'frontend/index.html': FRONTEND_DIR.exists() and (FRONTEND_DIR / 'index.html').exists(),
        'backend/requirements.txt': REQUIREMENTS.exists(),
        'tools/': TOOLS_DIR.exists(),
    }
    all_ok = True
    for name, ok in checks.items():
        if ok:
            print_ok(f'{name} - {T("file_ok")}')
        else:
            print_warn(f'{name} - {T("file_missing")}')
            all_ok = False

    if all_ok:
        print_result(T('struct_ok'))
    else:
        print_warn(T('struct_warn'))

    # venv
    has_venv = (PROJECT_ROOT / '.venv').exists()
    if has_venv:
        print_info(f'{T("venv_detected")}: {C.YELLOW}.venv{C.RESET}')
        safe_print(f'  {C.DIM}{T("venv_explain")}{C.RESET}')
        use_venv = input_yes_no(T('use_venv'), default=True)
        if use_venv:
            venv_python = PROJECT_ROOT / '.venv' / 'Scripts' / 'python.exe'
            if venv_python.exists():
                python_path = str(venv_python)
                print_ok(f'{T("venv_found")}: {python_path}')
            else:
                print_warn(f'{T("venv_not_found")}: {venv_python}')
    else:
        print_info(T('no_venv'))

    config['python_path'] = python_path
    config['pip_ok'] = pip_ok
    config['git_info'] = git_info
    return config


def step_port_config(config: dict) -> dict:
    """步骤2: 端口配置"""
    print_step(2, 7, T('step_port'))

    current_port = DEFAULT_PORT
    if APP_PY.exists():
        content = APP_PY.read_text(encoding='utf-8')
        m = re.search(r"port\s*=\s*(\d+)", content)
        if m:
            current_port = int(m.group(1))

    print_info(f'{T("current_port")}: {C.YELLOW}{current_port}{C.RESET}')

    if is_port_in_use(current_port):
        procs = find_process_on_port(current_port)
        print_warn(f'{T("port_in_use")} ({current_port})')
        for p in procs:
            safe_print(f'    {C.RED}{p}{C.RESET}')
        change_port = input_yes_no(T('change_port'), default=True)
    else:
        print_ok(f'{T("port_available")} ({current_port})')
        change_port = input_yes_no(T('change_port'), default=False)

    if change_port:
        while True:
            port_str = input_ask(T('enter_port'), default=str(current_port))
            try:
                new_port = int(port_str)
                if new_port < 1 or new_port > 65535:
                    print_error(T('port_range_err'))
                    continue
                if is_port_in_use(new_port):
                    print_warn(f'Port {new_port} {T("port_in_use")}')
                    procs = find_process_on_port(new_port)
                    for p in procs:
                        safe_print(f'    {C.RED}{p}{C.RESET}')
                    force = input_yes_no(T('still_use_port'), default=False)
                    if not force:
                        continue
                config['port'] = new_port
                print_ok(f'{T("selected_port")}: {new_port}')
                break
            except ValueError:
                print_error(T('enter_valid_num'))
    else:
        config['port'] = current_port

    safe_print()
    print_info(T('lan_desc'))
    allow_lan = input_yes_no(T('allow_lan'), default=True)
    config['host'] = '0.0.0.0' if allow_lan else '127.0.0.1'
    print_ok(f'{T("listen_addr")}: {config["host"]}  (port: {config["port"]})')
    return config


def step_install_deps(config: dict) -> dict:
    """步骤3: 安装依赖"""
    print_step(3, 7, T('step_deps'))

    python_path = config['python_path']

    deps = [
        ('flask', 'flask'),
        ('flask-cors', 'flask_cors'),
        ('psutil', 'psutil'),
    ]

    print_info(f'{T("deps_title")}:')
    for name, _ in deps:
        safe_print(f'  * {C.YELLOW}{name}{C.RESET}')

    installed = {}
    try:
        r = subprocess.run(
            [python_path, '-m', 'pip', 'list', '--format=json'],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            for pkg in json.loads(r.stdout):
                installed[pkg['name'].lower()] = pkg['version']
    except Exception:
        pass

    missing = []
    for name, import_name in deps:
        pkg_name = name.lower().replace('-', '_')
        if pkg_name in installed or import_name in installed:
            ver = installed.get(pkg_name) or installed.get(import_name, '?')
            print_ok(f'{name} ({T("deps_installed")} v{ver})')
        else:
            print_info(f'{name} ({T("deps_missing")})')
            missing.append(name)

    if not missing:
        print_result(T('all_deps_ready'))
        config['deps_installed'] = True
        config['should_install_deps'] = False
        return config

    if not config.get('pip_ok'):
        print_warn(T('pip_unavail'))
        safe_print(f'    {C.YELLOW}{python_path} -m pip install -r {REQUIREMENTS}{C.RESET}')
        config['deps_installed'] = False
        config['should_install_deps'] = False
        return config

    do_install = input_yes_no(T('install_deps_q'), default=True)
    config['should_install_deps'] = do_install
    if do_install:
        print_info(f'{C.YELLOW}{T("will_install")}: pip install -r requirements.txt{C.RESET}')
    else:
        print_info(T('skip_deps'))
    return config


def step_admin_setup(config: dict) -> dict:
    """步骤4: 管理员设置"""
    print_step(4, 7, T('step_admin'))

    port_str = str(config.get('port', DEFAULT_PORT))
    print_info(f'{T("admin_desc")} (http://localhost:{port_str}/admin/accounts)')

    already_configured = False
    settings = {}
    if SETTINGS_JSON.exists():
        try:
            settings = json.loads(SETTINGS_JSON.read_text(encoding='utf-8'))
            if settings.get('admin_username') and settings.get('admin_password'):
                already_configured = True
                print_ok(f'{T("admin_exists")}: {C.YELLOW}{settings["admin_username"]}{C.RESET}')
        except Exception:
            pass

    if already_configured:
        reset = input_yes_no(T('reset_admin'), default=False)
        if not reset:
            print_info(T('keep_admin'))
            config['admin_username'] = settings['admin_username']
            config['admin_password'] = settings['admin_password']
            config['admin_configured'] = True
            return config

    safe_print()
    username = input_ask(T('admin_username'), allow_empty=False)
    while True:
        password = input_ask(T('admin_password'))
        if len(password) < 4:
            print_error(T('pwd_min_err'))
            continue
        confirm = input_ask(T('confirm_pwd'))
        if password != confirm:
            print_error(T('pwd_mismatch'))
            continue
        break

    config['admin_username'] = username
    config['admin_password'] = password
    config['admin_configured'] = True
    print_info(f'{C.YELLOW}{T("config_admin")}: {username}{C.RESET}')
    return config


def step_optional_features(config: dict) -> dict:
    """步骤5: 可选功能配置"""
    print_step(5, 7, T('step_features'))

    # Debug mode
    print_info(T('debug_desc'))
    debug_mode = input_yes_no(T('enable_debug'), default=False)
    config['debug'] = debug_mode
    print_ok(f'{T("debug_on") if debug_mode else T("debug_off")}')

    safe_print()

    # Auto-start
    print_info(T('auto_start_desc'))
    config['auto_start'] = input_yes_no(T('add_startup'), default=False)
    if config['auto_start']:
        print_info(f'{C.YELLOW}{T("will_apply")}: {T("autostart")}{C.RESET}')

    safe_print()

    # Desktop shortcuts
    print_info(T('shortcut_desc'))
    config['desktop_shortcut'] = input_yes_no(T('create_shortcut'), default=True)
    if config['desktop_shortcut']:
        print_info(f'{C.YELLOW}{T("will_create")}: {T("shortcuts")}{C.RESET}')

    safe_print()

    # Auto browser
    auto_browser = input_yes_no(T('auto_browser'), default=True)
    config['auto_browser'] = auto_browser
    print_ok(f'{T("browser_on") if auto_browser else T("browser_off")}')

    return config


def _setup_auto_start(config: dict) -> bool:
    """添加开机自启（Windows 任务计划程序）"""
    if os.name != 'nt':
        print_warn(T('autostart_win'))
        return False

    vbs_path = START_VBS
    if not vbs_path.exists():
        print_warn(T('autostart_novbs'))
        return False

    task_name = 'FamilyMoneyServer'
    try:
        r = subprocess.run(
            f'schtasks /Query /TN "{task_name}"',
            capture_output=True, text=True, shell=True, timeout=5
        )
        if r.returncode == 0:
            print_info(T('task_exists'))
            update = input_yes_no(T('task_update'), default=False)
            if not update:
                return True
            subprocess.run(
                f'schtasks /Delete /TN "{task_name}" /F',
                capture_output=True, shell=True, timeout=5
            )

        cmd = (
            f'schtasks /Create /SC ONLOGON /TN "{task_name}" '
            f'/TR "wscript.exe \\"{vbs_path}\\"" /RL HIGHEST /F'
        )
        r = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
        if r.returncode == 0:
            print_result(T('autostart_ok'))
            return True
        else:
            print_warn(f'{T("autostart_fail")}: {r.stderr.strip()}')
            return False
    except Exception as e:
        print_warn(f'{T("autostart_fail")}: {e}')
        return False


def _create_desktop_shortcuts(config: dict) -> bool:
    """创建桌面快捷方式（使用 VBScript 方式）"""
    return _create_shortcut_vbs(config)


def _create_shortcut_vbs(config: dict) -> bool:
    """用 VBScript 创建桌面快捷方式"""
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    if not os.path.exists(desktop):
        desktop = os.path.join(os.environ.get('USERPROFILE', 'C:\\'), 'Desktop')
    port = config.get('port', DEFAULT_PORT)

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    app_name = T('app_name')
    vbs_code = f'''
Set WshShell = WScript.CreateObject("WScript.Shell")
desktop = WshShell.SpecialFolders("Desktop")

' Start server shortcut
Set Shortcut = WshShell.CreateShortcut(desktop & "\\{app_name} - Start Server.lnk")
Shortcut.TargetPath = "{START_BAT}"
Shortcut.WorkingDirectory = "{TOOLS_DIR}"
Shortcut.Description = "Start {app_name} backend server"
Shortcut.Save

' Homepage shortcut
Set Shortcut2 = WshShell.CreateShortcut(desktop & "\\{app_name} - Open Homepage.lnk")
Shortcut2.TargetPath = "http://localhost:{port}"
Shortcut2.Description = "Open {app_name}"
Shortcut2.Save
'''
    try:
        vbs_temp = TOOLS_DIR / '_create_shortcut.vbs'
        vbs_temp.write_text(vbs_code, encoding='utf-8')
        subprocess.run(['wscript.exe', str(vbs_temp)], capture_output=True, timeout=10)
        vbs_temp.unlink(missing_ok=True)
        print_result(T('shortcut_ok'))
        return True
    except Exception as e:
        print_warn(f'{T("shortcut_fail")}: {e}')
        return False


# ============================================================
# 应用配置到文件
# ============================================================

def apply_port_to_app_py(config: dict) -> bool:
    """将端口和 host 配置写入 app.py"""
    port = config.get('port', DEFAULT_PORT)
    host = config.get('host', '0.0.0.0')
    debug = config.get('debug', False)

    if not APP_PY.exists():
        print_error(f'app.py {T("app_not_found")}: {APP_PY}')
        return False

    content = APP_PY.read_text(encoding='utf-8')

    # 备份原始文件
    if not APP_PY_BAK.exists():
        APP_PY_BAK.write_text(content, encoding='utf-8')
        print_info(f'{T("backup_created")}: {APP_PY_BAK.name}')

    # 替换 app.run 行（保留原始缩进）
    pattern = r"(\s*)(app\.run\([^)]*\))"
    m = re.search(pattern, content)
    if m:
        indent = m.group(1)
        new_run = f"{indent}app.run(host='{host}', port={port}, debug={str(debug)})"
        content = re.sub(pattern, new_run, content)
        APP_PY.write_text(content, encoding='utf-8')
        print_ok(f'app.py {T("app_updated")}: host={host} port={port} debug={debug}')
        return True
    else:
        print_warn(T('no_apprun_found'))
        return False


def generate_startup_scripts(config: dict) -> bool:
    """生成本地启动脚本"""
    port = config.get('port', DEFAULT_PORT)
    host = config.get('host', '0.0.0.0')
    admin_user = config.get('admin_username', 'admin')

    # 优先使用 .venv 的 Python（项目自带依赖）
    venv_python = PROJECT_ROOT / '.venv' / 'Scripts' / 'python.exe'
    if venv_python.exists():
        python_path = str(venv_python)
    else:
        python_path = config.get('python_path', get_real_python())

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 更新 start.bat（通过 wscript 静默调用 VBS，窗口自动关闭） ----
    bat_content = f'''@echo off
chcp 65001 >nul

echo ==================================================
echo   {T('app_name')} - Start Server
echo ==================================================
echo.

REM 调用 VBS 静默启动（无窗口运行 Flask）
start "" /B wscript.exe "%~dp0start_backend.vbs"

echo {T('launch_sent')}
echo.
echo   {T('frontend_url')}: http://localhost:{DEFAULT_PORT}
echo   {T('admin_url')}: http://localhost:{DEFAULT_PORT}/admin/accounts
echo.
echo   {T('stop_hint')}
echo ==================================================
timeout /t 3 /nobreak >nul
'''
    START_BAT.write_text(bat_content, encoding='utf-8')
    print_ok(f'{T("updated")}: 快捷工具\\start.bat')

    # ---- 更新 start_backend.vbs（以隐藏窗口模式静默启动 Flask） ----
    vbs_content = f''''
' 家庭报销管理系统 - 静默启动后端服务
' 以完全隐藏的方式启动 Flask 后端，无任何弹窗

Dim objShell, objFSO, sScriptDir, sBackendDir, sPythonPath, sScriptPath

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 获取 backend 目录的绝对路径
sScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
sBackendDir = objFSO.GetAbsolutePathName(sScriptDir & "\\..\\backend")

sPythonPath = "{python_path}"
sScriptPath = sBackendDir & "\\app.py"

' 检查文件是否存在
If Not objFSO.FileExists(sPythonPath) Then
    WScript.Quit 1
End If

If Not objFSO.FileExists(sScriptPath) Then
    WScript.Quit 1
End If

' 以隐藏窗口模式启动 Flask（0=隐藏窗口, False=异步执行）
objShell.Run """" & sPythonPath & """ """ & sScriptPath & """", 0, False

Set objShell = Nothing
Set objFSO = Nothing
'''
    # VBS 必须用 ANSI 编码，否则 cscript 无法编译（UTF-8 BOM 会导致编译错误）
    with open(START_VBS, 'w', encoding='ansi') as f:
        f.write(vbs_content)
    print_ok(f'{T("updated")}: 快捷工具\\start_backend.vbs')

    # ---- 更新 close.bat（查端口杀进程，自动清理） ----
    close_content = f'''@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==================================================
echo   {T('app_name')} - Stop Server
echo ==================================================
echo.

echo {T('finding_port')} {port}...
set FOUND=0
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":{port} " ^| findstr LISTENING') do (
    set FOUND=1
    echo {T('found_pid')} %%p
    taskkill /F /PID %%p >nul 2>nul
    if !ERRORLEVEL! equ 0 (
        echo {T('killed_ok')}
    )
)

echo {T('cleaning_python')}
taskkill /F /IM python.exe >nul 2>nul
if !ERRORLEVEL! equ 0 (
    echo {T('cleaned_ok')}
) else (
    if !FOUND! equ 0 (
        echo {T('no_process_found')}
    ) else (
        echo {T('all_cleaned')}
    )
)

echo.
echo {T('done_press_any')}
pause >nul
endlocal
'''
    CLOSE_BAT.write_text(close_content, encoding='utf-8')
    print_ok(f'{T("updated")}: 快捷工具\\close.bat')

    # 创建 URL 快捷方式
    _update_tools_links(port)

    return True


def _update_tools_links(port: int):
    """更新快捷工具/中的 .url 文件"""
    # 首页 URL 快捷方式
    url_file = TOOLS_DIR / 'Home - FamilyMoney.url'
    url_file.write_text(
        f'[InternetShortcut]\r\nURL=http://localhost:{port}\r\n', encoding='utf-8'
    )
    # 后台 URL 快捷方式
    admin_url = TOOLS_DIR / 'Admin - Account Management.url'
    admin_url.write_text(
        f'[InternetShortcut]\r\nURL=http://localhost:{port}/admin/accounts\r\n', encoding='utf-8'
    )
    # 控制台 URL 快捷方式
    console_url = TOOLS_DIR / 'Server Console.url'
    console_url.write_text(
        f'[InternetShortcut]\r\nURL=http://localhost:{port}/admin/console\r\n', encoding='utf-8'
    )
    print_ok(f'{T("updated")}: .url shortcuts')


def generate_virtual_env_script(config: dict):
    """生成虚拟环境激活并启动的脚本（可选）"""
    has_venv = (PROJECT_ROOT / '.venv').exists()
    if not has_venv:
        return

    script = f'''@echo off
chcp 65001 >nul
echo Family Expense Manager - Virtual Env Start
echo.

cd /d "{PROJECT_ROOT}"
call "{PROJECT_ROOT}\\.venv\\Scripts\\activate.bat"

echo [OK] Virtual env activated: .venv
echo.

python "{APP_PY}"

pause
'''
    start_venv = TOOLS_DIR / 'start_with_venv.bat'
    start_venv.write_text(script, encoding='utf-8')
    print_ok(f'{T("created")}: 快捷工具\\start_with_venv.bat ({T("default")} venv start)')


# ============================================================
# 配置执行函数（一次性应用所有选择）
# ============================================================

def apply_install_deps(config: dict) -> bool:
    """实际安装依赖"""
    python_path = config['python_path']
    safe_print()
    print_info(T('installing'))
    try:
        r = subprocess.run(
            [python_path, '-m', 'pip', 'install', '-r', str(REQUIREMENTS)],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            print_result(T('deps_success'))
            config['deps_installed'] = True
            return True
        else:
            print_error(f'{T("install_failed")}')
            for line in r.stderr.splitlines():
                if line.strip():
                    safe_print(f'    {line.strip()}')
            print_warn(T('manual_install'))
            config['deps_installed'] = False
            return False
    except subprocess.TimeoutExpired:
        print_error(T('install_timeout'))
        config['deps_installed'] = False
        return False


def apply_admin_config(config: dict):
    """写入管理员配置到 settings.json"""
    if not config.get('admin_configured'):
        return
    settings = {}
    if SETTINGS_JSON.exists():
        try:
            settings = json.loads(SETTINGS_JSON.read_text(encoding='utf-8'))
        except Exception:
            pass
    settings['admin_username'] = config['admin_username']
    settings['admin_password'] = config['admin_password']
    settings['admin_setup_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    SETTINGS_JSON.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print_ok(f'{T("admin")} {config["admin_username"]} {T("admin_ok")}')


def show_config_preview(config: dict):
    """展示收集到的所有配置，等待用户确认"""
    port = config.get('port', DEFAULT_PORT)
    host = config.get('host', '0.0.0.0')
    debug = config.get('debug', False)
    admin_user = config.get('admin_username', '')
    admin_cfg = config.get('admin_configured', False)
    lan = (host == '0.0.0.0')

    safe_print(f'\n{C.BOLD_CYAN}{"=" * 50}{C.RESET}')
    safe_print(f'{C.BOLD}{" " * 18}{T("confirm_title")}{C.RESET}')
    safe_print(f'{C.BOLD_CYAN}{"=" * 50}{C.RESET}\n')

    # Python 路径
    safe_print(f'  {C.BOLD}{T("config_python")}:{C.RESET}  {config.get("python_path", "?")}')

    # 端口
    safe_print(f'  {C.BOLD}{T("config_port")}:{C.RESET}     {port}')

    # 监听地址
    if lan:
        safe_print(f'  {C.BOLD}{T("config_host")}:{C.RESET}    0.0.0.0 {C.DIM}{T("lan_accessible")}{C.RESET}')
    else:
        safe_print(f'  {C.BOLD}{T("config_host")}:{C.RESET}    127.0.0.1 {C.DIM}{T("local_only")}{C.RESET}')

    # 调试模式
    safe_print(f'  {C.BOLD}{T("config_debug")}:{C.RESET}   {T("debug_on") if debug else T("debug_off")}')

    # 管理员
    if admin_cfg and admin_user:
        safe_print(f'  {C.BOLD}{T("config_admin")}:{C.RESET}  {admin_user}')
    else:
        safe_print(f'  {C.BOLD}{T("config_admin")}:{C.RESET}  {C.DIM}{T("status_not_added")}{C.RESET}')

    # 依赖
    deps_ready = config.get('deps_installed', False)
    should_deps = config.get('should_install_deps', False)
    if deps_ready:
        safe_print(f'  {C.BOLD}{T("config_deps")}:{C.RESET}   {C.GREEN}{T("status_installed")}{C.RESET}')
    elif should_deps:
        safe_print(f'  {C.BOLD}{T("config_deps")}:{C.RESET}   {C.YELLOW}{T("will_install")}{C.RESET}')
    else:
        safe_print(f'  {C.BOLD}{T("config_deps")}:{C.RESET}   {C.DIM}{T("will_skip")}{C.RESET}')

    # 开机自启
    if config.get('auto_start'):
        safe_print(f'  {C.BOLD}{T("config_autostart")}:{C.RESET} {C.YELLOW}{T("will_apply")}{C.RESET}')
    else:
        safe_print(f'  {C.BOLD}{T("config_autostart")}:{C.RESET} {C.DIM}{T("will_not_apply")}{C.RESET}')

    # 桌面快捷方式
    if config.get('desktop_shortcut'):
        safe_print(f'  {C.BOLD}{T("config_shortcut")}:{C.RESET}  {C.YELLOW}{T("will_create")}{C.RESET}')
    else:
        safe_print(f'  {C.BOLD}{T("config_shortcut")}:{C.RESET}  {C.DIM}{T("will_not_create")}{C.RESET}')

    # 自动打开浏览器
    safe_print(f'  {C.BOLD}{T("config_browser")}:{C.RESET} {T("browser_on") if config.get("auto_browser", True) else T("browser_off")}')

    safe_print()


def apply_all_config(config: dict):
    """一次性应用所有配置"""
    print_step(6, 7, T('step_apply'))
    print_info(T('applying_config'))
    safe_print()

    # 1) 安装依赖
    if config.get('should_install_deps'):
        apply_install_deps(config)

    # 2) 写入管理员配置到 settings.json
    apply_admin_config(config)

    # 3) 端口和 host 写入 app.py
    apply_port_to_app_py(config)

    # 4) 生成/更新启动脚本
    generate_startup_scripts(config)

    # 5) 虚拟环境启动脚本
    generate_virtual_env_script(config)

    # 6) 开机自启
    if config.get('auto_start'):
        _setup_auto_start(config)

    # 7) 桌面快捷方式
    if config.get('desktop_shortcut'):
        _create_desktop_shortcuts(config)

    safe_print()
    print_result(T('config_applied'))


# ============================================================
# 服务器启动
# ============================================================

def start_server(config: dict):
    """启动服务器"""
    print_step(7, 7, T('step_start'))

    port = config.get('port', DEFAULT_PORT)
    python_path = config.get('python_path', get_real_python())
    auto_browser = config.get('auto_browser', True)

    print_info(f'Python: {python_path}')
    print_info(f'Script: {APP_PY}')
    print_info(f'Port: {port}')

    safe_print()
    print_info(T('start_info'))
    safe_print()

    try:
        proc = subprocess.Popen(
            [python_path, str(APP_PY)],
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        import time
        time.sleep(2)

        if proc.poll() is not None:
            print_error(T('start_failed'))
            try:
                output = proc.stdout.read(1024).decode('utf-8', errors='replace')
                safe_print(f'    {output}')
            except Exception:
                pass
            print_warn(T('manual_start'))
            safe_print(f'    cd {BACKEND_DIR}')
            safe_print(f'    {python_path} app.py')
            return

        print_result(f'{T("start_ok")} (PID: {proc.pid})')
        safe_print()
        safe_print(f'  {C.BOLD_GREEN}[Access]{C.RESET}')
        safe_print(f'     {C.BOLD_CYAN}http://localhost:{port}{C.RESET}')
        safe_print(f'     {C.BOLD_CYAN}http://localhost:{port}/admin/accounts{C.RESET}  ({T("admin_label")})')
        safe_print(f'     {C.BOLD_CYAN}http://localhost:{port}/admin/console{C.RESET}   (Console)')
        safe_print()
        safe_print(f'  {C.YELLOW}[{T("admin_label")}] {config.get("admin_username", "configured")}{C.RESET}')
        safe_print()
        safe_print(f'  {C.DIM}[{T("stop_server")}] {T("stop_hint")}{C.RESET}')

        pid_file = BACKEND_DIR / '.server.pid'
        pid_file.write_text(str(proc.pid), encoding='utf-8')

        if auto_browser:
            safe_print()
            print_info(T('open_browser'))
            webbrowser.open(f'http://localhost:{port}')

    except Exception as e:
        print_error(f'{T("start_err")}: {e}')
        print_warn(T('manual_start'))
        safe_print(f'    cd {BACKEND_DIR}')
        safe_print(f'    {python_path} app.py')


# ============================================================
# 总结报告
# ============================================================

def print_summary(config: dict):
    """打印配置总结"""
    port = config.get('port', DEFAULT_PORT)
    host = config.get('host', '0.0.0.0')
    debug = config.get('debug', False)
    admin_user = config.get('admin_username', 'admin')
    lan = T('lan_accessible') if host == '0.0.0.0' else T('local_only')
    deps_s = T('status_installed') if config.get('deps_installed') else T('status_none')
    auto_s = T('status_added') if config.get('auto_start') else T('status_not_added')
    short_s = T('status_created') if config.get('desktop_shortcut') else T('status_not_created')

    safe_print(f"""
{C.BOLD_CYAN}{'='*46}
       {T('summary_title')}
{'='*46}{C.RESET}

  {C.BOLD}{T('project')}:{C.RESET}      {PROJECT_ROOT}
  {C.BOLD}{T('python')}:{C.RESET}       {config.get('python_path', '?')}
  {C.BOLD}{T('listen')}:{C.RESET}       {host}:{port}  {lan}
  {C.BOLD}Debug:{C.RESET}        {"On" if debug else "Off"}
  {C.BOLD}{T('admin')}:{C.RESET}        {admin_user}
  {C.BOLD}{T('dependencies')}:{C.RESET} {deps_s}
  {C.BOLD}{T('autostart')}:{C.RESET}   {auto_s}
  {C.BOLD}{T('shortcuts')}:{C.RESET}    {short_s}

  {C.BOLD_GREEN}[{T('quick_start')}]{C.RESET}
     {T('double_click')} {C.YELLOW}快捷工具\\start.bat{C.RESET}
     {T('or_run')} {C.YELLOW}setup --quick{C.RESET}

  {C.BOLD_GREEN}[{T('stop_server')}]{C.RESET}
     {T('double_click')} {C.YELLOW}快捷工具\\close.bat{C.RESET}
""")


# ============================================================
# 快速模式
# ============================================================

def quick_setup():
    """快速模式 - 使用全部默认值"""
    safe_print(f'{C.BOLD_YELLOW}[Quick Mode] {T("guide_desc")}{C.RESET}\n')

    python_path = get_real_python()
    config = {
        'python_path': python_path,
        'port': DEFAULT_PORT,
        'host': '0.0.0.0',
        'debug': False,
        'pip_ok': False,
        'deps_installed': False,
        'admin_username': '',
        'admin_password': '',
        'admin_configured': False,
        'auto_browser': True,
        'auto_start': False,
        'desktop_shortcut': False,
    }

    # 检测环境
    pip_ok = detect_pip(python_path)
    config['pip_ok'] = pip_ok

    # 安装依赖
    if pip_ok:
        print_info(T('installing'))
        subprocess.run(
            [python_path, '-m', 'pip', 'install', '-r', str(REQUIREMENTS)],
            capture_output=True, text=True, timeout=120
        )
        config['deps_installed'] = True
        print_ok(T('deps_success'))

    # 设置管理员
    settings = {'admin_username': 'admin', 'admin_password': 'admin123',
                'admin_setup_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
    config['admin_username'] = 'admin'
    config['admin_password'] = 'admin123'
    config['admin_configured'] = True
    print_ok(f'{T("admin_ok")} (admin / admin123)')

    # 应用端口配置到 app.py
    apply_port_to_app_py(config)

    # 生成启动脚本
    generate_startup_scripts(config)

    # 总结
    print_summary(config)

    # 启动
    if input_yes_no(f'\n{T("start_now")}', default=True):
        start_server(config)


# ============================================================
# 主流程
# ============================================================

def main():
    init_console()
    print_banner()

    # 检测是否快速模式
    if len(sys.argv) > 1 and sys.argv[1] in ('--quick', '-q', '/quick'):
        quick_setup()
        return

    python_path = get_real_python()
    config = {
        'python_path': python_path,
        'port': DEFAULT_PORT,
        'host': '0.0.0.0',
        'debug': False,
        'pip_ok': False,
        'git_info': '',
        'deps_installed': False,
        'should_install_deps': False,
        'admin_username': '',
        'admin_password': '',
        'admin_configured': False,
        'auto_browser': True,
        'auto_start': False,
        'desktop_shortcut': False,
    }

    # ================================================================
    # 第一阶段：收集配置（只询问和检测，不执行任何修改操作）
    # ================================================================

    # === 步骤1: 环境检测 ===
    config = step_environment_check(config)
    input(f'\n{C.DIM}{T("enter_continue")}{C.RESET}')

    # === 步骤2: 端口配置 ===
    config = step_port_config(config)
    input(f'\n{C.DIM}{T("enter_continue")}{C.RESET}')

    # === 步骤3: 依赖检测（仅检测+询问，不实际安装） ===
    config = step_install_deps(config)
    input(f'\n{C.DIM}{T("enter_continue")}{C.RESET}')

    # === 步骤4: 管理员设置（仅询问，不写入文件） ===
    config = step_admin_setup(config)
    input(f'\n{C.DIM}{T("enter_continue")}{C.RESET}')

    # === 步骤5: 可选功能（仅询问，不执行） ===
    config = step_optional_features(config)
    input(f'\n{C.DIM}{T("enter_continue")}{C.RESET}')

    # ================================================================
    # 第二阶段：展示汇总并请求确认
    # ================================================================
    show_config_preview(config)

    if not input_yes_no(f'\n{C.BOLD}{T("confirm_apply")}{C.RESET}', default=True):
        safe_print(f'\n  {C.YELLOW}{T("user_cancelled")}{C.RESET}')
        safe_print(f'  {C.DIM}{T("goodbye")}{C.RESET}')
        return

    # ================================================================
    # 第三阶段：一次性应用所有配置
    # ================================================================
    apply_all_config(config)

    # ================================================================
    # 第四阶段：打印总结
    # ================================================================
    print_summary(config)

    # ================================================================
    # 第五阶段：启动服务器
    # ================================================================
    if input_yes_no(f'\n{T("start_now")}', default=True):
        start_server(config)
    else:
        safe_print()
        print_info(T('later_hint'))
        safe_print(f'  1. {T("double_click")} {C.YELLOW}快捷工具\\start.bat{C.RESET}')
        safe_print(f'  2. {T("or_run")} {C.YELLOW}python backend/app.py{C.RESET}')
        safe_print(f'  3. {T("or_run")} {C.YELLOW}setup --quick{C.RESET}')
        safe_print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        safe_print(f'\n{C.YELLOW}\n[Exit] {T("goodbye")}{C.RESET}')
        sys.exit(0)
    except Exception as e:
        safe_print(f'\n{C.RED}[Error] {e}{C.RESET}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
