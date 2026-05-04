from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
import random

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'deepconnect-secure-key'
socketio = SocketIO(app, cors_allowed_origins="*")

OBJECT_NAMES = ["Banaan", "Koekenpan", "Stofzuiger", "Gitaar", "Cactus", "Laptop", "Ananas", "Vliegtuig", "Watermeloen", "Tandenborstel", "Wasmachine", "Robot"]
QUESTIONS = {
    "ice_breakers": [
        {"q": "Wat was je allereerste bijbaantje?", "type": "open"},
        {"q": "Pizza met ananas: Culinair hoogstandje of een misdaad?", "type": "multiple_choice", "options": ["Geniaal", "Misdaad"]},
        {"q": "Als je voor de rest van je leven nog maar één gerecht mocht eten, wat zou dat zijn?", "type": "open"},
        {"q": "Op een schaal van 1-10: Hoe erg ben je een ochtendmens?", "type": "scale"},
        {"q": "Would you rather? Zou je liever een jaar lang geen muziek horen of een jaar lang geen sociale media gebruiken?", "type": "action"},
        {"q": "Would you rather? Zou je liever supersterk zijn of supersnel?", "type": "action"},
        {"q": "Would you rather? Zou je liever de rest van je leven alleen maar fluisteren, of altijd schreeuwen?", "type": "action"},
        {"q": "Would you rather? Zou je liever elke ochtend wakker worden met een ander kapsel, of elke dag een ander stemgeluid hebben?", "type": "action"}
    ],
    "activiteiten": [
        {"q": "Staarwedstrijd! De eerste die knippert verliest.", "type": "action"},
        {"q": "Wie kan het langst op één been staan met de ogen dicht?", "type": "action"}, 
        {"q": "Beeld een dier uit zonder geluid te maken. De rest raadt!", "type": "action"}
    ],
    "diepgaand": [
        {"q": "Waar ben je het meest dankbaar voor van de afgelopen week?", "type": "open"},
        {"q": "Wat is een eigenschap die je echt in anderen bewondert?", "type": "open"},
        {"q": "Wat is een droom die je nog steeds hoopt te verwezenlijken?", "type": "open"},
        {"q": "Wat is iets aan jou dat mensen niet meteen van je zouden verwachten?", "type": "open"},
        {"q": "Waar ben je trots op?", "type": "open"},
        {"q": "Wanneer heb je het gevoel dat iemand jou echt begrijpt? ", "type": "open"},
        {"q": "Wat voor kwaliteiten maken een goeie vriend?", "type": "open"}
    ],
    "boomit_templates": [
        "Wie gaf het meest verrassende antwoord op: '{prev_q}'?",
        "Wie was volgens de groep de winnaar van de minigame: '{prev_game}'?"
    ]
}

games = {}

@app.route('/')
def index(): return render_template('index.html')

@app.route('/host')
def host_page(): return render_template('host.html')

@app.route('/game')
def game_page(): return render_template('game.html')

@socketio.on('validate_code')
def on_validate(data):
    room = data.get('room')
    if room in games:
        emit('code_valid', {'valid': True, 'room': room, 'custom_names': games[room]['settings'].get('custom_names', True)}, to=request.sid)
    else:
        emit('code_valid', {'valid': False}, to=request.sid)

@socketio.on('create_game')
def on_create(data):
    room = str(random.randint(1000, 9999))
    games[room] = {
        'players': [], 'history': [], 'settings': data.get('settings'), 'queue': [], 'current_answers': [], 'answered_count': 0
    }
    join_room(room)
    emit('game_created', {'room': room}, to=request.sid)

@socketio.on('join_game')
def on_join(data):
    room = data.get('room')
    if room in games:
        join_room(room)
        name = data.get('name')
        if not games[room]['settings'].get('custom_names', True) and name != "HOST":
            name = random.choice(OBJECT_NAMES) + " " + str(random.randint(10, 99))
        player = {"name": name, "emoji": random.choice(["🦁","🚀","🥑","👾","🎸","🍕"])}
        games[room]['players'].append(player)
        emit('player_joined', games[room]['players'], to=room)
        emit('name_assigned', {'name': name}, to=request.sid)

@socketio.on('start_game')
def on_start(data):
    room = data.get('room')
    if room in games:
        game = games[room]
        s = game['settings']
        queue = [('ice_breakers', q) for q in random.sample(QUESTIONS['ice_breakers'], min(int(s['ice']), len(QUESTIONS['ice_breakers'])))]
        others = [('minigames', q) for q in random.sample(QUESTIONS['minigames'], min(int(s['mini']), len(QUESTIONS['minigames'])))]
        others += [('diepgaand', q) for q in random.sample(QUESTIONS['diepgaand'], min(int(s['deep']), len(QUESTIONS['diepgaand'])))]
        random.shuffle(others)
        queue += others
        queue += [('boomit', None) for _ in range(int(s['boom']))]
        game['queue'] = queue
        socketio.sleep(1)
        send_next_question(room)

@socketio.on('submit_answer')
def on_answer(data):
    room = data.get('room')
    if room in games:
        games[room]['current_answers'].append({'player': data['name'], 'answer': data['answer']})
        games[room]['answered_count'] += 1
        emit('update_status', {'answered': games[room]['answered_count'], 'total': len(games[room]['players']) - 1}, to=room)

@socketio.on('request_next')
def handle_next(data):
    room = data.get('room')
    if room in games:
        if games[room]['current_answers'] and not data.get('force_next'):
            emit('show_results', {'answers': games[room]['current_answers']}, to=room)
            games[room]['current_answers'] = []
        else:
            send_next_question(room)

def send_next_question(room):
    game = games[room]
    if not game['queue']:
        # Expliciete categorie 'end' meesturen
        emit('game_over', {"message": "Bedankt voor het spelen!", "category": "end"}, to=room)
        return
    game['answered_count'] = 0
    cat, q_obj = game['queue'].pop(0)
    if cat == 'boomit':
        prev = random.choice(game['history']) if game['history'] else "deze sessie"
        q_text = random.choice(QUESTIONS['boomit_templates']).replace('{prev_q}', prev).replace('{prev_game}', prev)
        q_type = 'boomit'
    else:
        q_text = q_obj['q']
        q_type = q_obj.get('type', 'open')
        game['history'].append(q_text)
    emit('next_round', {
        'category': cat, 'question': q_text, 'type': q_type, 
        'mode': game['settings']['mode'], 'total_players': len(game['players']) - 1
    }, to=room)

if __name__ == '__main__':
    socketio.run(app, debug=False, port=5026, host='0.0.0.0', allow_unsafe_werkzeug=True)