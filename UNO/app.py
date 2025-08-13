# app.py (FIXED)


import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS # <-- ADD THIS LINE
from game import Card, Deck 

# --- App and SocketIO Setup ---
app = Flask(__name__)
CORS(app, cors_allowed_origins="*") # <-- ADD THIS LINE
app.config['SECRET_KEY'] = 'a_very_secret_key!'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Game State Management ---
games = {} 

class Player:
    """Represents a player in the game."""
    def __init__(self, sid, username):
        self.sid = sid
        self.username = username
        self.hand = []

    def to_json(self):
        """Converts player data to a JSON-serializable format for client-side rendering."""
        return { "sid": self.sid, "username": self.username, "card_count": len(self.hand) }

class Game:
    """Manages the state and logic for a single game room."""
    def __init__(self, room_id, host_sid):
        self.room_id = room_id
        self.players = []
        self.deck = Deck()
        self.discard_pile = []
        self.game_started = False
        self.host_sid = host_sid
        self.current_turn_index = 0
        self.game_direction = 1 
        self.winner = None

    def add_player(self, player):
        self.players.append(player)

    def get_player(self, sid):
        for p in self.players:
            if p.sid == sid:
                return p
        return None

    def start_game(self):
        """Deals cards, sets up the board, and determines the first turn."""
        if self.game_started or len(self.players) < 2:
            return
        self.deck.shuffle()
        for player in self.players:
            player.hand = [self.deck.draw_card() for _ in range(7)]
        
        first_card = self.deck.draw_card()
        while first_card.value in ["Wild", "Wild Draw Four"]:
            self.deck.cards.append(first_card)
            self.deck.shuffle()
            first_card = self.deck.draw_card()
        
        self.discard_pile.append(first_card)
        self.game_started = True
        
        self.current_turn_index = 0 
        
        if first_card.value == "Draw Two":
            self.draw_cards(self.players[0], 2)
            self.advance_turn() 
        elif first_card.value == "Reverse":
            self.game_direction *= -1
            self.advance_turn() 
        elif first_card.value == "Skip":
            self.advance_turn()

    def _reshuffle_discard_pile(self):
        """Reshuffles the discard pile back into the deck."""
        print(f"ROOM {self.room_id}: Reshuffling discard pile.")
        top_card = self.discard_pile.pop()
        for card in self.discard_pile:
            if card.value in ["Wild", "Wild Draw Four"]:
                card.color = "Wild"
        self.deck.cards.extend(self.discard_pile)
        self.deck.shuffle()
        self.discard_pile = [top_card]

    def draw_cards(self, player, num_cards):
        """Makes a player draw a specified number of cards."""
        print(f"ROOM {self.room_id}: {player.username} is drawing {num_cards} card(s).")
        for _ in range(num_cards):
            if not self.deck.cards:
                self._reshuffle_discard_pile()
            if self.deck.cards:
                player.hand.append(self.deck.draw_card())

    def advance_turn(self, steps=1):
        """Moves the turn to the next player."""
        self.current_turn_index = (self.current_turn_index + self.game_direction * steps) % len(self.players)

    def is_valid_play(self, card_to_play):
        """Checks if a card can be legally played."""
        top_card = self.discard_pile[-1]
        return (card_to_play.color == top_card.color or
                card_to_play.value == top_card.value or
                card_to_play.color == "Wild")

    def get_game_state(self, for_sid=None):
        """Returns the current state of the game, customized for the given player."""
        player = self.get_player(for_sid)
        if not self.game_started:
            return { "players": [p.to_json() for p in self.players], "host_sid": self.host_sid, "game_started": self.game_started, "winner": None }
        player_hand = [vars(card) for card in player.hand] if player else []
        return {
            "players": [p.to_json() for p in self.players],
            "host_sid": self.host_sid,
            "game_started": self.game_started,
            "discard_pile_top": vars(self.discard_pile[-1]),
            "player_hand": player_hand,
            "current_turn_sid": self.players[self.current_turn_index].sid,
            "deck_card_count": len(self.deck.cards),
            "winner": self.winner
        }

# --- SocketIO Event Handlers ---
def broadcast_game_state(room_id):
    """Sends the updated game state to all players in a room."""
    game = games.get(room_id)
    if game:
        for p in game.players:
            emit('update_game_state', game.get_game_state(p.sid), room=p.sid)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f"CLIENT CONNECTED: {request.sid}")

@socketio.on('create_room')
def handle_create_room(data):
    username = data.get('username', 'Anonymous')
    room_id = str(random.randint(1000, 9999))
    join_room(room_id)
    games[room_id] = Game(room_id, request.sid)
    player = Player(request.sid, username)
    games[room_id].add_player(player)
    print(f"ROOM {room_id}: Created by {username}.")
    emit('room_created', {'room_id': room_id})
    broadcast_game_state(room_id)

@socketio.on('join_room')
def handle_join_room(data):
    username = data.get('username', 'Anonymous')
    room_id = data.get('room_id')
    if room_id in games and not games[room_id].game_started:
        join_room(room_id)
        player = Player(request.sid, username)
        games[room_id].add_player(player)
        print(f"ROOM {room_id}: {username} has joined.")
        
        # *** THE FIX IS HERE: Tell the joining player which room they are in ***
        emit('room_joined', {'room_id': room_id}) 
        
        broadcast_game_state(room_id)
    else:
        emit('error', {'message': 'Room not found or game has already started.'})

@socketio.on('start_game')
def handle_start_game(data):
    room_id = data.get('room_id')
    game = games.get(room_id)
    if game and game.host_sid == request.sid:
        print(f"ROOM {room_id}: Game starting...")
        game.start_game()
        broadcast_game_state(room_id)
        starter = game.players[game.current_turn_index]
        print(f"ROOM {room_id}: First turn belongs to {starter.username}.")


@socketio.on('play_card')
def handle_play_card(data):
    room_id = data.get('room_id')
    game = games.get(room_id)
    
    # This check now prevents the crash
    if not game:
        print(f"ERROR: Game not found for room ID: {room_id}")
        return
        
    player = game.get_player(request.sid)

    if not player or game.players[game.current_turn_index].sid != request.sid:
        return 

    card_data = data.get('card')
    card_to_play = Card(card_data['color'], card_data['value'])

    if not game.is_valid_play(card_to_play):
        return

    card_in_hand = None
    for c in player.hand:
        if c.color == card_to_play.color and c.value == card_to_play.value:
            card_in_hand = c
            break
    
    if not card_in_hand:
        return

    player.hand.remove(card_in_hand)
    
    if card_in_hand.value in ["Wild", "Wild Draw Four"]:
        card_in_hand.color = data.get('chosen_color')
    
    game.discard_pile.append(card_in_hand)

    if len(player.hand) == 0:
        game.winner = player.username
        broadcast_game_state(room_id)
        return

    steps_to_advance = 1
    if card_in_hand.value == "Reverse":
        game.game_direction *= -1
        if len(game.players) == 2: steps_to_advance = 2
    elif card_in_hand.value == "Skip":
        steps_to_advance = 2
    elif card_in_hand.value == "Draw Two":
        next_player = game.players[(game.current_turn_index + game.game_direction) % len(game.players)]
        game.draw_cards(next_player, 2)
        steps_to_advance = 2
    elif card_in_hand.value == "Wild Draw Four":
        next_player = game.players[(game.current_turn_index + game.game_direction) % len(game.players)]
        game.draw_cards(next_player, 4)
        steps_to_advance = 2
    
    game.advance_turn(steps_to_advance)
    broadcast_game_state(room_id)


@socketio.on('draw_card')
def handle_draw_card(data):
    room_id = data.get('room_id')
    game = games.get(room_id)
    if not game: return
    player = game.get_player(request.sid)

    if not player or game.players[game.current_turn_index].sid != request.sid:
        return

    game.draw_cards(player, 1)
    game.advance_turn()
    broadcast_game_state(room_id)

# --- Main Entry Point ---
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
