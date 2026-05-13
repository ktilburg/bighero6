from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
from collections import defaultdict
import csv
import os
import random
from threading import Lock

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'deepconnect-secure-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# alleen voor testen en feedback 
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# FEEDBACK_FILE = os.path.join(BASE_DIR, 'feedback.xls')
# feedback_lock = Lock()
# feedback_scores = defaultdict(lambda: {'upvotes': 0, 'downvotes': 0})
# # Feedback systeem 

# def load_feedback_scores():
#     if not os.path.exists(FEEDBACK_FILE):
#         return
#     with open(FEEDBACK_FILE, 'r', encoding='utf-8', newline='') as feedback_handle:
#         reader = csv.DictReader(feedback_handle, delimiter='\t')
#         for row in reader:
#             question = row.get('question', '').strip()
#             if not question:
#                 continue
#             feedback_scores[question] = {
#                 'upvotes': int(row.get('upvotes', 0) or 0),
#                 'downvotes': int(row.get('downvotes', 0) or 0),
#             }


# def save_feedback_scores():
#     with open(FEEDBACK_FILE, 'w', encoding='utf-8', newline='') as feedback_handle:
#         writer = csv.DictWriter(feedback_handle, fieldnames=['question', 'upvotes', 'downvotes'], delimiter='\t')
#         writer.writeheader()
#         for question, counts in sorted(feedback_scores.items()):
#             writer.writerow({
#                 'question': question,
#                 'upvotes': counts['upvotes'],
#                 'downvotes': counts['downvotes'],
#             })


# load_feedback_scores()

OBJECT_NAMES = ["Banaan", "Koekenpan", "Stofzuiger", "Gitaar", "Cactus", "Laptop", "Ananas", "Vliegtuig", "Watermeloen", "Tandenborstel", "Wasmachine", "Robot"]
QUESTIONS = {
    "ice_breakers": [
        # {"q": "Wat was je allereerste bijbaantje?", "type": "open"},
        # {"q": "Pizza met ananas: Culinair hoogstandje of een misdaad?", "type": "multiple_choice", "options": ["Geniaal", "Misdaad"]},
        {"q": "Als je voor de rest van je leven nog maar één gerecht mocht eten, wat zou dat zijn?", "type": "open"},
        # {"q": "Op een schaal van 1-10: Hoe erg ben je een ochtendmens?", "type": "scale"},
        # {"q": "Would you rather? Zou je liever supersterk zijn of supersnel?", "type": "action"},
        {"q": "Welke superkracht zou je willen hebben?", "type": "open"},
        # {"q": "Would you rather? Zou je liever de rest van je leven alleen maar fluisteren, of altijd schreeuwen?", "type": "action"},
        {"q": "Wat voor serie/film/boek zou je opnieuw willen zien/lezen?", "type": "open"},
    ],
    "would_you_rather": [
        {"q": "Zou je liever een jaar lang geen muziek luisteren of een jaar lang geen sociale media gebruiken?", "type": "multiple_choice", "options": ["Een jaar lang geen muziek luisteren", "Een jaar lang geen sociale media gebruiken"]},
        {"q": "Zou je liever elke ochtend wakker worden met een ander kapsel, of elke dag een andere stem hebben?", "type": "multiple_choice", "options": ["Elke ochtend met een ander kapsel", "Elke dag een andere stem"]},
    ],
    "minigames": [
        # {"q": "Staarwedstrijd! De eerste die knippert verliest.", "type": "action"},
        # {"q": "Wie kan het langst op één been staan met de ogen dicht?", "type": "action"},
        {"q": "Galgje","d":"Galgje is een spel waarbij je een woord moet raden door steeds een letter te kiezen. Je mag maar een beperkt aantal letters fout kiezen.","type": "action"},
        {"q": "Wordchain", "type": "action"},
        {"q": "Thirthy seconds", "type": "action."},
        # {"q": "Beeld een dier uit zonder geluid te maken. De rest raadt!", "type": "action"}
    ],
    "get2know": [
        # {"q": "Waar ben je het meest dankbaar voor van de afgelopen week?", "type": "open"},
        {"q": "Wat is een eigenschap die je echt in anderen bewonderd?", "type": "open"},
        {"q": "Wat is iets wat je echt wilt doen/leren dit jaar?", "type": "open"},
        # {"q": "Wat is iets aan jou dat mensen niet meteen van je zouden verwachten?", "type": "open"},
        {"q": "Waar ben je trots op?", "type": "open"},
        # {"q": "Wanneer heb je het gevoel dat iemand jou echt begrijpt? ", "type": "open"},
        # {"q": "Wat voor kwaliteiten maken een goeie vriend?", "type": "open"},
        {"q": "zou je liever vrienden zijn met iemand die heel veel op je lijkt qua persoonlijkheid of juist totaal anders is?", "type": "open"}
    ],
}

games = {}


def build_question_queue(settings):
    ice_breakers = [('ice_breakers', q) for q in random.sample(
        QUESTIONS['ice_breakers'],
        min(int(settings['ice']), len(QUESTIONS['ice_breakers']))
    )]

    minigames = [('minigames', q) for q in random.sample(
        QUESTIONS['minigames'],
        min(int(settings['mini']), len(QUESTIONS['minigames']))
    )]

    get2know = [('get2know', q) for q in random.sample(
        QUESTIONS['get2know'],
        min(int(settings['deep']), len(QUESTIONS['get2know']))
    )]

    queue = list(ice_breakers)

    if get2know:
        queue.append(get2know.pop(0))

    active_pools = {
        'minigames': minigames,
        'get2know': get2know,
    }
    last_category = queue[-1][0] if queue else None
    streak = 1 if last_category in active_pools else 0

    while active_pools['minigames'] or active_pools['get2know']:
        available_categories = [
            category for category, pool in active_pools.items() if pool
        ]

        if last_category in available_categories and streak >= 2 and len(available_categories) > 1:
            available_categories = [category for category in available_categories if category != last_category]

        if not available_categories:
            available_categories = [category for category, pool in active_pools.items() if pool]

        next_category = random.choice(available_categories)
        queue.append(active_pools[next_category].pop(0))

        if next_category == last_category:
            streak += 1
        else:
            last_category = next_category
            streak = 1

    return queue

@app.route('/')
def index(): return render_template('index.html')

@app.route('/host')
def host_page(): return render_template('host.html')

@app.route('/game')
def game_page(): return render_template('game.html')


# @socketio.on('submit_feedback')
# def on_feedback(data):
#     question = (data.get('question') or '').strip()
#     vote = data.get('vote')
#     if not question or vote not in ('up', 'down'):
#         emit('feedback_saved', {'ok': False}, to=request.sid)
#         return

#     with feedback_lock:
#         counts = feedback_scores[question]
#         if vote == 'up':
#             counts['upvotes'] += 1
#         else:
#             counts['downvotes'] += 1
#         save_feedback_scores()

#     emit('feedback_saved', {
#         'ok': True,
#         'question': question,
#         'upvotes': feedback_scores[question]['upvotes'],
#         'downvotes': feedback_scores[question]['downvotes'],
#     }, to=request.sid)

@socketio.on('validate_code')
def on_validate(data):
    room = data.get('room')
    if room in games:
        emit('code_valid', {'valid': True, 'room': room, 'custom_names': games[room]['settings'].get('custom_names', True)}, to=request.sid) # type: ignore
    else:
        emit('code_valid', {'valid': False}, to=request.sid) # type: ignore

@socketio.on('create_game')
def on_create(data):
    room = str(random.randint(1000, 9999))
    games[room] = {
        'players': [], 'history': [], 'settings': data.get('settings'), 'queue': [], 'current_answers': [], 'answered_count': 0
    }
    join_room(room)
    emit('game_created', {'room': room}, to=request.sid) # type: ignore

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
        emit('name_assigned', {'name': name}, to=request.sid) # type: ignore

@socketio.on('start_game')
def on_start(data):
    room = data.get('room')
    if room in games:
        game = games[room]
        game['queue'] = build_question_queue(game['settings'])
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
    q_text = q_obj['q']
    q_type = q_obj.get('type', 'open')
    game['history'].append(q_text)
    emit('next_round', {
        'category': cat, 'question': q_text, 'type': q_type, 
        'mode': game['settings']['mode'], 'total_players': len(game['players']) - 1
    }, to=room)

if __name__ == '__main__':
    socketio.run(app, debug=False, port=5026, host='0.0.0.0', allow_unsafe_werkzeug=True)