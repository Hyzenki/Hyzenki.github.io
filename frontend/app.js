let players = [];
let currentChart = null; // Variabile globale per tenere traccia del grafico corrente

class Player {
    constructor(name, points = 1200, matchesWon = 0) {
        this.name = name;
        this.points = points;
        this.matchesWon = matchesWon;
    }
}

// Configurazione dell'ambiente
const API_CONFIG = {
    development: {
        baseUrl: 'http://localhost:5000'
    },
    production: {
        baseUrl: 'https://tuo-server-produzione.com' // Sostituisci con l'URL del tuo server di produzione
    }
};

const isProduction = window.location.hostname === 'hyzenki.github.io';
const API_BASE_URL = isProduction ? API_CONFIG.production.baseUrl : API_CONFIG.development.baseUrl;

async function loadRankings() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/rankings`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors',
            credentials: isProduction ? 'omit' : 'include'
        });
        const result = await response.json();
        
        if (result.success && result.data) {
            updateRankingsTable(result.data);
        } else {
            console.error('Errore nel caricamento della classifica:', result.error);
            alert('Errore nel caricamento della classifica');
        }
    } catch (error) {
        console.error('Errore nella richiesta:', error);
        alert('Il server non è raggiungibile. Assicurati che sia in esecuzione e accessibile.');
    }
}

function updateRankingsTable(players) {
    const rankingsTable = document.getElementById('rankings');
    rankingsTable.innerHTML = '';
    
    players.forEach((player, index) => {
        const row = document.createElement('tr');
        
        const playerLink = document.createElement('a');
        playerLink.href = '#';
        playerLink.className = 'player-link';
        playerLink.textContent = player.name;
        
        playerLink.onclick = function(e) {
            e.preventDefault();
            showPlayerHistory(player.name);
        };
        
        row.innerHTML = `
            <td class="text-center">${index + 1}</td>
            <td></td>
            <td class="text-center">${Math.round(player.points)}</td>
            <td class="text-center">${player.matches_won}</td>
            <td class="text-center">${player.matches_lost}</td>
            <td class="text-center">${player.matches_drawn}</td>
        `;
        
        row.cells[1].appendChild(playerLink);
        rankingsTable.appendChild(row);
    });
}

async function handleMatch(winner, loser, isDraw = false) {
    const token = localStorage.getItem('authToken');
    if (!token) {
        alert('Devi effettuare il login per registrare le partite');
        return;
    }

    try {
        const response = await fetch('http://localhost:5000/api/match', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                winner: winner,
                loser: loser,
                draw: isDraw
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const pointsExchange = result.pointsExchange;
            let message;
            if (isDraw) {
                message = `Pareggio registrato!\n${winner} ha guadagnato ${pointsExchange.won} punti\n${loser} ha guadagnato ${pointsExchange.lost} punti`;
            } else {
                message = `Match registrato!\n${winner} ha guadagnato ${pointsExchange.won} punti\n${loser} ha perso ${pointsExchange.lost} punti`;
            }
            alert(message);
            await loadRankings();
        } else {
            alert('Errore nella registrazione del match: ' + (result.error || 'Errore sconosciuto'));
        }
    } catch (error) {
        console.error('Errore nella richiesta:', error);
        alert('Errore nella comunicazione con il server');
    }
}


// Carica la classifica all'avvio
document.addEventListener('DOMContentLoaded', async () => {
    loadRankings();

    // Gestione login e registrazione
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('newUsername').value;
        const password = document.getElementById('newPassword').value;
        await registerTrustedUser(username, password);
    });

    document.getElementById('loginForm').addEventListener('submit', handleLogin);

    

    document.getElementById('matchForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const player1 = document.getElementById('player1').value;
        const player2 = document.getElementById('player2').value;
        const result = document.getElementById('result').value;

        if (player1 === player2) {
            alert('Seleziona due giocatori diversi');
            return;
        }

        if (result === '0') {
            await handleMatch(player1, player2, true);
        } else if (result === '1') {
            await handleMatch(player1, player2, false);
        } else {
            await handleMatch(player2, player1, false);
        }
    });
});

// Aggiungi queste funzioni
async function showPlayerHistory(playerName) {
    try {
        const rankingsResponse = await fetch('http://localhost:5000/api/rankings');
        const rankingsResult = await rankingsResponse.json();
        const playerData = rankingsResult.data.find(p => p.name === playerName);

        const historyResponse = await fetch(`http://localhost:5000/api/player/${playerName}/history`);
        const historyResult = await historyResponse.json();
        
        if (historyResult.success && playerData) {
            const playerDetails = document.getElementById('playerDetails');
            const playerHistory = document.getElementById('playerHistory');
            const playerStats = document.getElementById('playerStats');
            const playerNameH2 = document.getElementById('playerName');
            
            playerDetails.style.display = 'block';
            playerNameH2.textContent = `Statistiche di ${playerName}`;
            
            // Statistiche del giocatore dalla leaderboard
            playerStats.innerHTML = `
                <div class="stats-container">
                    <div class="stat-item text-center">
                        <strong>Partite Totali:</strong> ${playerData.matches_won + playerData.matches_lost + playerData.matches_drawn}
                    </div>
                    <div class="stat-item text-center">
                        <strong>Vittorie:</strong> ${playerData.matches_won}
                    </div>
                    <div class="stat-item text-center">
                        <strong>Sconfitte:</strong> ${playerData.matches_lost}
                    </div>
                    <div class="stat-item text-center">
                        <strong>Pareggi:</strong> ${playerData.matches_drawn}
                    </div>
                    <div class="stat-item text-center">
                        <strong>% Vittoria:</strong> ${calculateWinRate(playerData.matches_won, playerData.matches_lost, playerData.matches_drawn)}%
                    </div>
                    <div class="stat-item text-center">
                        <strong>Punti Totali:</strong> ${Math.round(playerData.points)}
                    </div>
                </div>
            `;

            // Tabella dello storico partite
            playerHistory.innerHTML = `
                <div class="match-history-wrapper">
                    <table class="match-history-table">
                        <thead>
                            <tr>
                                <th>Data</th>
                                <th>Avversario</th>
                                <th>Risultato</th>
                                <th>Punti</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${historyResult.matches.map(match => {
                                const matchDate = new Date(match.date).toLocaleString('it-IT');
                                let result, opponent, points;
                                
                                console.log('Match data:', match);
                                
                                if (match.is_draw === 1 || match.is_draw === true) {
                                    result = 'Pareggio';
                                    opponent = match.winner === playerName ? match.loser : match.winner;
                                    points = `+${match.points_gained || match.winner_points_change}`;
                                } else if (match.winner === playerName) {
                                    result = 'Vittoria';
                                    opponent = match.loser;
                                    points = `+${match.points_gained || match.winner_points_change}`;
                                } else {
                                    result = 'Sconfitta';
                                    opponent = match.winner;
                                    points = `-${match.points_lost || match.loser_points_change}`;
                                }

                                return `
                                    <tr class="${result.toLowerCase()}-row">
                                        <td>${matchDate}</td>
                                        <td>${opponent}</td>
                                        <td class="${result.toLowerCase()}-text">${result}</td>
                                        <td class="${points.startsWith('+') ? 'points-gained' : 'points-lost'}">${points}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            createPointsChart(historyResult.matches, playerName);
            playerDetails.scrollIntoView({ behavior: 'smooth' });
        } else {
            playerHistory.innerHTML = '<p>Nessuna partita trovata per questo giocatore.</p>';
            playerStats.innerHTML = '<p>Nessuna statistica disponibile</p>';
            document.getElementById('pointsChart').innerHTML = '';
        }
    } catch (error) {
        console.error('Errore nella richiesta:', error);
        alert('Errore nella comunicazione con il server');
    }
}

function calculateWinRate(wins, losses, draws) {
    const totalMatches = wins + losses + draws;
    return totalMatches > 0 
        ? Math.round((wins / totalMatches) * 100) 
        : 0;
}

function closePlayerDetails() {
    const playerDetails = document.getElementById('playerDetails');
    playerDetails.style.display = 'none';
}


function createPointsChart(matches, playerName) {
    if (currentChart) {
        currentChart.destroy();
    }

    const ctx = document.getElementById('pointsChart');
    if (!ctx) return;

    const canvas = document.createElement('canvas');
    ctx.innerHTML = '';
    ctx.appendChild(canvas);

    let currentPoints = 1200; // Punto di partenza
    const points = [1200];
    const sortedMatches = [...matches].sort((a, b) => new Date(a.date) - new Date(b.date));

    sortedMatches.forEach(match => {
        if (match.is_draw === 1 || match.is_draw === true) {
            currentPoints += match.points_gained;
        } else if (match.winner === playerName) {
            currentPoints += match.points_gained;
        } else {
            currentPoints -= match.points_lost;
        }
        points.push(currentPoints);
    });

    currentChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: ['Inizio', ...sortedMatches.map(m => new Date(m.date).toLocaleString('it-IT'))],
            datasets: [{
                label: 'Punti',
                data: points,
                borderColor: '#4CAF50',
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Andamento Punti - ${playerName}`
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });
}

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closePlayerDetails();
    }
});

// Funzione per registrare un utente affidato
async function registerTrustedUser(username, password) {
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('http://localhost:5000/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                username,
                password,
                is_trusted: true
            })
        });

        const data = await response.json();
        if (data.success) {
            alert('Utente affidato registrato con successo');
        } else {
            alert('Errore nella registrazione: ' + data.error);
        }
    } catch (error) {
        console.error('Errore:', error);
        alert('Errore nella comunicazione con il server');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('http://localhost:5000/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        
        if (data.success) {
            localStorage.setItem('authToken', data.token);
            document.getElementById('loginSection').style.display = 'none';
            document.getElementById('matchSection').style.display = 'block';
            if (data.is_admin) {
                document.getElementById('registerLink').style.display = 'block';
            }
        } else {
            alert('Login fallito: ' + data.error);
        }
    } catch (error) {
        console.error('Errore durante il login:', error);
        alert('Errore durante il login');
    }
}

function toggleLoginForm() {
    const loginSection = document.getElementById('loginSection');
    loginSection.style.display = loginSection.style.display === 'none' ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loginLink').addEventListener('click', (e) => {
        e.preventDefault();
        toggleLoginForm();
    });
});

function toggleRegisterForm() {
    const registerSection = document.getElementById('registerSection');
    registerSection.style.display = registerSection.style.display === 'none' ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('registerLink').addEventListener('click', (e) => {
        e.preventDefault();
        toggleRegisterForm();
    });
});

// Funzione helper per le chiamate API
async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        mode: 'cors',
        credentials: isProduction ? 'omit' : 'include'
    };

    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, finalOptions);
        return await response.json();
    } catch (error) {
        console.error('Errore nella chiamata API:', error);
        throw error;
    }
}
