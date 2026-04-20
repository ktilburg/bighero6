from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'verbinding-is-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- DATABASE ---
QUESTIONS = {
    "ice_breakers": [
        {"q": "Wat was je allereerste bijbaantje?", "type": "open"},
        {"q": "Pizza met ananas: Culinair hoogstandje of een misdaad?", "type": "multiple_choice", "options": ["Geniaal", "Misdaad"]},
        {"q": "Als je voor de rest van je leven nog maar één gerecht mocht eten, wat zou dat zijn?", "type": "open"},
        {"q": "Op een schaal van 1-10: Hoe erg ben je een ochtendmens?", "type": "scale"},
        {"q": "Wat is de meest nutteloze app op je telefoon die je toch niet verwijdert?", "type": "open"},
        {"q": "Ben je een honden- of een kattenmens?", "type": "multiple_choice", "options": ["Honden", "Katten", "Beide", "Geen van beide"]},
        {"q": "Wat is je favoriete serie of film van dit moment?", "type": "open"},
        {"q": "Welke bekende persoon (dood of levend) zou je wel eens willen ontmoeten?", "type": "open"}
    ],
    "minigames": [
        {"q": "Staarwedstrijd! De eerste die knippert (of lacht) verliest.", "type": "action"},
        {"q": "Wie kan het langst op één been staan met de ogen dicht?", "type": "action"},
        {"q": "Beeld een dier uit zonder geluid te maken. De rest moet raden!", "type": "action"},
        {"q": "Typ 'De snelle bruine vos springt over de luie hond' in de groepsapp. Wie is het snelst?", "type": "action"},
        {"q": "Duimworstelen! Zoek een partner en start het toernooi.", "type": "action"},
        {"q": "Noem om de beurt een automerk. Wie stilvalt is af!", "type": "action"},
        {"q": "Luchtgitaar-solo! Wie geeft de meest overtuigende show van 10 seconden?", "type": "action"}
    ],
    "diepgaand": [
        {"q": "Waar ben je het meest dankbaar voor van de afgelopen week?", "type": "open"},
        {"q": "Wat is een eigenschap die je echt in anderen bewondert?", "type": "open"},
        {"q": "Als je één ding aan je verleden kon veranderen, wat zou dat zijn?", "type": "open"},
        {"q": "Wat is je grootste onzekerheid en hoe ga je daarmee om?", "type": "open"},
        {"q": "Wanneer heb je voor het laatst iets gedaan wat je echt eng vond?", "type": "open"},
        {"q": "Wat is volgens jou het belangrijkste in een vriendschap?", "type": "open"},
        {"q": "Op een schaal van 1-10: Hoe goed zit je momenteel in je vel?", "type": "scale"},
        {"q": "Wat is een droom die je nog steeds hoopt te verwezenlijken?", "type": "open"}
    ],
    "boomit_templates": [
        "Wie gaf het meest verrassende antwoord op de vraag: '{prev_q}'?",
        "Wie was volgens de groep de absolute winnaar van de minigame: '{prev_game}'?",
        "Als we één antwoord op de vraag '{prev_q}' moesten inlijsten, van wie zou dat zijn?",
        "Wie had de meeste moeite met de opdracht: '{prev_game}'?",
        "Wat was tot nu toe het meest grappige moment van deze sessie?",
        "Wie heeft ons het meest verbaasd tijdens de categorie '{prev_q}'?"
    ]
}

games = {}

@app.route('/')
def index(): return render_template('index.html')

@app.route('/host')
def host_page(): return render_template('host.html')

@app.route('/game')
def game_page(): return render_template('game.html')

# --- SOCKET LOGICA ---

@socketio.on('validate_code')
def on_validate(data):
    room = data.get('room')
    if room in games:
        emit('code_valid', {'valid': True, 'room': room}, to=request.sid)
    else:
        emit('code_valid', {'valid': False}, to=request.sid)

@socketio.on('create_game')
def on_create(data):
    room = str(random.randint(1000, 9999))
    games[room] = {
        'players': [],
        'history': [],
        'settings': data.get('settings', {'ice':3, 'mini':2, 'deep':3, 'boom':2}),
        'queue': []
    }
    join_room(room)
    emit('game_created', {'room': room}, to=request.sid)

@socketio.on('join_game')
def on_join(data):
    room = data.get('room')
    name = data.get('name')
    if room in games:
        join_room(room)
        # Check of speler al bestaat (voorkomt dubbele emoji's bij refresh)
        emojis = ["🦁", "🐘", "🍦", "🍕", "🚀", "🎸", "🥑", "👾"]
        player = {"name": name, "emoji": random.choice(emojis)}
        games[room]['players'].append(player)
        emit('player_joined', games[room]['players'], to=room)

@socketio.on('start_game')
def on_start(data):
    room = data.get('room')
    if room in games:
        game = games[room]
        s = game['settings']
        
        # 1. Ice Breakers eerst
        queue = [('ice_breakers', q) for q in random.sample(QUESTIONS['ice_breakers'], min(int(s['ice']), len(QUESTIONS['ice_breakers'])))]
        
        # 2. Mix van minigames en diepgang
        others = []
        others += [('minigames', q) for q in random.sample(QUESTIONS['minigames'], min(int(s['mini']), len(QUESTIONS['minigames'])))]
        others += [('diepgaand', q) for q in random.sample(QUESTIONS['diepgaand'], min(int(s['deep']), len(QUESTIONS['diepgaand'])))]
        random.shuffle(others)
        
        queue += others
        # 3. BoomIt aan het einde
        queue += [('boomit', None) for _ in range(int(s['boom']))]
        
        game['queue'] = queue
        
        # HEEL BELANGRIJK: Wacht 1 seconde zodat de host-pagina kan laden
        socketio.sleep(1)
        send_next_question(room)

@socketio.on('request_next')
def handle_next(data):
    room = data.get('room')
    if room in games:
        send_next_question(room)

def send_next_question(room):
    game = games[room]
    if not game['queue']:
        emit('game_over', {"message": "Bedankt voor het spelen!", "category": "end"}, to=room)
        return

    cat, q_obj = game['queue'].pop(0)
    
    if cat == 'boomit':
        if game['history']:
            prev = random.choice(game['history'])
            q_text = random.choice(QUESTIONS['boomit_templates']).replace('{prev_q}', prev).replace('{prev_game}', prev)
        else:
            q_text = "Wat was tot nu toe je favoriete moment?"
    else:
        q_text = q_obj['q']
        game['history'].append(q_text)

    emit('next_round', {'category': cat, 'question': q_text}, to=room)

if __name__ == '__main__':
    # Debug=False voor stabiliteit in Python 3.13
    socketio.run(app, debug=False, port=5026, host='0.0.0.0', allow_unsafe_werkzeug=True)