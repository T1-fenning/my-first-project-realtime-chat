from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# 初始化 Flask 與擴充套件
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here' # 實務上應使用環境變數
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)

# ==========================================
# 1. 資料庫模型設計 (ORM 架構)
# ==========================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    is_online = db.Column(db.Boolean, default=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(50), nullable=False)
    sender = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================
# 2. 靜態網頁路由
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# 3. WebSocket 事件監聽器 (全雙工通訊)
# ==========================================
@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    
    # 確保使用者存在於資料庫並更新狀態
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, is_online=True)
        db.session.add(user)
    else:
        user.is_online = True
    db.session.commit()

    # 撈取歷史訊息並傳送給該名剛加入的用戶
    history = Message.query.filter_by(room=room).order_by(Message.timestamp.asc()).all()
    history_data = [{'sender': m.sender, 'content': m.content} for m in history]
    emit('load_history', history_data)

    # 廣播給房間內的其他人
    emit('status_update', {'msg': f'{username} 已進入聊天室。'}, room=room)

@socketio.on('send_message')
def handle_message(data):
    username = data['username']
    room = data['room']
    content = data['message']

    # 將訊息持久化儲存至資料庫
    new_msg = Message(room=room, sender=username, content=content)
    db.session.add(new_msg)
    db.session.commit()

    # 即時廣播給同一個房間的所有人
    emit('receive_message', {'sender': username, 'content': content}, room=room)

@socketio.on('disconnect')
def on_disconnect():
    # 這裡實務上會透過 session 判斷是誰斷線，為保持 Vibe Coding 雛型先留空
    print('Client disconnected')

# ==========================================
# 啟動伺服器與初始化資料庫
# ==========================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # 自動建立 SQLite 資料表
    # 使用 socketio.run 取代 app.run 以支援 WebSocket
    socketio.run(app, debug=True, port=5000)