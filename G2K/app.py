from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
from collections import defaultdict
import csv
import os
import random
import json
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
        {"q": "Zou je liever een jaar lang geen muziek luisteren of een jaar lang geen sociale media gebruiken?", "type": "open"},
        # {"q": "Would you rather? Zou je liever supersterk zijn of supersnel?", "type": "action"},
        {"q": "Welke superkracht zou je willen hebben?", "type": "open"},
        # {"q": "Would you rather? Zou je liever de rest van je leven alleen maar fluisteren, of altijd schreeuwen?", "type": "action"},
        # {"q": "Would you rather? Zou je liever elke ochtend wakker worden met een ander kapsel, of elke dag een ander stemgeluid hebben?", "type": "action"},
        {"q": "Wat voor serie/film/boek zou je opnieuw willen zien/lezen?", "type": "open"},
    ],
    "minigames": [
        # {"q": "Staarwedstrijd! De eerste die knippert verliest.", "type": "action"},
        # {"q": "Wie kan het langst op één been staan met de ogen dicht?", "type": "action"},
        {"q": "Galgje","d":"Galgje is een spel waarbij je een woord moet raden door steeds een letter te kiezen. Je mag maar een beperkt aantal letters fout kiezen.","type": "action"},
        {"q": "Wordchain", "type": "action"},
        {"q": "Thirty seconds", "type": "action."},
        # {"q": "Beeld een dier uit zonder geluid te maken. De rest raadt!", "type": "action"}
    ],
    "get2know": [
        # {"q": "Waar ben je het meest dankbaar voor van de afgelopen week?", "type": "open"},
        {"q": "Wat is een eigenschap die je echt in anderen bewondert?", "type": "open"},
        {"q": "Wat is iets wat je echt wilt doen/leren dit jaar?", "type": "open"},
        # {"q": "Wat is iets aan jou dat mensen niet meteen van je zouden verwachten?", "type": "open"},
        {"q": "Waar ben je trots op?", "type": "open"},
        # {"q": "Wanneer heb je het gevoel dat iemand jou echt begrijpt? ", "type": "open"},
        # {"q": "Wat voor kwaliteiten maken een goeie vriend?", "type": "open"},
        {"q": "Zou je liever vrienden zijn met iemand die heel veel op je lijkt qua intresses of juist totaal anders is?", "type": "open"}
    ],
    "would_you_rather": [
        {"q": "Zou je liever een jaar lang geen muziek luisteren of een jaar lang geen sociale media gebruiken?", "type": "multiple_choice", "options": ["Een jaar lang geen muziek luisteren", "Een jaar lang geen sociale media gebruiken"]},
        {"q": "Zou je liever elke ochtend wakker worden met een ander kapsel, of elke dag een andere stem hebben?", "type": "multiple_choice", "options": ["Elke ochtend met een ander kapsel", "Elke dag een andere stem"]},
    ],
    "statements": [
        {"q": "Kwaliteit gaat altijd boven kwantiteit als het gaat om je sociale kring.", "type": "multiple_choice", "options": ["Eens", "Oneens"]},
        {"q": "Sociale media heeft sociale contacten oppervlakkiger gemaakt.", "type": "multiple_choice", "options": ["Eens", "Oneens"]},
        {"q": "Een goede vriend hoort je te steunen, zelfs als je overduidelijk ongelijk hebt.", "type": "multiple_choice", "options": ["Eens", "Oneens"]},
    ],
}

# Load thirty-seconds lists 
THIRTY_SECONDS_LISTS = []
try:
    _path = os.path.join(os.path.dirname(__file__), 'thirty_seconds.json')
    if os.path.exists(_path):
        with open(_path, 'r', encoding='utf-8') as _f:
            _data = json.load(_f)
            THIRTY_SECONDS_LISTS = _data.get('lists', []) or []
except Exception:
    THIRTY_SECONDS_LISTS = []

# Load wordchain themes 
WORDCHAIN_THEMES = []
try:
    _path = os.path.join(os.path.dirname(__file__), 'wordchain.json')
    if os.path.exists(_path):
        with open(_path, 'r', encoding='utf-8') as _f:
            _data = json.load(_f)
            WORDCHAIN_THEMES = _data.get('themes', []) or []
except Exception:
    WORDCHAIN_THEMES = []

# Load galgje words 
HANGMAN_WORDS = []
try:
    _path = os.path.join(os.path.dirname(__file__), 'galgje.json')
    if os.path.exists(_path):
        with open(_path, 'r', encoding='utf-8') as _f:
            _data = json.load(_f)
            HANGMAN_WORDS = _data.get('woorden', []) or []
except Exception:
    HANGMAN_WORDS = []

games = {}


def build_question_queue(settings):
    ice_breakers = [('ice_breakers', q) for q in random.sample(
        QUESTIONS['ice_breakers'],
        min(int(settings['ice']), len(QUESTIONS['ice_breakers']))
    )]
    
    would_you_rather = [('would_you_rather', q) for q in random.sample(
        QUESTIONS['would_you_rather'],
        min(int(settings['wy']), len(QUESTIONS['would_you_rather']))
    )]
    
    statements = [('statements', q) for q in random.sample(
        QUESTIONS['statements'],
        min(int(settings.get('st', 0)), len(QUESTIONS['statements']))
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
        'would_you_rather': would_you_rather,
        'statements': statements,
    }
    last_category = queue[-1][0] if queue else None
    streak = 1 if last_category in active_pools else 0

    while active_pools['minigames'] or active_pools['get2know'] or active_pools['would_you_rather'] or active_pools['statements']:
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
def host_page():
    slider_maxes = {
        'ice': min(len(QUESTIONS['ice_breakers']), 10),
        'mini': min(len(QUESTIONS['minigames']), 10),
        'deep': min(len(QUESTIONS['get2know']), 10),
        'wy': min(len(QUESTIONS['would_you_rather']), 10),
        'st': min(len(QUESTIONS['statements']), 10),
    }
    return render_template('host.html', slider_maxes=slider_maxes)

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
    settings = data.get('settings') or {}
    games[room] = {
        'players': [], 'history': [], 'settings': settings, 'queue': [], 'current_answers': [],
        'answered_count': 0, 'hangman': None, 'round_history': [], 'revisit_stack': [], 'current_round': None
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
        game['round_history'] = []
        game['revisit_stack'] = []
        game['current_round'] = None
        socketio.sleep(1)
        send_next_question(room)

@socketio.on('submit_answer')
def on_answer(data):
    room = data.get('room')
    if room in games:
        games[room]['current_answers'].append({'player': data['name'], 'answer': data['answer']})
        games[room]['answered_count'] += 1
        emit('update_status', {'answered': games[room]['answered_count'], 'total': len(games[room]['players']) - 1}, to=room)


@socketio.on('hangman_guess')
def on_hangman_guess(data):
    room = data.get('room')
    letter = (data.get('letter') or '').strip().lower()
    if room not in games or not letter:
        return

    game = games[room]
    hangman = game.get('hangman')
    if not hangman or hangman.get('finished'):
        return

    if len(letter) != 1 or not letter.isalpha():
        return

    if letter in hangman['guessed_letters']:
        emit('hangman_state', _build_hangman_state(hangman), to=room)
        return

    hangman['guessed_letters'].append(letter)
    secret_word = hangman['word'].lower()
    if letter not in secret_word:
        hangman['wrong_letters'].append(letter)
        hangman['lives'] -= 1

    solved = _hangman_is_solved(secret_word, hangman['guessed_letters'])
    hangman['solved'] = solved
    hangman['finished'] = solved or hangman['lives'] <= 0

    emit('hangman_state', _build_hangman_state(hangman), to=room)
    if hangman['finished']:
        emit('hangman_complete', {
            'solved': solved,
            'word': hangman['word'],
            'lives': hangman['lives']
        }, to=room)

@socketio.on('hangman_hint')
def on_hangman_hint(data):
    room = data.get('room')
    if room not in games:
        return

    game = games[room]
    hangman = game.get('hangman')
    if not hangman or hangman.get('finished'):
        return

    if hangman.get('hint_used'):
        emit('hangman_state', _build_hangman_state(hangman), to=room)
        return

    # Lose one life for using hint
    hangman['lives'] -= 1
    hangman['hint_used'] = True
    
    secret_word = hangman['word'].lower()
    unguessed = [char for char in secret_word if char.isalpha() and char not in hangman['guessed_letters']]
    
    if unguessed:
        revealed_letter = random.choice(unguessed)
        hangman['guessed_letters'].append(revealed_letter)
    
    # Check solved
    solved = _hangman_is_solved(secret_word, hangman['guessed_letters'])
    hangman['solved'] = solved
    hangman['finished'] = solved or hangman['lives'] <= 0

    emit('hangman_state', _build_hangman_state(hangman), to=room)
    if hangman['finished']:
        emit('hangman_complete', {
            'solved': solved,
            'word': hangman['word'],
            'lives': hangman['lives']
        }, to=room)

@socketio.on('request_next')
def handle_next(data):
    room = data.get('room')
    if room in games:
        if games[room]['current_answers'] and not data.get('force_next'):
            emit('show_results', {'answers': games[room]['current_answers']}, to=room)
            games[room]['current_answers'] = []
        else:
            game = games[room]
            if game.get('revisit_stack'):
                payload = game['revisit_stack'].pop()
                game['current_answers'] = []
                game['answered_count'] = 0
                game['current_round'] = payload
                game['round_history'].append(payload)
                emit('update_status', {'answered': 0, 'total': len(game['players']) - 1}, to=room)
                emit('next_round', payload, to=room)
            else:
                send_next_question(room)

@socketio.on('request_back')
def handle_back(data):
    room = data.get('room')
    if room not in games:
        return

    game = games[room]
    round_history = game.get('round_history') or []
    if len(round_history) < 2:
        return

    current_round = round_history.pop()
    previous_round = round_history[-1]

    game['revisit_stack'].append(current_round)
    game['current_answers'] = []
    game['answered_count'] = 0
    game['current_round'] = previous_round

    emit('update_status', {'answered': 0, 'total': len(game['players']) - 1}, to=room)
    emit('next_round', previous_round, to=room)

@socketio.on('start_thirty_seconds')
def on_start_thirty_seconds(data):
    room = data.get('room')
    if room in games:
        emit('thirty_seconds_started', {'room': room}, to=room)

def send_next_question(room):
    game = games[room]
    if not game['queue']:
        emit('game_over', {"message": "Bedankt voor het spelen!", "category": "end"}, to=room)
        return
    
    game['answered_count'] = 0
    cat, q_obj = game['queue'].pop(0)
    q_text = q_obj['q']
    q_type = q_obj.get('type', 'open')
    payload = None

    # minigame logica
    if q_text == 'Wordchain':
        theme = random.choice(WORDCHAIN_THEMES) if WORDCHAIN_THEMES else 'Dieren'
        q_text = theme
        q_type = 'wordchain'
        payload = {'theme': theme}

    if q_text == 'Galgje':
        word_pool = list(HANGMAN_WORDS)
        word_pool.extend(game['settings'].get('hangman_words') or [])
        word_pool = [w.strip() for w in word_pool if isinstance(w, str) and w.strip()]
        secret_word = random.choice(word_pool) if word_pool else 'regenboog'
        game['hangman'] = {
            'word': secret_word, 'guessed_letters': [], 'wrong_letters': [],
            'lives': 10, 'finished': False, 'solved': False, 'hint_used': False,
        }
        q_type = 'hangman'
        payload = _build_hangman_state(game['hangman'])

    if 'thirt' in q_text.lower():
        chosen = random.choice(THIRTY_SECONDS_LISTS) if THIRTY_SECONDS_LISTS else {'woorden': ['appel','auto','boom']}
        payload = {'naam': chosen.get('naam', ''), 'woorden': chosen.get('woorden', []), 'timer': 30}
        q_type = 'thirty_seconds'
        game['thirty_seconds_started'] = False

    game['history'].append(q_text)
    
    # Payload samenstellen voor de frontend
    emit_payload = {
        'category': cat, 
        'question': q_text, 
        'type': q_type,
        'mode': game['settings']['mode'], 
        'total_players': len(game['players']) - 1
    }
    
    if 'options' in q_obj:
        emit_payload['options'] = q_obj['options']
        
    if payload is not None:
        emit_payload['payload'] = payload

    game['current_round'] = emit_payload
    game['round_history'].append(emit_payload)
    emit('next_round', emit_payload, to=room)

def _hangman_is_solved(secret_word, guessed_letters):
    guessed = set(guessed_letters)
    for character in secret_word.lower():
        if character.isalpha() and character not in guessed:
            return False
    return True


def _mask_hangman_word(secret_word, guessed_letters):
    guessed = set(guessed_letters)
    masked_characters = []
    for character in secret_word:
        if not character.isalpha():
            masked_characters.append(character)
        elif character.lower() in guessed:
            masked_characters.append(character)
        else:
            masked_characters.append('_')
    return ' '.join(masked_characters)


def _build_hangman_state(hangman):
    return {
        'word_mask': _mask_hangman_word(hangman['word'], hangman['guessed_letters']),
        'lives': hangman['lives'],
        'guessed_letters': hangman['guessed_letters'],
        'wrong_letters': hangman['wrong_letters'],
        'solved': hangman['solved'],
        'finished': hangman['finished'],
    }

if __name__ == '__main__':
    socketio.run(app, debug=False, port=5026, host='0.0.0.0', allow_unsafe_werkzeug=True)