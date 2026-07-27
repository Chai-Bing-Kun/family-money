# app.py - 家庭报销管理系统后端
# 运行方式：双击运行 或 在终端执行 python app.py
# 访问地址：http://localhost:3000
#
# 项目结构：
#   family-money/
#   ├── frontend/           ← 前端静态文件（由此服务提供）
#   │   └── index.html           # 主应用
#   ├── backend/            ← 后端（本文件所在目录）
#   │   ├── app.py               # 服务入口
#   │   ├── account-manager.html # 后端账号管理页面
#   │   ├── requirements.txt     # 依赖清单
#   │   ├── users.json           # 用户数据（自动生成）
#   │   ├── bills.json           # 账单数据（自动生成）
#   │   └── claims.json          # 认领数据（自动生成）
#   └── docs/               ← 项目文档
#       ├── 接口文档.txt
#       └── index快速导览.txt

import json
import os
import shutil
import sys
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder='.')
CORS(app)

# ================================================================
# 0. 全局错误处理
# ================================================================

# 全局未捕获异常处理器
@app.errorhandler(Exception)
def global_error_handler(e):
    import traceback
    error_detail = traceback.format_exc()
    print(f'❌ [全局异常] {str(e)}')
    print(f'📋 [详细堆栈] {error_detail}')
    return jsonify({
        'code': 5000,
        'message': f'服务器内部错误: {str(e)}',
        'error_detail': str(e) if app.debug else None
    }), 500

@app.errorhandler(404)
def not_found_handler(e):
    return jsonify({
        'code': 5001,
        'message': f'请求的资源不存在: {request.path}',
        'error_detail': '请检查 URL 地址是否正确'
    }), 404

@app.errorhandler(405)
def method_not_allowed_handler(e):
    return jsonify({
        'code': 5002,
        'message': f'请求方法不允许: {request.method} {request.path}',
        'error_detail': '请检查 HTTP 请求方法是否正确'
    }), 405

@app.errorhandler(413)
def payload_too_large_handler(e):
    return jsonify({
        'code': 5003,
        'message': '请求体过大',
        'error_detail': '请减小请求数据大小'
    }), 413

# ================================================================
# 0.5 日志文件配置 — 将 print 输出同时写入文件，供控制台查看
# ================================================================
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.log')

class LogWriter:
    """将 print 输出同时写入日志文件和终端"""
    def __init__(self, log_path, clean=False):
        self.log_path = log_path
        self.terminal = sys.stdout
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        if clean:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f'=== 服务启动于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===\n')

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        if message.strip():
            try:
                with open(self.log_path, 'a', encoding='utf-8') as f:
                    ts = datetime.now().strftime('%H:%M:%S')
                    f.write(f'[{ts}] {message}')
                    f.flush()
            except:
                pass  # 日志写入失败不影响服务运行

    def flush(self):
        self.terminal.flush()

# 主进程启动时清空日志；子进程（debug reloader）只追加不清空
_is_reloader = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
sys.stdout = LogWriter(LOG_FILE, clean=not _is_reloader)
sys.stderr = sys.stdout

# ================================================================
# 1. 文件路径
# ================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')
USERS_FILE = os.path.join(BASE_DIR, 'users.json')
BILLS_FILE = os.path.join(BASE_DIR, 'bills.json')
CLAIMS_FILE = os.path.join(BASE_DIR, 'claims.json')
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')

# ================================================================
# 2. 数据读写工具
# ================================================================
def read_json(filepath):
    """安全读取 JSON 文件，文件不存在或格式错误时返回默认值"""
    if not os.path.exists(filepath):
        print(f'⚠️ [文件不存在] {filepath}，返回空列表')
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f'❌ [JSON解析错误] 文件 {filepath} 格式损坏: {e}')
        # 备份损坏文件
        backup_path = filepath + '.bak'
        try:
            os.rename(filepath, backup_path)
            print(f'💾 [已备份] 损坏文件已重命名为 {backup_path}')
        except Exception:
            pass
        return []
    except PermissionError as e:
        print(f'❌ [权限错误] 无法读取文件 {filepath}: {e}')
        return []
    except Exception as e:
        print(f'❌ [读取异常] 文件 {filepath}: {e}')
        return []

def write_json(filepath, data):
    """安全写入 JSON 文件，包含备份和错误处理"""
    try:
        # 先写入临时文件，防止写入过程中崩溃导致数据损坏
        tmp_path = filepath + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # 写入成功后再替换原文件
        os.replace(tmp_path, filepath)
    except PermissionError as e:
        print(f'❌ [权限错误] 无法写入文件 {filepath}: {e}')
        raise Exception(f'文件写入权限不足: {e}')
    except OSError as e:
        print(f'❌ [磁盘错误] 写入文件 {filepath} 失败: {e}')
        raise Exception(f'磁盘写入失败，请检查磁盘空间: {e}')
    except Exception as e:
        print(f'❌ [写入异常] 文件 {filepath}: {e}')
        raise Exception(f'数据保存失败: {e}')

# ================================================================
# 3. 初始化默认数据
# ================================================================
def init_data():
    """初始化默认数据，包含启动检查"""
    print(f'📂 [数据检查] 用户文件: {USERS_FILE}')
    print(f'📂 [数据检查] 账单文件: {BILLS_FILE}')
    print(f'📂 [数据检查] 认领文件: {CLAIMS_FILE}')
    print(f'📂 [前端目录] {FRONTEND_DIR}')
    
    # 检查前端目录是否存在
    if not os.path.exists(FRONTEND_DIR):
        print(f'⚠️ [启动警告] 前端目录不存在: {FRONTEND_DIR}')
        print(f'⚠️ [启动警告] 请确保项目结构正确，否则网站将无法正确显示前端页面')
    
    users = read_json(USERS_FILE)
    if not users:
        users = [
            {
                "id": 1,
                "username": "mom",
                "password": "123456",
                "name": "妈妈",
                "role": "mother",
                "is_admin": False,
                "max_commitment": 300
            },
            {
                "id": 2,
                "username": "son",
                "password": "123456",
                "name": "儿子",
                "role": "son",
                "is_admin": False,
                "max_commitment": 100
            },
            {
                "id": 3,
                "username": "daughter",
                "password": "123456",
                "name": "女儿",
                "role": "daughter",
                "is_admin": False,
                "max_commitment": 80
            }
        ]
        write_json(USERS_FILE, users)
    
    if not os.path.exists(BILLS_FILE):
        write_json(BILLS_FILE, [])
    if not os.path.exists(CLAIMS_FILE):
        write_json(CLAIMS_FILE, [])
    
    # 确保备份目录存在
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)

init_data()

# ================================================================
# 4. 工具函数
# ================================================================
def get_next_id(data):
    if not data:
        return 1
    return max(item.get('id', 0) for item in data) + 1

def find_user_by_username(username):
    users = read_json(USERS_FILE)
    for u in users:
        if u.get('username') == username:
            return u
    return None

def find_user_by_id(user_id):
    users = read_json(USERS_FILE)
    for u in users:
        if u.get('id') == user_id:
            return u
    return None

def get_user_name(user_id):
    u = find_user_by_id(user_id)
    return u.get('name', '未知') if u else '未知'

def get_claims_by_bill(bill_id):
    claims = read_json(CLAIMS_FILE)
    return [c for c in claims if c.get('bill_id') == bill_id]

def get_claimed_amount(bill_id):
    claims = get_claims_by_bill(bill_id)
    return sum(c.get('amount', 0) for c in claims)

def get_user_claimed_amount(user_id):
    claims = read_json(CLAIMS_FILE)
    return sum(c.get('amount', 0) for c in claims 
               if c.get('claimant_id') == user_id and c.get('status') == 'pending')

def get_user_receivable(user_id):
    claims = read_json(CLAIMS_FILE)
    bills = read_json(BILLS_FILE)
    total = 0
    for c in claims:
        if c.get('status') != 'pending':
            continue
        bill = next((b for b in bills if b.get('id') == c.get('bill_id')), None)
        if bill and bill.get('purchaser_id') == user_id:
            total += c.get('amount', 0)
    return total

def get_user_payable(user_id):
    claims = read_json(CLAIMS_FILE)
    return sum(c.get('amount', 0) for c in claims 
               if c.get('claimant_id') == user_id and c.get('status') == 'pending')

# ================================================================
# 4.5 管理员配置工具（settings.json）
# ================================================================
def read_settings():
    """读取 settings.json 配置"""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def write_settings(data):
    """写入 settings.json 配置"""
    try:
        tmp_path = SETTINGS_FILE + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, SETTINGS_FILE)
    except Exception as e:
        print(f'❌ [写入配置异常] {e}')
        raise Exception(f'保存配置失败: {e}')

def is_admin_configured():
    """检查管理员是否已配置"""
    s = read_settings()
    return bool(s.get('admin_username') and s.get('admin_password'))

def check_admin_credentials(username, password):
    """验证管理员账号密码"""
    s = read_settings()
    return s.get('admin_username') == username and s.get('admin_password') == password

# ================================================================
# 4.6 健康检查
# ================================================================
@app.route('/api/ping', methods=['GET'])
def ping():
    """前端用于检测后端是否在线的健康检查接口"""
    return jsonify({
        'code': 0,
        'message': 'pong',
        'data': {
            'status': 'ok',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    })

# ================================================================
# 5. 登录接口
# ================================================================
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 1000, 'message': '请求数据为空，请提供登录信息', 'error_detail': 'POST body is empty or not valid JSON'})
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'code': 1000, 'message': '账号和密码不能为空', 'error_detail': '请填写完整的登录信息'})
        
        # 先检查是否为 settings.json 中的管理员
        if check_admin_credentials(username, password):
            token = str(uuid.uuid4())
            admin_settings = read_settings()
            return jsonify({
                'code': 0,
                'message': '管理员登录成功',
                'data': {
                    'token': token,
                    'user_id': -1,
                    'username': admin_settings.get('admin_username', username),
                    'name': '管理员',
                    'role': 'admin',
                    'is_admin': True,
                    'max_commitment': 0
                }
            })
        
        user = find_user_by_username(username)
        if not user or user.get('password') != password:
            return jsonify({'code': 1001, 'message': '账号或密码错误'})
        
        token = str(uuid.uuid4())
        return jsonify({
            'code': 0,
            'message': '登录成功',
            'data': {
                'token': token,
                'user_id': user.get('id'),
                'username': user.get('username'),
                'name': user.get('name'),
                'role': user.get('role'),
                'is_admin': user.get('is_admin', False),
                'max_commitment': user.get('max_commitment', 0)
            }
        })
    except Exception as e:
        print(f'❌ [登录接口异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'登录服务异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 6. 仪表盘
# ================================================================
@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    try:
        users = read_json(USERS_FILE)
        bills = read_json(BILLS_FILE)
        
        total_commitment = sum(u.get('max_commitment', 0) for u in users)
        total_pending = 0
        total_settled = 0
        
        for b in bills:
            if b.get('status') == 'settled':
                total_settled += 1
            else:
                claimed = get_claimed_amount(b.get('id'))
                total_pending += b.get('total_amount', 0) - claimed
        
        # 获取当前登录用户 ID
        current_user_id = request.args.get('user_id', type=int)
        
        members = []
        current_user_data = {}
        for u in users:
            used = get_user_claimed_amount(u.get('id'))
            member = {
                'id': u.get('id'),
                'username': u.get('username'),
                'name': u.get('name'),
                'role': u.get('role'),
                'is_admin': u.get('is_admin', False),
                'max_commitment': u.get('max_commitment', 0),
                'used': used,
                'remain': u.get('max_commitment', 0) - used,
                'receivable': get_user_receivable(u.get('id')),
                'payable': get_user_payable(u.get('id'))
            }
            members.append(member)
            if u.get('id') == current_user_id:
                current_user_data = member
        
        if not current_user_data:
            current_user_data = members[0] if members else {}
        
        # 获取当前用户的应付/应收明细
        claims_data = read_json(CLAIMS_FILE)
        bills_data = read_json(BILLS_FILE)
        payable_detail = []
        receivable_detail = []
        uid = current_user_data.get('id')
        for c in claims_data:
            if c.get('status') != 'pending':
                continue
            bill = next((b for b in bills_data if b.get('id') == c.get('bill_id')), None)
            if not bill:
                continue
            # 当前用户是认领人 → 应付款（转给购买人）
            if c.get('claimant_id') == uid:
                payable_detail.append({
                    'claim_id': c.get('id'),
                    'bill_id': bill.get('id'),
                    'bill_title': bill.get('title'),
                    'receiver_name': get_user_name(bill.get('purchaser_id')),
                    'amount': c.get('amount'),
                    'payer_confirmed': c.get('payer_confirmed', False)
                })
            # 当前用户是购买人 → 应收款（认领人付给他）
            if bill.get('purchaser_id') == uid:
                receivable_detail.append({
                    'claim_id': c.get('id'),
                    'bill_id': bill.get('id'),
                    'bill_title': bill.get('title'),
                    'payer_name': get_user_name(c.get('claimant_id')),
                    'amount': c.get('amount'),
                    'receiver_confirmed': c.get('receiver_confirmed', False)
                })
        
        current_user_data['payable_detail'] = payable_detail
        current_user_data['receivable_detail'] = receivable_detail
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'totalCommitment': total_commitment,
                'totalPending': total_pending,
                'totalAvailable': total_commitment - total_pending,
                'totalSettled': total_settled,
                'members': members,
                'currentUser': current_user_data
            }
        })
    except Exception as e:
        print(f'❌ [仪表盘接口异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取仪表盘数据异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 7. 账单接口
# ================================================================
@app.route('/api/bills', methods=['GET'])
def get_bills():
    try:
        bills = read_json(BILLS_FILE)
        status = request.args.get('status', '')
        
        if status and status != 'all':
            bills = [b for b in bills if b.get('status') == status]
        if not status:
            bills = [b for b in bills if b.get('status') != 'settled']
        
        result = []
        for b in bills:
            claimed = get_claimed_amount(b.get('id'))
            # 获取该账单的认领人信息
            claims = get_claims_by_bill(b.get('id'))
            claimants = []
            for c in claims:
                claimants.append({
                    'claimant_id': c.get('claimant_id'),
                    'claimant_name': get_user_name(c.get('claimant_id')),
                    'amount': c.get('amount'),
                    'status': c.get('status'),
                    'status_text': '已结清' if c.get('status') == 'settled' else '待确认',
                    'payer_confirmed': c.get('payer_confirmed', False),
                    'receiver_confirmed': c.get('receiver_confirmed', False)
                })
            result.append({
                'id': b.get('id'),
                'title': b.get('title'),
                'total_amount': b.get('total_amount', 0),
                'purchaser_id': b.get('purchaser_id'),
                'purchaser_name': get_user_name(b.get('purchaser_id')),
                'status': b.get('status'),
                'claimed_amount': claimed,
                'remaining': b.get('total_amount', 0) - claimed,
                'created_at': b.get('created_at', ''),
                'settled_at': b.get('settled_at'),
                'claimants': claimants
            })
        return jsonify({'code': 0, 'message': 'success', 'data': result})
    except Exception as e:
        print(f'❌ [账单列表接口异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取账单列表异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/bills/<int:bill_id>', methods=['GET'])
def get_bill_detail(bill_id):
    try:
        bills = read_json(BILLS_FILE)
        bill = next((b for b in bills if b.get('id') == bill_id), None)
        if not bill:
            return jsonify({'code': 404, 'message': f'账单不存在 (ID: {bill_id})'})
        
        claims = get_claims_by_bill(bill_id)
        claim_list = []
        for c in claims:
            claim_list.append({
                'id': c.get('id'),
                'claimant_id': c.get('claimant_id'),
                'claimant_name': get_user_name(c.get('claimant_id')),
                'amount': c.get('amount'),
                'status': c.get('status'),
                'status_text': '已结清' if c.get('status') == 'settled' else '待确认',
                'status_class': 'settled' if c.get('status') == 'settled' else 'pending',
                'payer_confirmed': c.get('payer_confirmed', False),
                'receiver_confirmed': c.get('receiver_confirmed', False),
                'created_at': c.get('created_at', '')
            })
        
        claimed = get_claimed_amount(bill_id)
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'id': bill.get('id'),
                'title': bill.get('title'),
                'total_amount': bill.get('total_amount', 0),
                'purchaser_id': bill.get('purchaser_id'),
                'purchaser_name': get_user_name(bill.get('purchaser_id')),
                'status': bill.get('status'),
                'claimed_amount': claimed,
                'remaining': bill.get('total_amount', 0) - claimed,
                'created_at': bill.get('created_at', ''),
                'settled_at': bill.get('settled_at'),
                'claims': claim_list
            }
        })
    except Exception as e:
        print(f'❌ [账单详情接口异常] bill_id={bill_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取账单详情异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/bills', methods=['POST'])
def create_bill():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 1000, 'message': '请求数据为空', 'error_detail': '请提供账单信息'})
        if not data.get('title'):
            return jsonify({'code': 1000, 'message': '账单名称不能为空', 'error_detail': '请填写账单标题'})
        
        amount = float(data.get('total_amount', 0))
        if amount <= 0:
            return jsonify({'code': 1000, 'message': '账单金额必须大于0', 'error_detail': f'当前金额: {amount}'})
        
        bills = read_json(BILLS_FILE)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_bill = {
            'id': get_next_id(bills),
            'title': data.get('title', ''),
            'total_amount': amount,
            'purchaser_id': int(data.get('purchaser_id', 1)),
            'status': 'pending',
            'created_at': now,
            'settled_at': None
        }
        bills.append(new_bill)
        write_json(BILLS_FILE, bills)
        return jsonify({'code': 0, 'message': '账单创建成功', 'data': new_bill})
    except (ValueError, TypeError) as e:
        print(f'❌ [创建账单-参数错误] {e}')
        return jsonify({'code': 1000, 'message': f'账单参数格式错误: {str(e)}', 'error_detail': '请检查金额和用户ID是否为有效数字'})
    except Exception as e:
        print(f'❌ [创建账单接口异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'创建账单异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 8. 认领接口
# ================================================================
@app.route('/api/claims', methods=['POST'])
def create_claim():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 1000, 'message': '请求数据为空', 'error_detail': '请提供认领信息'})
        
        bill_id = int(data.get('bill_id', 0))
        claimant_id = int(data.get('claimant_id', 0))
        amount = float(data.get('amount', 0))
        
        if bill_id <= 0 or claimant_id <= 0:
            return jsonify({'code': 1000, 'message': '参数错误', 'error_detail': '账单ID和认领人ID无效'})
        if amount <= 0:
            return jsonify({'code': 1000, 'message': '认领金额必须大于0', 'error_detail': f'当前金额: {amount}'})
        
        bills = read_json(BILLS_FILE)
        bill = next((b for b in bills if b.get('id') == bill_id), None)
        if not bill:
            return jsonify({'code': 404, 'message': f'账单不存在 (ID: {bill_id})'})
        
        claimed = get_claimed_amount(bill_id)
        if claimed + amount > bill.get('total_amount', 0):
            remaining = bill.get('total_amount', 0) - claimed
            return jsonify({'code': 1003, 'message': f'认领失败：该账单剩余额度不足（剩余 {remaining:.2f} 元）'})
        
        users = read_json(USERS_FILE)
        user = next((u for u in users if u.get('id') == claimant_id), None)
        if not user:
            return jsonify({'code': 404, 'message': f'用户不存在 (ID: {claimant_id})'})
        
        user_used = get_user_claimed_amount(claimant_id)
        if user_used + amount > user.get('max_commitment', 0):
            remaining = user.get('max_commitment', 0) - user_used
            return jsonify({'code': 1002, 'message': f'认领失败：您的剩余额度不足（剩余 {remaining:.2f} 元）'})
        
        claims = read_json(CLAIMS_FILE)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_claim = {
            'id': get_next_id(claims),
            'bill_id': bill_id,
            'claimant_id': claimant_id,
            'amount': amount,
            'payer_confirmed': False,
            'receiver_confirmed': False,
            'status': 'pending',
            'created_at': now,
            'settled_at': None
        }
        claims.append(new_claim)
        write_json(CLAIMS_FILE, claims)
        
        total_claimed = claimed + amount
        bill_status = 'transferring' if total_claimed >= bill.get('total_amount', 0) else 'claiming'
        
        for b in bills:
            if b.get('id') == bill_id:
                b['status'] = bill_status
                break
        write_json(BILLS_FILE, bills)
        
        return jsonify({
            'code': 0,
            'message': '认领成功',
            'data': {
                'bill_status': bill_status,
                'remaining': bill.get('total_amount', 0) - total_claimed
            }
        })
    except (ValueError, TypeError) as e:
        print(f'❌ [认领-参数错误] {e}')
        return jsonify({'code': 1000, 'message': f'认领参数格式错误: {str(e)}', 'error_detail': '请检查金额和用户ID是否为有效数字'})
    except Exception as e:
        print(f'❌ [认领接口异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'认领服务异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 9. 确认支付接口
# ================================================================
@app.route('/api/claims/<int:claim_id>/confirm-payer', methods=['PUT'])
def confirm_payer(claim_id):
    try:
        claims = read_json(CLAIMS_FILE)
        claim = next((c for c in claims if c.get('id') == claim_id), None)
        if not claim:
            return jsonify({'code': 404, 'message': f'认领记录不存在 (ID: {claim_id})'})
        
        claim['payer_confirmed'] = True
        # 先写盘，确保后续读取的是最新数据
        write_json(CLAIMS_FILE, claims)
        if claim.get('receiver_confirmed'):
            claim['status'] = 'settled'
            claim['settled_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            write_json(CLAIMS_FILE, claims)
            bills = read_json(BILLS_FILE)
            bill = next((b for b in bills if b.get('id') == claim.get('bill_id')), None)
            if bill:
                all_claims = get_claims_by_bill(bill.get('id'))
                if all(c.get('status') == 'settled' for c in all_claims):
                    bill['status'] = 'settled'
                    bill['settled_at'] = claim['settled_at']
                    write_json(BILLS_FILE, bills)
        
        return jsonify({'code': 0, 'message': '已确认转账'})
    except Exception as e:
        print(f'❌ [付款方确认接口异常] claim_id={claim_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'确认转账失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/claims/<int:claim_id>/confirm-receiver', methods=['PUT'])
def confirm_receiver(claim_id):
    try:
        claims = read_json(CLAIMS_FILE)
        claim = next((c for c in claims if c.get('id') == claim_id), None)
        if not claim:
            return jsonify({'code': 404, 'message': f'认领记录不存在 (ID: {claim_id})'})
        
        claim['receiver_confirmed'] = True
        # 先写盘，确保后续读取的是最新数据
        write_json(CLAIMS_FILE, claims)
        if claim.get('payer_confirmed'):
            claim['status'] = 'settled'
            claim['settled_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            write_json(CLAIMS_FILE, claims)
            bills = read_json(BILLS_FILE)
            bill = next((b for b in bills if b.get('id') == claim.get('bill_id')), None)
            if bill:
                all_claims = get_claims_by_bill(bill.get('id'))
                if all(c.get('status') == 'settled' for c in all_claims):
                    bill['status'] = 'settled'
                    bill['settled_at'] = claim['settled_at']
                    write_json(BILLS_FILE, bills)
        
        return jsonify({'code': 0, 'message': '已确认收款'})
    except Exception as e:
        print(f'❌ [收款方确认接口异常] claim_id={claim_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'确认收款失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 9.5 取消认领接口
# ================================================================
@app.route('/api/claims/<int:claim_id>', methods=['DELETE'])
def cancel_claim(claim_id):
    try:
        claims = read_json(CLAIMS_FILE)
        claim = next((c for c in claims if c.get('id') == claim_id), None)
        if not claim:
            return jsonify({'code': 404, 'message': f'认领记录不存在 (ID: {claim_id})'})
        
        # 已确认转账的不能取消
        if claim.get('payer_confirmed'):
            return jsonify({'code': 1004, 'message': '该认领已确认转账，无法取消'})
        if claim.get('receiver_confirmed'):
            return jsonify({'code': 1004, 'message': '该认领已确认收款，无法取消'})
        
        bill_id = claim.get('bill_id')
        
        # 删除该认领
        claims = [c for c in claims if c.get('id') != claim_id]
        write_json(CLAIMS_FILE, claims)
        
        # 重新计算账单状态
        bills = read_json(BILLS_FILE)
        bill = next((b for b in bills if b.get('id') == bill_id), None)
        if bill:
            remaining_claims = [c for c in claims if c.get('bill_id') == bill_id]
            if len(remaining_claims) == 0:
                bill['status'] = 'pending'
            else:
                total_claimed = sum(c.get('amount', 0) for c in remaining_claims if c.get('status') == 'pending')
                bill['status'] = 'transferring' if total_claimed >= bill.get('total_amount', 0) else 'claiming'
            write_json(BILLS_FILE, bills)
        
        return jsonify({'code': 0, 'message': '认领已取消'})
    except Exception as e:
        print(f'❌ [取消认领接口异常] claim_id={claim_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'取消认领失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 10. 结算接口
# ================================================================
@app.route('/api/settlement/<int:user_id>', methods=['GET'])
def get_settlement(user_id):
    try:
        claims = read_json(CLAIMS_FILE)
        bills = read_json(BILLS_FILE)
        
        payable = []
        receivable = []
        
        for c in claims:
            if c.get('status') != 'pending':
                continue
            bill = next((b for b in bills if b.get('id') == c.get('bill_id')), None)
            if not bill:
                continue
            if c.get('claimant_id') == user_id:
                payable.append({
                    'claim_id': c.get('id'),
                    'bill_id': bill.get('id'),
                    'bill_title': bill.get('title'),
                    'receiver_name': get_user_name(bill.get('purchaser_id')),
                    'amount': c.get('amount'),
                    'payer_confirmed': c.get('payer_confirmed', False),
                    'receiver_confirmed': c.get('receiver_confirmed', False)
                })
            if bill.get('purchaser_id') == user_id:
                receivable.append({
                    'claim_id': c.get('id'),
                    'bill_id': bill.get('id'),
                    'bill_title': bill.get('title'),
                    'payer_name': get_user_name(c.get('claimant_id')),
                    'amount': c.get('amount'),
                    'payer_confirmed': c.get('payer_confirmed', False),
                    'receiver_confirmed': c.get('receiver_confirmed', False)
                })
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'payable': payable,
                'receivable': receivable,
                'total_payable': sum(p['amount'] for p in payable),
                'total_receivable': sum(r['amount'] for r in receivable)
            }
        })
    except Exception as e:
        print(f'❌ [结算接口异常] user_id={user_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取结算数据异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

def get_ranking_cleared_at():
    try:
        settings = read_json(SETTINGS_FILE)
        return settings.get('ranking_cleared_at')
    except:
        return None

# 11. 激励榜
# ================================================================
@app.route('/api/ranking', methods=['GET'])
def get_ranking():
    try:
        users = read_json(USERS_FILE)
        bills = read_json(BILLS_FILE)
        cleared_at = get_ranking_cleared_at()
        
        medals = []
        for u in users:
            claims = read_json(CLAIMS_FILE)
            count = len([c for c in claims if c.get('claimant_id') == u.get('id') and c.get('status') == 'settled' and (cleared_at is None or c.get('settled_at', '') > cleared_at)])
            medals.append({'user_id': u.get('id'), 'name': u.get('name'), 'count': count})
        
        medals.sort(key=lambda x: x['count'], reverse=True)
        
        shoppers = []
        for u in users:
            count = len([b for b in bills if b.get('purchaser_id') == u.get('id') and (cleared_at is None or b.get('created_at', '') > cleared_at)])
            shoppers.append({'user_id': u.get('id'), 'name': u.get('name'), 'count': count})
        
        shoppers.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'medals': medals[:5],
                'shoppers': shoppers[:5]
            }
        })
    except Exception as e:
        print(f'❌ [激励榜接口异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取激励榜数据异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 12. 后台管理接口
# ================================================================
@app.route('/api/admin/members', methods=['GET'])
def admin_members():
    try:
        users = read_json(USERS_FILE)
        result = []
        for u in users:
            used = get_user_claimed_amount(u.get('id'))
            result.append({
                'id': u.get('id'),
                'username': u.get('username'),
                'name': u.get('name'),
                'role': u.get('role'),
                'is_admin': u.get('is_admin', False),
                'max_commitment': u.get('max_commitment', 0),
                'used': used,
                'remain': u.get('max_commitment', 0) - used,
                'receivable': get_user_receivable(u.get('id')),
                'payable': get_user_payable(u.get('id'))
            })
        return jsonify({'code': 0, 'message': 'success', 'data': result})
    except Exception as e:
        print(f'❌ [后台-成员列表接口异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取成员列表异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/admin/bills', methods=['GET'])
def admin_bills():
    try:
        bills = read_json(BILLS_FILE)
        result = []
        for b in bills:
            claimed = get_claimed_amount(b.get('id'))
            result.append({
                'id': b.get('id'),
                'title': b.get('title'),
                'total_amount': b.get('total_amount', 0),
                'purchaser_id': b.get('purchaser_id'),
                'purchaser_name': get_user_name(b.get('purchaser_id')),
                'status': b.get('status'),
                'status_text': {'pending': '待认领', 'claiming': '认领中', 'transferring': '待转账', 'settled': '已结清'}.get(b.get('status'), b.get('status')),
                'claimed_amount': claimed,
                'created_at': b.get('created_at', ''),
                'settled_at': b.get('settled_at')
            })
        return jsonify({'code': 0, 'message': 'success', 'data': result})
    except Exception as e:
        print(f'❌ [后台-账单列表接口异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取账单列表异常: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})


@app.route('/api/admin/bills/<int:bill_id>', methods=['PUT'])
def admin_update_bill(bill_id):
    """管理员编辑账单（标题、金额、购买人）"""
    try:
        bills = read_json(BILLS_FILE)
        bill = next((b for b in bills if b.get('id') == bill_id), None)
        if not bill:
            return jsonify({'code': 404, 'message': f'账单不存在 (ID: {bill_id})'})

        data = request.get_json()
        if not data:
            return jsonify({'code': 1000, 'message': '请求数据为空'})

        if 'title' in data and data['title']:
            bill['title'] = data['title']
        if 'total_amount' in data:
            amount = float(data['total_amount'])
            if amount <= 0:
                return jsonify({'code': 1000, 'message': '金额必须大于0'})
            bill['total_amount'] = amount
        if 'purchaser_id' in data:
            uid = int(data['purchaser_id'])
            if not find_user_by_id(uid):
                return jsonify({'code': 1000, 'message': f'用户不存在 (ID: {uid})'})
            bill['purchaser_id'] = uid

        write_json(BILLS_FILE, bills)
        print(f'♻️ [管理员] 已编辑账单 ID={bill_id}')
        return jsonify({'code': 0, 'message': '账单已更新'})
    except Exception as e:
        print(f'❌ [后台-编辑账单异常] bill_id={bill_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'编辑账单失败: {str(e)}'})


@app.route('/api/admin/bills/<int:bill_id>', methods=['DELETE'])
def admin_delete_bill(bill_id):
    """管理员删除指定账单及其所有认领记录"""
    try:
        bills = read_json(BILLS_FILE)
        bill = next((b for b in bills if b.get('id') == bill_id), None)
        if not bill:
            return jsonify({'code': 404, 'message': f'账单不存在 (ID: {bill_id})'})

        # 删除账单
        bills = [b for b in bills if b.get('id') != bill_id]
        write_json(BILLS_FILE, bills)

        # 删除该账单的所有认领记录
        claims = read_json(CLAIMS_FILE)
        claims = [c for c in claims if c.get('bill_id') != bill_id]
        write_json(CLAIMS_FILE, claims)

        print(f'🗑️ [管理员] 已删除账单 ID={bill_id} 及其所有认领')
        return jsonify({'code': 0, 'message': '账单及关联认领已删除'})
    except Exception as e:
        print(f'❌ [后台-删除账单异常] bill_id={bill_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'删除账单失败: {str(e)}'})


@app.route('/api/admin/bills/<int:bill_id>/claims', methods=['GET'])
def admin_bill_claims(bill_id):
    """管理员获取指定账单的所有认领详情"""
    try:
        bills = read_json(BILLS_FILE)
        bill = next((b for b in bills if b.get('id') == bill_id), None)
        if not bill:
            return jsonify({'code': 404, 'message': f'账单不存在 (ID: {bill_id})'})

        claims = get_claims_by_bill(bill_id)
        result = []
        for c in claims:
            result.append({
                'id': c.get('id'),
                'bill_id': c.get('bill_id'),
                'claimant_id': c.get('claimant_id'),
                'claimant_name': get_user_name(c.get('claimant_id')),
                'amount': c.get('amount'),
                'status': c.get('status'),
                'status_text': '已结清' if c.get('status') == 'settled' else '待确认',
                'payer_confirmed': c.get('payer_confirmed', False),
                'receiver_confirmed': c.get('receiver_confirmed', False),
                'created_at': c.get('created_at', '')
            })

        return jsonify({'code': 0, 'message': 'success', 'data': result})
    except Exception as e:
        print(f'❌ [后台-账单认领列表异常] bill_id={bill_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取认领列表失败: {str(e)}'})


@app.route('/api/admin/claims/<int:claim_id>', methods=['PUT'])
def admin_update_claim(claim_id):
    """管理员编辑认领记录（修改认领人和金额）"""
    try:
        claims = read_json(CLAIMS_FILE)
        claim = next((c for c in claims if c.get('id') == claim_id), None)
        if not claim:
            return jsonify({'code': 404, 'message': f'认领记录不存在 (ID: {claim_id})'})

        data = request.get_json()
        if not data:
            return jsonify({'code': 1000, 'message': '请求数据为空'})

        if 'amount' in data:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({'code': 1000, 'message': '金额必须大于0'})
            claim['amount'] = amount
        if 'claimant_id' in data:
            uid = int(data['claimant_id'])
            if not find_user_by_id(uid):
                return jsonify({'code': 1000, 'message': f'用户不存在 (ID: {uid})'})
            claim['claimant_id'] = uid

        write_json(CLAIMS_FILE, claims)
        print(f'♻️ [管理员] 已编辑认领 ID={claim_id}')
        return jsonify({'code': 0, 'message': '认领记录已更新'})
    except Exception as e:
        print(f'❌ [后台-编辑认领异常] claim_id={claim_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'编辑认领失败: {str(e)}'})


@app.route('/api/admin/claims/<int:claim_id>', methods=['DELETE'])
def admin_delete_claim(claim_id):
    """管理员删除指定认领记录"""
    try:
        claims = read_json(CLAIMS_FILE)
        claim = next((c for c in claims if c.get('id') == claim_id), None)
        if not claim:
            return jsonify({'code': 404, 'message': f'认领记录不存在 (ID: {claim_id})'})

        claims = [c for c in claims if c.get('id') != claim_id]
        write_json(CLAIMS_FILE, claims)

        # 如果账单下没有其他认领了，将账单状态重置为 pending
        bill_id = claim.get('bill_id')
        bills = read_json(BILLS_FILE)
        remaining_claims = get_claims_by_bill(bill_id)
        if remaining_claims:
            total_claimed = sum(c.get('amount', 0) for c in remaining_claims)
            bill = next((b for b in bills if b.get('id') == bill_id), None)
            if bill:
                if total_claimed >= bill.get('total_amount', 0):
                    bill['status'] = 'transferring'
                else:
                    bill['status'] = 'claiming'
                write_json(BILLS_FILE, bills)
        else:
            bills = read_json(BILLS_FILE)
            bill = next((b for b in bills if b.get('id') == bill_id), None)
            if bill:
                bill['status'] = 'pending'
                write_json(BILLS_FILE, bills)

        print(f'🗑️ [管理员] 已删除认领 ID={claim_id}')
        return jsonify({'code': 0, 'message': '认领记录已删除'})
    except Exception as e:
        print(f'❌ [后台-删除认领异常] claim_id={claim_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'删除认领失败: {str(e)}'})


@app.route('/api/admin/claims/<int:claim_id>/force-settle', methods=['PUT'])
def admin_force_settle(claim_id):
    try:
        claims = read_json(CLAIMS_FILE)
        claim = next((c for c in claims if c.get('id') == claim_id), None)
        if not claim:
            return jsonify({'code': 404, 'message': f'认领记录不存在 (ID: {claim_id})'})
        
        claim['status'] = 'settled'
        claim['payer_confirmed'] = True
        claim['receiver_confirmed'] = True
        claim['settled_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        write_json(CLAIMS_FILE, claims)
        
        bills = read_json(BILLS_FILE)
        bill = next((b for b in bills if b.get('id') == claim.get('bill_id')), None)
        if bill:
            all_claims = get_claims_by_bill(bill.get('id'))
            if all(c.get('status') == 'settled' for c in all_claims):
                bill['status'] = 'settled'
                bill['settled_at'] = claim['settled_at']
                write_json(BILLS_FILE, bills)
        
        return jsonify({'code': 0, 'message': '强制结清成功'})
    except Exception as e:
        print(f'❌ [强制结清接口异常] claim_id={claim_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'强制结清失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/admin/users/<int:user_id>/commitment', methods=['PUT'])
def admin_update_commitment(user_id):
    try:
        data = request.get_json()
        if not data or 'max_commitment' not in data:
            return jsonify({'code': 1000, 'message': '请求数据错误', 'error_detail': '请提供 max_commitment 字段'})
        
        users = read_json(USERS_FILE)
        user = next((u for u in users if u.get('id') == user_id), None)
        if not user:
            return jsonify({'code': 404, 'message': f'用户不存在 (ID: {user_id})'})
        
        user['max_commitment'] = float(data.get('max_commitment', 0))
        write_json(USERS_FILE, users)
        return jsonify({'code': 0, 'message': '修改成功'})
    except (ValueError, TypeError) as e:
        return jsonify({'code': 1000, 'message': f'额度参数格式错误: {str(e)}', 'error_detail': '请确保额度为有效数字'})
    except Exception as e:
        print(f'❌ [修改额度接口异常] user_id={user_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'修改额度失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ---- 普通用户自行修改承诺上限（仅可调高，不清空已认领） ----
@app.route('/api/user/commitment', methods=['PUT'])
def user_update_commitment():
    try:
        data = request.get_json()
        if not data or 'max_commitment' not in data or 'user_id' not in data:
            return jsonify({'code': 1000, 'message': '请求数据错误', 'error_detail': '请提供 user_id 和 max_commitment 字段'})

        user_id = int(data['user_id'])
        new_limit = float(data['max_commitment'])

        users = read_json(USERS_FILE)
        user = next((u for u in users if u.get('id') == user_id), None)
        if not user:
            return jsonify({'code': 404, 'message': f'用户不存在 (ID: {user_id})'})

        used = get_user_claimed_amount(user_id)
        if new_limit < used:
            return jsonify({
                'code': 1002,
                'message': f'修改失败：新上限（{new_limit:.0f} 元）不能低于已认领金额（{used:.0f} 元）',
                'error_detail': f'当前已认领 {used:.0f} 元，上限至少需设为 {used:.0f} 元'
            })

        old_limit = user.get('max_commitment', 0)
        user['max_commitment'] = new_limit
        write_json(USERS_FILE, users)

        print(f'📝 [修改承诺上限] 用户 {user.get("name")}(ID={user_id}) 上限 {old_limit:.0f} → {new_limit:.0f}')

        return jsonify({
            'code': 0,
            'message': f'承诺上限已从 {old_limit:.0f} 元调整为 {new_limit:.0f} 元'
        })

    except (ValueError, TypeError) as e:
        return jsonify({'code': 1000, 'message': f'额度参数格式错误: {str(e)}', 'error_detail': '请确保额度为有效数字'})
    except Exception as e:
        print(f'❌ [用户修改承诺上限异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'修改承诺上限失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 13. 账号管理接口（图形化界面用）
# ================================================================
@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    try:
        users = read_json(USERS_FILE)
        result = []
        for u in users:
            result.append({
                'id': u.get('id'),
                'username': u.get('username'),
                'name': u.get('name'),
                'role': u.get('role'),
                'is_admin': u.get('is_admin', False),
                'max_commitment': u.get('max_commitment', 0)
            })
        return jsonify({'code': 0, 'message': 'success', 'data': result})
    except Exception as e:
        print(f'❌ [获取用户列表异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'获取用户列表失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/admin/users', methods=['POST'])
def admin_create_user():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 1000, 'message': '请求数据为空', 'error_detail': '请提供用户信息'})
        if not data.get('username'):
            return jsonify({'code': 1000, 'message': '用户名不能为空', 'error_detail': '请填写账号'})
        if not data.get('name'):
            return jsonify({'code': 1000, 'message': '姓名不能为空', 'error_detail': '请填写姓名'})
        
        users = read_json(USERS_FILE)
        
        if find_user_by_username(data.get('username')):
            return jsonify({'code': 1004, 'message': '用户名已存在', 'error_detail': f'账号 "{data.get("username")}" 已被占用'})
        
        new_user = {
            'id': get_next_id(users),
            'username': data.get('username', ''),
            'password': data.get('password', '123456'),
            'name': data.get('name', ''),
            'role': data.get('role', 'son'),
            'is_admin': data.get('is_admin', False),
            'max_commitment': float(data.get('max_commitment', 100))
        }
        users.append(new_user)
        write_json(USERS_FILE, users)
        return jsonify({'code': 0, 'message': '用户创建成功', 'data': new_user})
    except (ValueError, TypeError) as e:
        return jsonify({'code': 1000, 'message': f'参数格式错误: {str(e)}', 'error_detail': '请检查输入数据格式'})
    except Exception as e:
        print(f'❌ [创建用户异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'创建用户失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def admin_update_user(user_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 1000, 'message': '请求数据为空', 'error_detail': '请提供要修改的信息'})
        
        users = read_json(USERS_FILE)
        user = next((u for u in users if u.get('id') == user_id), None)
        if not user:
            return jsonify({'code': 404, 'message': f'用户不存在 (ID: {user_id})'})
        
        if 'name' in data:
            user['name'] = data['name']
        if 'username' in data and data['username']:
            # 检查新用户名是否被占用（排除自己）
            existing = next((u for u in users if u.get('username') == data['username'] and u.get('id') != user_id), None)
            if existing:
                return jsonify({'code': 1004, 'message': '用户名已存在', 'error_detail': f'账号 "{data["username"]}" 已被占用'})
            user['username'] = data['username']
        if 'role' in data:
            user['role'] = data['role']
        if 'is_admin' in data:
            user['is_admin'] = data['is_admin']
        if 'max_commitment' in data:
            user['max_commitment'] = float(data['max_commitment'])
        if 'password' in data and data['password']:
            user['password'] = data['password']
        
        write_json(USERS_FILE, users)
        return jsonify({'code': 0, 'message': '修改成功'})
    except (ValueError, TypeError) as e:
        return jsonify({'code': 1000, 'message': f'参数格式错误: {str(e)}', 'error_detail': '请检查输入数据格式'})
    except Exception as e:
        print(f'❌ [更新用户异常] user_id={user_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'更新用户失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    try:
        users = read_json(USERS_FILE)
        users = [u for u in users if u.get('id') != user_id]
        write_json(USERS_FILE, users)
        return jsonify({'code': 0, 'message': '删除成功'})
    except Exception as e:
        print(f'❌ [删除用户异常] user_id={user_id}, {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'删除用户失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 13.5 管理员首次设置 & 备份 & 恢复出厂
# ================================================================

@app.route('/api/admin/check-setup', methods=['GET'])
def admin_check_setup():
    """检查管理员是否已完成首次设置"""
    try:
        configured = is_admin_configured()
        return jsonify({'code': 0, 'message': 'success', 'data': {'configured': configured}})
    except Exception as e:
        print(f'❌ [检查设置异常] {e}')
        return jsonify({'code': 5000, 'message': f'检查失败: {str(e)}'})

@app.route('/api/admin/setup', methods=['POST'])
def admin_setup():
    """首次设置管理员账号密码（仅一次）"""
    try:
        if is_admin_configured():
            return jsonify({'code': 1006, 'message': '管理员已设置，请直接登录'})
        
        data = request.get_json()
        if not data:
            return jsonify({'code': 1000, 'message': '请求数据为空'})
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        confirm = data.get('confirm', '').strip()

        if not username or not password:
            return jsonify({'code': 1000, 'message': '账号和密码不能为空'})
        if len(password) < 4:
            return jsonify({'code': 1000, 'message': '密码长度至少4位'})
        if password != confirm:
            return jsonify({'code': 1000, 'message': '两次密码输入不一致'})

        settings = read_settings()
        settings['admin_username'] = username
        settings['admin_password'] = password
        settings['admin_setup_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        write_settings(settings)

        print(f'🔐 [管理员] 首次设置完成: {username}')
        return jsonify({'code': 0, 'message': '管理员设置成功'})
    except Exception as e:
        print(f'❌ [管理员设置异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'设置失败: {str(e)}'})

@app.route('/api/admin/backup', methods=['POST'])
def admin_create_backup():
    """创建全量数据备份"""
    try:
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_subdir = os.path.join(BACKUP_DIR, f'backup_{ts}')
        os.makedirs(backup_subdir, exist_ok=True)

        files_to_backup = {
            'users.json': USERS_FILE,
            'bills.json': BILLS_FILE,
            'claims.json': CLAIMS_FILE,
            'settings.json': SETTINGS_FILE
        }

        manifest = {}
        for name, src in files_to_backup.items():
            if os.path.exists(src):
                dst = os.path.join(backup_subdir, name)
                with open(src, 'r', encoding='utf-8') as f_in:
                    data = json.load(f_in)
                with open(dst, 'w', encoding='utf-8') as f_out:
                    json.dump(data, f_out, ensure_ascii=False, indent=2)
                manifest[name] = 'ok'
                print(f'💾 [备份] {name} 已备份')
            else:
                manifest[name] = 'skipped'

        # 写入备份清单
        info = {
            'created_at': ts,
            'files': manifest
        }
        with open(os.path.join(backup_subdir, 'manifest.json'), 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        print(f'💾 [备份完成] {backup_subdir}')
        return jsonify({'code': 0, 'message': '备份成功', 'data': {'path': f'backup_{ts}', 'files': manifest}})
    except Exception as e:
        print(f'❌ [备份异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'备份失败: {str(e)}'})

@app.route('/api/admin/backups', methods=['GET'])
def admin_list_backups():
    """列出所有备份"""
    try:
        if not os.path.exists(BACKUP_DIR):
            return jsonify({'code': 0, 'message': 'success', 'data': []})
        
        backups = []
        for entry in sorted(os.listdir(BACKUP_DIR), reverse=True):
            entry_path = os.path.join(BACKUP_DIR, entry)
            if os.path.isdir(entry_path) and entry.startswith('backup_'):
                manifest_path = os.path.join(entry_path, 'manifest.json')
                manifest = {}
                if os.path.exists(manifest_path):
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                backups.append({
                    'id': entry,
                    'name': entry,
                    'created_at': manifest.get('created_at', entry.replace('backup_', '')),
                    'files': manifest.get('files', {})
                })

        return jsonify({'code': 0, 'message': 'success', 'data': backups})
    except Exception as e:
        print(f'❌ [列出备份异常] {e}')
        return jsonify({'code': 5000, 'message': f'列出备份失败: {str(e)}'})

@app.route('/api/admin/backup/restore/<backup_id>', methods=['POST'])
def admin_restore_backup(backup_id):
    """从指定备份恢复数据"""
    try:
        restore_path = os.path.join(BACKUP_DIR, backup_id)
        if not os.path.isdir(restore_path):
            return jsonify({'code': 404, 'message': f'备份不存在: {backup_id}'})

        files_to_restore = {
            'users.json': USERS_FILE,
            'bills.json': BILLS_FILE,
            'claims.json': CLAIMS_FILE,
            # 不恢复 settings.json，避免覆盖当前管理员密码
        }

        restored = []
        for name, dst in files_to_restore.items():
            src = os.path.join(restore_path, name)
            if os.path.exists(src):
                with open(src, 'r', encoding='utf-8') as f_in:
                    data = json.load(f_in)
                with open(dst, 'w', encoding='utf-8') as f_out:
                    json.dump(data, f_out, ensure_ascii=False, indent=2)
                restored.append(name)
                print(f'♻️ [恢复] {name} 已恢复')

        print(f'♻️ [恢复完成] 从 {backup_id}')
        return jsonify({'code': 0, 'message': '恢复成功', 'data': {'restored': restored}})
    except Exception as e:
        print(f'❌ [恢复备份异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'恢复失败: {str(e)}'})

@app.route('/api/admin/backup/delete/<backup_id>', methods=['DELETE'])
def admin_delete_backup(backup_id):
    """刪除指定备份"""
    try:
        backup_path = os.path.join(BACKUP_DIR, backup_id)
        if not os.path.isdir(backup_path):
            return jsonify({'code': 404, 'message': f'备份不存在: {backup_id}'})

        shutil.rmtree(backup_path)
        print(f'🗑️ [删除备份] {backup_id} 已删除')
        return jsonify({'code': 0, 'message': '备份已删除'})
    except Exception as e:
        print(f'❌ [删除备份异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'删除备份失败: {str(e)}'})

@app.route('/api/admin/factory-reset', methods=['POST'])
def admin_factory_reset():
    """恢复出厂设置：清空所有数据并重置管理员"""
    try:
        # 清空所有数据文件
        write_json(USERS_FILE, [])
        write_json(BILLS_FILE, [])
        write_json(CLAIMS_FILE, [])
        write_json(SETTINGS_FILE, {})
        print('🗑️ [管理员] 已执行恢复出厂设置')
        return jsonify({'code': 0, 'message': '已恢复出厂设置，所有数据已清除，管理员账号需要重新设置'})
    except Exception as e:
        print(f'❌ [恢复出厂设置异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'恢复出厂设置失败: {str(e)}'})

@app.route('/api/admin/reset', methods=['POST'])
def admin_reset_all():
    try:
        # 清空所有账单和认领数据
        write_json(BILLS_FILE, [])
        write_json(CLAIMS_FILE, [])
        print('🗑️ [管理员] 已清空全部账单和认领数据')
        return jsonify({'code': 0, 'message': '已清空全部账单和认领数据'})
    except Exception as e:
        print(f'❌ [重置数据异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'重置失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

@app.route('/api/admin/clear-ranking', methods=['POST'])
def admin_clear_ranking():
    try:
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        settings = read_json(SETTINGS_FILE) if os.path.exists(SETTINGS_FILE) else {}
        settings['ranking_cleared_at'] = now
        write_json(SETTINGS_FILE, settings)
        print(f'🗑️ [管理员] 已清除排行数据 ({now})')
        return jsonify({'code': 0, 'message': '已清除排行数据，排行统计已归零'})
    except Exception as e:
        print(f'❌ [清除排行异常] {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'code': 5000, 'message': f'清除排行失败: {str(e)}', 'error_detail': '请联系管理员查看后端日志'})

# ================================================================
# 14. 提供前端页面
# ================================================================
@app.route('/')
def serve_index():
    try:
        return send_from_directory(FRONTEND_DIR, 'index.html')
    except FileNotFoundError:
        return jsonify({'code': 5004, 'message': '前端首页文件不存在', 'error_detail': f'请确保 {FRONTEND_DIR}/index.html 存在'}), 500
    except Exception as e:
        print(f'❌ [前端页面服务异常] {e}')
        return jsonify({'code': 5000, 'message': f'无法加载前端页面: {str(e)}', 'error_detail': '请检查前端目录配置'}), 500

@app.route('/admin/accounts')
def serve_account_manager():
    try:
        return send_from_directory(BASE_DIR, 'account-manager.html')
    except FileNotFoundError:
        return jsonify({'code': 5004, 'message': '账号管理页面不存在', 'error_detail': f'请确保 {BASE_DIR}/account-manager.html 存在'}), 500
    except Exception as e:
        print(f'❌ [账号管理页面服务异常] {e}')
        return jsonify({'code': 5000, 'message': f'无法加载账号管理页面: {str(e)}', 'error_detail': '请检查文件路径'}), 500

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(FRONTEND_DIR, path)
    except FileNotFoundError:
        return jsonify({'code': 5004, 'message': f'静态文件不存在: {path}', 'error_detail': f'请确保 {FRONTEND_DIR}/{path} 存在'}), 404
    except Exception as e:
        print(f'❌ [静态文件服务异常] path={path}, {e}')
        return jsonify({'code': 5000, 'message': f'无法加载静态文件: {str(e)}'}), 500

# ================================================================
# 14.5 服务控制台 — 查看服务器日志与运行状态
# ================================================================

@app.route('/api/admin/server-logs')
def admin_server_logs():
    """返回服务器日志文件内容（最近100行）"""
    try:
        if not os.path.exists(LOG_FILE):
            return jsonify({'code': 0, 'data': {'lines': [], 'total': 0}})
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        # 返回最近 200 行
        recent = all_lines[-200:]
        return jsonify({
            'code': 0,
            'data': {
                'lines': recent,
                'total': len(all_lines),
                'showing': len(recent)
            }
        })
    except Exception as e:
        print(f'❌ [日志读取异常] {e}')
        return jsonify({'code': 5000, 'message': f'读取日志失败: {str(e)}'})

@app.route('/api/admin/server-status')
def admin_server_status():
    """返回服务器运行状态信息"""
    try:
        import platform
        import psutil
        process = psutil.Process()
        mem = process.memory_info()
        uptime_seconds = int((datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds())
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return jsonify({
            'code': 0,
            'data': {
                'pid': process.pid,
                'uptime': f'{hours}时{minutes}分{seconds}秒',
                'memory_mb': f'{mem.rss / 1024 / 1024:.1f}',
                'cpu_percent': process.cpu_percent(interval=0.1),
                'python_version': sys.version,
                'platform': platform.platform(),
                'host': 'http://localhost:3000',
                'log_file': LOG_FILE
            }
        })
    except ImportError:
        # psutil 可能未安装，返回基本信息
        return jsonify({
            'code': 0,
            'data': {
                'pid': os.getpid(),
                'uptime': '未知（请安装 psutil 获取详情）',
                'python_version': sys.version,
                'host': 'http://localhost:3000'
            }
        })
    except Exception as e:
        print(f'❌ [状态查询异常] {e}')
        return jsonify({'code': 5000, 'message': f'获取状态失败: {str(e)}'})

@app.route('/admin/console')
def serve_server_console():
    """提供服务控制台页面"""
    try:
        return send_from_directory(BASE_DIR, 'server-console.html')
    except FileNotFoundError:
        return jsonify({'code': 5004, 'message': '控制台页面不存在'}), 500
    except Exception as e:
        print(f'❌ [控制台页面服务异常] {e}')
        return jsonify({'code': 5000, 'message': f'无法加载控制台页面: {str(e)}'}), 500

# ================================================================
# 15. 启动服务
# ================================================================
if __name__ == '__main__':
    print('=' * 50)
    print('🏠 家庭报销管理系统 后端服务')
    print('=' * 50)
    print(f'📂 后端目录: {BASE_DIR}')
    print(f'📂 前端目录: {FRONTEND_DIR}')
    print(f'📂 用户数据: {USERS_FILE}')
    print(f'📂 账单数据: {BILLS_FILE}')
    print(f'📂 认领数据: {CLAIMS_FILE}')
    print(f'📂 配置数据: {SETTINGS_FILE}')
    print(f'📂 备份目录: {BACKUP_DIR}')
    print(f'🌐 访问地址: http://localhost:3000')
    print(f'🔗 账号管理: http://localhost:3000/admin/accounts')
    print(f'👤 管理员: 首次访问 /admin/accounts 时设置')
    print(f'📋 家庭成员账号见: {USERS_FILE}')
    print('=' * 50)
    
    # 启动前检查
    if not os.path.exists(FRONTEND_DIR):
        print(f'⚠️  警告: 前端目录不存在! ({FRONTEND_DIR})')
        print('⚠️  网站将无法正确加载前端页面，请检查项目结构')
        print('=' * 50)
    
    frontend_file = os.path.join(FRONTEND_DIR, 'index.html')
    if not os.path.exists(frontend_file):
        print(f'⚠️  警告: 前端文件不存在! ({frontend_file})')
        print('⚠️  访问根路径时可能返回404错误')
        print('=' * 50)
    
    print('🚀 服务启动中...')
    print('按 Ctrl+C 停止服务')
    print('')
    app.run(host='0.0.0.0', port=3000, debug=False)