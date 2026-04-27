from flask import Flask, render_template, request
from flask_socketio import SocketIO
import random
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'avalon_secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

GAME_CONFIG = {
    5: {'goods': 3, 'evils': 2, 'missions': [2, 3, 2, 3, 3]},
    6: {'goods': 4, 'evils': 2, 'missions': [2, 3, 4, 3, 4]},
    7: {'goods': 4, 'evils': 3, 'missions': [2, 3, 3, 4, 4]},
    8: {'goods': 5, 'evils': 3, 'missions': [3, 4, 4, 5, 5]},
    9: {'goods': 6, 'evils': 3, 'missions': [3, 4, 4, 5, 5]},
    10: {'goods': 6, 'evils': 4, 'missions': [3, 4, 4, 5, 5]}
}

room = {
    'players': [],
    'state': 'waiting',
    'mission_sizes': [2, 3, 2, 3, 3],
    'current_mission': 0,
    'leader_index': 0,
    'failed_votes': 0,
    'results': [],
    'proposed_team': [],
    'team_votes': {},
    'mission_votes': [],
    'logs': []
}

def log(msg, color="inherit"):
    colored_msg = f"<span style='color:{color}'>{msg}</span>"
    room['logs'].append(colored_msg)
    socketio.emit('game_log', {'msg': colored_msg})
    print(f"[LOG] {msg}")

def broadcast_state():
    data = {
        'state': room['state'],
        'current_mission': room['current_mission'] + 1 if room['current_mission'] < 5 else 5,
        'req_players': room['mission_sizes'][room['current_mission']] if room['current_mission'] < 5 else 0,
        'leader': room['players'][room['leader_index']]['name'] if room['players'] else '无',
        'failed_votes': room['failed_votes'],
        'results': room['results'],
        'logs': room['logs'][-7:]
    }
    socketio.emit('state_update', data)

@app.route('/')
def index():
    return render_template('room.html')

@socketio.on('join')
def on_join(data):
    name = data['name']
    sid = request.sid
    if any(p['name'] == name for p in room['players']):
        socketio.emit('server_error', {'msg': '名字已被占用，换一个吧！'}, to=sid)
        return
    if room['state'] != 'waiting':
        socketio.emit('server_error', {'msg': '游戏已经开始了，等下一局吧！'}, to=sid)
        return

    room['players'].append({'sid': sid, 'name': name, 'role': None, 'is_good': None, 'is_bot': False})
    socketio.emit('update_players', {'players': [p['name'] for p in room['players']], 'count': len(room['players'])})

@socketio.on('start_game')
def on_start_game():
    if room['state'] != 'waiting': return
    if len(room['players']) > 10:
        socketio.emit('server_error', {'msg': '最多只能支持10人局！'}, to=request.sid)
        return

    bot_names = ['🤖 AI-高文', '🤖 AI-兰斯洛特', '🤖 AI-加拉哈德', '🤖 AI-鲍斯', '🤖 AI-崔斯坦', '🤖 AI-杰兰特']
    bot_counter = 0
    # 至少填满5人局
    while len(room['players']) < 5:
        room['players'].append({
            'sid': f'bot_{bot_counter}', 
            'name': bot_names[bot_counter], 
            'role': None, 
            'is_good': None, 
            'is_bot': True
        })
        bot_counter += 1

    num_players = len(room['players'])
    room['mission_sizes'] = GAME_CONFIG[num_players]['missions']

    room['state'] = 'playing'
    room['current_mission'] = 0
    room['leader_index'] = random.randint(0, num_players - 1)
    room['failed_votes'] = 0
    room['results'] = []
    room['logs'] = []
    
    cfg = GAME_CONFIG[num_players]
    roles = ["Merlin", "Percival", "Assassin", "Morgana"]
    roles += ["Loyal Servant"] * (cfg['goods'] - 2)
    roles += ["Minion of Mordred"] * (cfg['evils'] - 2)
    random.shuffle(roles)

    ROLE_INFO = {
        "Merlin": {
            "display": "Merlin (梅林)", 
            "desc": "【好人阵营】你知道除了莫德雷德和其爪牙以外谁是坏人。请暗中引导好人，绝对不能被刺客发现！"
        },
        "Percival": {
            "display": "Percival (派西维尔)", 
            "desc": "【好人阵营】雷达范围内会同时显示梅林和莫甘娜，但你分不清谁是谁。找出真梅林并保护他！"
        },
        "Loyal Servant": {
            "display": "Loyal Servant (忠臣)", 
            "desc": "【好人阵营】没有任何视野情报的闭眼玩家。请依靠逻辑分析，努力把好人投上车！"
        },
        "Assassin": {
            "display": "Assassin (刺客)", 
            "desc": "【坏人阵营】与坏人队友互相认识。若好人赢下3次任务，你将在最后时刻开火暗杀梅林，刺对直接翻盘！"
        },
        "Morgana": {
            "display": "Morgana (莫甘娜)", 
            "desc": "【坏人阵营】与坏人队友互相认识。你会在派西维尔的眼中伪装为梅林，极力迷惑他吧！"
        },
        "Minion of Mordred": {
            "display": "Minion (爪牙)",
            "desc": "【坏人阵营】与坏人队友互相认识。配合队友破坏任务并找出梅林吧！"
        }
    }
    
    for i, p in enumerate(room['players']):
        p['role'] = roles[i]
        p['is_good'] = p['role'] in ["Merlin", "Percival", "Loyal Servant"]

    for p in room['players']:
        if not p['is_bot']:
            vision_msg = ""
            if p['role'] == 'Merlin':
                evils = [f"<span style='color:#e74c3c; font-weight:bold;'>{x['name']}</span>" for x in room['players'] if not x['is_good']]
                vision_msg = f"😈 坏人们是：{', '.join(evils)}"
            elif p['role'] == 'Percival':
                mMs = [f"<span style='color:#f1c40f; font-weight:bold;'>{x['name']}</span>" for x in room['players'] if x['role'] in ['Merlin', 'Morgana']]
                random.shuffle(mMs)
                vision_msg = f"🔮 这两名玩家中有一位是梅林，一位是莫甘娜：{', '.join(mMs)}"
            elif not p['is_good']:
                evils = [f"<span style='color:#e74c3c; font-weight:bold;'>{x['name']}</span>" for x in room['players'] if not x['is_good'] and x['name'] != p['name']]
                if evils:
                    vision_msg = f"😈 你的坏人队友是：{', '.join(evils)}"
                else:
                    vision_msg = "😈 目前好像只有你一个坏人哦..."

            socketio.emit('receive_role', {
                'role': ROLE_INFO[p['role']]['display'], 
                'desc': ROLE_INFO[p['role']]['desc'],
                'is_good': p['is_good'],
                'vision': vision_msg
            }, to=p['sid'])

    log(f"🌟 {num_players}人局游戏正式开始！全员身份下发完毕，雷达已启动。", "#f1c40f")
    start_building_phase()

def start_building_phase():
    room['state'] = 'building'
    room['proposed_team'] = []
    room['team_votes'] = {}
    broadcast_state()
    
    leader = room['players'][room['leader_index']]
    req_count = room['mission_sizes'][room['current_mission']]
    log(f"👑 第 {room['current_mission'] + 1} 轮轮到 【{leader['name']}】 当队长，需挑选 {req_count} 人执行任务。", "#3498db")
    
    if leader['is_bot']:
        others = [p['name'] for p in room['players'] if p['name'] != leader['name']]
        bot_team = [leader['name']] + random.sample(others, req_count - 1)
        socketio.start_background_task(bot_submit_team, bot_team)
    else:
        players_list = [p['name'] for p in room['players']]
        socketio.emit('request_propose', {'players': players_list, 'req_count': req_count}, to=leader['sid'])

def bot_submit_team(team):
    time.sleep(2)
    handle_submit_team({'team': team})

@socketio.on('submit_team')
def on_submit_team(data):
    handle_submit_team(data)

def handle_submit_team(data):
    room['proposed_team'] = data['team']
    team_str = f"<span style='color:#f39c12; font-weight:bold;'>{', '.join(room['proposed_team'])}</span>"
    log(f"📋 队长提议了以下队伍出发：{team_str}", "#ecf0f1")
    room['state'] = 'voting'
    broadcast_state()

    for p in room['players']:
        if not p['is_bot']:
            socketio.emit('request_team_vote', {'team': room['proposed_team']}, to=p['sid'])
        else:
            is_approve = p['is_good'] or random.choice([True, False])
            socketio.start_background_task(bot_submit_team_vote, p['name'], is_approve)

def bot_submit_team_vote(name, approve):
    time.sleep(random.uniform(1, 3))
    handle_team_vote(name, approve)

@socketio.on('submit_team_vote')
def on_submit_team_vote(data):
    name = next(p['name'] for p in room['players'] if p['sid'] == request.sid)
    handle_team_vote(name, data['approve'])

def handle_team_vote(name, approve):
    if name in room['team_votes']: return
    room['team_votes'][name] = approve

    num_players = len(room['players'])

    if len(room['team_votes']) == num_players:
        approves = sum(1 for v in room['team_votes'].values() if v)
        vote_details = ", ".join([f"{k}:{ '✅' if v else '❌'}" for k, v in room['team_votes'].items()])
        is_approved = approves > num_players / 2
        color = "#2ecc71" if is_approved else "#e74c3c"
        log(f"📊 发车公投结果：{approves} 赞成 / {num_players-approves} 反对。详情: {vote_details}", color)

        if is_approved:
            log("🎉 发车位公投【通过】！小队正在前往任务地点...", "#2ecc71")
            room['failed_votes'] = 0
            start_mission_phase()
        else:
            room['failed_votes'] += 1
            log(f"⚠️ 发车位公投【失败】！(连续死车 {room['failed_votes']}/5)", "#e67e22")
            if room['failed_votes'] >= 5:
                game_over(False, "坏人直接胜利：连续5次死车让系统流局罢工！")
            else:
                room['leader_index'] = (room['leader_index'] + 1) % num_players
                start_building_phase()

def start_mission_phase():
    room['state'] = 'mission'
    room['mission_votes'] = []
    broadcast_state()
    
    for member_name in room['proposed_team']:
        p = next(p for p in room['players'] if p['name'] == member_name)
        if p['is_bot']:
            success = p['is_good']
            socketio.start_background_task(bot_submit_mission_vote, success)
        else:
            socketio.emit('request_mission_vote', {'is_good': p['is_good']}, to=p['sid'])

def bot_submit_mission_vote(success):
    time.sleep(random.uniform(2, 4))
    handle_mission_vote(success)

@socketio.on('submit_mission_vote')
def on_submit_mission_vote(data):
    handle_mission_vote(data['success'])

def handle_mission_vote(success):
    room['mission_votes'].append(success)
    if len(room['mission_votes']) == len(room['proposed_team']):
        fails = room['mission_votes'].count(False)
        num_players = len(room['players'])
        # 阿瓦隆7人及以上局规则：任务4需要2个失败票才能算失败
        req_fails = 2 if num_players >= 7 and room['current_mission'] == 3 else 1
        
        is_success = fails < req_fails
        room['results'].append(is_success)
        
        if is_success:
            msg = f"🟢 任务高捷！【成功】（本轮出现 {fails} 张破坏票"
            if req_fails == 2 and fails == 1:
                msg += "，但在7人以上局第4次任务中，1张红票不足以毁坏任务"
            msg += "）"
            log(msg, "#2ecc71")
        else:
            log(f"🔴 任务崩塌！【失败】（本轮惊现 {fails} 张破坏票！）", "#e74c3c")
        
        good_wins = room['results'].count(True)
        evil_wins = room['results'].count(False)
        
        if evil_wins >= 3:
            game_over(False, "坏人胜利：累计已成功破坏3次任务！")
        elif good_wins >= 3:
            start_assassination_phase()
        else:
            room['current_mission'] += 1
            room['leader_index'] = (room['leader_index'] + 1) % num_players
            start_building_phase()

def start_assassination_phase():
    room['state'] = 'assassination'
    log("🗡️ 好人率先赢下3次任务！直接进入刺杀大翻盘环节！请唯一的现身刺客指定目标...", "#8e44ad")
    broadcast_state()
    
    assassin = next(p for p in room['players'] if p['role'] == 'Assassin')
    good_names = [p['name'] for p in room['players'] if p['is_good']]
    
    if assassin['is_bot']:
        target = random.choice(good_names)
        socketio.start_background_task(bot_submit_assassination, target)
    else:
        socketio.emit('request_assassination', {'targets': good_names}, to=assassin['sid'])

def bot_submit_assassination(target):
    time.sleep(5)
    handle_assassination(target)

@socketio.on('submit_assassination')
def on_submit_assassination(data):
    handle_assassination(data['target'])

def handle_assassination(target_name):
    target = next(p for p in room['players'] if p['name'] == target_name)
    log(f"🔫 嘭！刺客扣动了扳机，选择枪决 【{target_name}】 ！", "#c0392b")
    
    if target['role'] == 'Merlin':
        game_over(False, f"惊天血案！被枪杀的 {target_name} 正是躲在暗处的梅林！坏人最后绝地大翻盘！")
    else:
        game_over(True, f"大反扑失败！被枪杀的 {target_name} 根本不是梅林（他是无辜的 {target['role']}），好人顺利捍卫了光明！")

def game_over(good_won, reason):
    room['state'] = 'over'
    color = "#2ecc71" if good_won else "#e74c3c"
    log(f"🏆 终局钟声敲响！{reason}", color)
    broadcast_state()
    
    final_roles = [f"<span style='color:{'#2ecc71' if p['is_good'] else '#e74c3c'}'>{p['name']}: {p['role']}</span>" for p in room['players']]
    socketio.emit('game_over', {
        'good_won': good_won,
        'reason': reason,
        'roles': final_roles
    })
    
    def reset():
        time.sleep(15)
        room['players'] = []
        room['state'] = 'waiting'
        socketio.emit('force_reload')
    socketio.start_background_task(reset)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    p = next((x for x in room['players'] if x['sid'] == sid), None)
    if p and room['state'] not in ['waiting', 'over']:
        log(f"❌ 玩家 {p['name']} 掉线跑路，对局强行终止，正在清空房间...", "#c0392b")
        game_over(False, "局末有人拔网线，流局！")
        room['players'] = []
        room['state'] = 'waiting'
        socketio.emit('force_reload')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)