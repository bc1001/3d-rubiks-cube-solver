import sqlite3
from flask import Flask, render_template, request, jsonify
import kociemba

app = Flask(__name__)
DB_FILE = 'rubiks_history.db'

# ==================== 数据库初始化 ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            cube_state TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 启动时初始化数据库
init_db()

@app.route('/')
def index():
    # 渲染 templates/index.html 页面
    return render_template('index.html')

# ==================== 后端 API ====================

@app.route('/api/solve', methods=['POST'])
def solve_cube():
    data = request.json
    cube_state = data.get('state', '')
    is_manual = data.get('is_manual', True)
    
    user_ip = request.remote_addr

    if is_manual:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT cube_state FROM history WHERE ip = ? ORDER BY id DESC LIMIT 1", (user_ip,))
        last_row = cursor.fetchone()
        
        if not last_row or last_row[0] != cube_state:
            cursor.execute("INSERT INTO history (ip, cube_state) VALUES (?, ?)", (user_ip, cube_state))
            conn.commit()
        conn.close()

    try:
        solution = kociemba.solve(cube_state)
        moves = solution.split()
        return jsonify({'status': 'success', 'solution': solution, 'moves': moves})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/history', methods=['GET'])
def get_history():
    user_ip = request.remote_addr
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cube_state, created_at FROM history WHERE ip = ? ORDER BY id DESC LIMIT 15", (user_ip,))
    rows = cursor.fetchall()
    conn.close()

    history_list = [{'id': r[0], 'state': r[1], 'created_at': r[2]} for r in rows]
    return jsonify({'status': 'success', 'history': history_list})

@app.route('/api/history/delete', methods=['POST'])
def delete_history_item():
    data = request.json
    item_id = data.get('id')
    user_ip = request.remote_addr

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE id = ? AND ip = ?", (item_id, user_ip))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    user_ip = request.remote_addr

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE ip = ?", (user_ip,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    print("--------------------------------------------------")
    print("🚀 代码分离版 3D 魔方求解器启动成功！")
    print("👉 请在浏览器访问: http://127.0.0.1:5000")
    print("--------------------------------------------------")
    app.run(host='0.0.0.0', debug=True, port=5000)