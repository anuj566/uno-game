// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    const socket = io("https://uno-game-6478.onrender.com");

    // --- State Variables ---
    let mySid = null;
    let myUsername = '';
    let currentRoomId = null; // This was the problem variable
    let isHost = false;
    let myTurn = false;
    let cardToPlayAfterWild = null;

    // --- DOM Elements ---
    const lobbyDiv = document.getElementById('lobby');
    const waitingRoomDiv = document.getElementById('waiting-room');
    const gameTableDiv = document.getElementById('game-table');
    const usernameInput = document.getElementById('username');
    const createRoomBtn = document.getElementById('create-room-btn');
    const joinRoomBtn = document.getElementById('join-room-btn');
    const roomIdInput = document.getElementById('room-id-input');
    const errorMessage = document.getElementById('error-message');
    const roomCodeSpan = document.getElementById('room-code');
    const playerList = document.getElementById('player-list');
    const startGameBtn = document.getElementById('start-game-btn');
    const playerHandDiv = document.getElementById('player-hand');
    const opponentContainer = document.getElementById('opponent-container');
    const discardPileDiv = document.getElementById('discard-pile');
    const drawPileDiv = document.getElementById('draw-pile');
    const wildColorPicker = document.getElementById('wild-color-picker');
    const colorChoices = document.querySelectorAll('.color-choice');
    const winnerModal = document.getElementById('winner-announcement');
    const winnerNameSpan = document.getElementById('winner-name');
    const selfPlayerArea = document.querySelector('.self-area');

    // --- Utility Functions ---
    function switchView(view) {
        lobbyDiv.classList.remove('active');
        waitingRoomDiv.classList.remove('active');
        gameTableDiv.classList.remove('active');
        document.getElementById(view).classList.add('active');
    }

    function renderCard(cardData) {
        const cardDiv = document.createElement('div');
        cardDiv.classList.add('card');
        if (cardData.color !== 'back') {
            cardDiv.classList.add(cardData.color);
        } else {
            cardDiv.classList.add('back');
        }
        cardDiv.dataset.color = cardData.color;
        cardDiv.dataset.value = cardData.value;
        const valueSpan = document.createElement('span');
        valueSpan.innerText = cardData.value.replace(/ /g, '\n');
        cardDiv.appendChild(valueSpan);
        return cardDiv;
    }

    function updateGameState(state) {
        if (state.winner) {
            winnerNameSpan.innerText = `${state.winner} wins!`;
            winnerModal.classList.add('active');
            return;
        }

        if (!state.game_started) {
            roomCodeSpan.innerText = currentRoomId;
            playerList.innerHTML = '';
            state.players.forEach(p => {
                const li = document.createElement('li');
                li.innerText = p.username + (p.sid === state.host_sid ? ' (Host)' : '');
                playerList.appendChild(li);
            });
            if (isHost) startGameBtn.style.display = 'block';
            switchView('waiting-room');
        } else {
            myTurn = state.current_turn_sid === mySid;
            
            playerHandDiv.innerHTML = '';
            const topCard = state.discard_pile_top;
            state.player_hand.forEach(cardData => {
                const cardDiv = renderCard(cardData);
                if (myTurn && (cardData.color === 'Wild' || cardData.color === topCard.color || cardData.value === topCard.value)) {
                    cardDiv.classList.add('playable');
                }
                playerHandDiv.appendChild(cardDiv);
            });

            opponentContainer.innerHTML = '';
            const myPlayerIndex = state.players.findIndex(p => p.sid === mySid);
            const reorderedPlayers = [...state.players.slice(myPlayerIndex + 1), ...state.players.slice(0, myPlayerIndex)];
            reorderedPlayers.forEach(opponent => {
                const opponentDiv = document.createElement('div');
                opponentDiv.classList.add('opponent');
                opponentDiv.id = `player-${opponent.sid}`;
                const nameDiv = document.createElement('div');
                nameDiv.classList.add('player-name');
                nameDiv.innerText = `${opponent.username} (${opponent.card_count} cards)`;
                const handDiv = document.createElement('div');
                handDiv.classList.add('hand');
                for (let i = 0; i < opponent.card_count; i++) {
                    handDiv.appendChild(renderCard({color: 'back', value: ''}));
                }
                opponentDiv.appendChild(handDiv);
                opponentDiv.appendChild(nameDiv);
                opponentContainer.appendChild(opponentDiv);
            });

            discardPileDiv.innerHTML = '';
            discardPileDiv.appendChild(renderCard(topCard));

            document.querySelectorAll('.opponent').forEach(el => el.classList.remove('current-turn'));
            selfPlayerArea.classList.remove('current-turn');

            if (myTurn) {
                selfPlayerArea.classList.add('current-turn');
            } else {
                const currentTurnEl = document.getElementById(`player-${state.current_turn_sid}`);
                if(currentTurnEl) currentTurnEl.classList.add('current-turn');
            }
            
            switchView('game-table');
        }
    }

    // --- Event Listeners ---
    createRoomBtn.addEventListener('click', () => {
        myUsername = usernameInput.value.trim();
        if (!myUsername) { errorMessage.innerText = 'Please enter a name.'; return; }
        errorMessage.innerText = '';
        socket.emit('create_room', { username: myUsername });
    });

    joinRoomBtn.addEventListener('click', () => {
        myUsername = usernameInput.value.trim();
        const roomId = roomIdInput.value.trim();
        if (!myUsername || !roomId) { errorMessage.innerText = 'Please enter name and room code.'; return; }
        errorMessage.innerText = '';
        socket.emit('join_room', { username: myUsername, room_id: roomId });
    });
    
    startGameBtn.addEventListener('click', () => {
        socket.emit('start_game', { room_id: currentRoomId });
    });

    playerHandDiv.addEventListener('click', (e) => {
        if (!myTurn) return;
        const cardDiv = e.target.closest('.card');
        if (cardDiv && cardDiv.classList.contains('playable')) {
            const card = { color: cardDiv.dataset.color, value: cardDiv.dataset.value };
            if (card.color === 'Wild') {
                cardToPlayAfterWild = card;
                wildColorPicker.classList.add('active');
            } else {
                socket.emit('play_card', { room_id: currentRoomId, card: card });
            }
        }
    });

    drawPileDiv.addEventListener('click', () => {
        if (myTurn) {
            socket.emit('draw_card', { room_id: currentRoomId });
        }
    });

    colorChoices.forEach(choice => {
        choice.addEventListener('click', () => {
            const chosenColor = choice.dataset.color;
            wildColorPicker.classList.remove('active');
            socket.emit('play_card', {
                room_id: currentRoomId,
                card: cardToPlayAfterWild,
                chosen_color: chosenColor
            });
            cardToPlayAfterWild = null;
        });
    });

    // --- SocketIO Handlers ---
    socket.on('connect', () => { mySid = socket.id; });

    socket.on('room_created', (data) => {
        currentRoomId = data.room_id;
        isHost = true;
    });
    
    // *** THE FIX IS HERE: Listen for the confirmation from the server ***
    socket.on('room_joined', (data) => {
        currentRoomId = data.room_id;
        isHost = false;
        console.log(`Successfully joined room: ${currentRoomId}`);
    });

    socket.on('update_game_state', updateGameState);
    
    socket.on('error', (data) => { errorMessage.innerText = data.message; });
});