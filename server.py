from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
import os
import logging
import jwt
import bcrypt
from datetime import datetime, timedelta

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "null"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

DB_PATH = 'tennis.db'

# Chiave segreta per JWT
JWT_SECRET = 'your-secret-key'  # In produzione, usa una chiave sicura e salvala in env vars
JWT_EXPIRATION = 24  # ore

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Crea tabella users se non esiste
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    is_trusted BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Crea tabella players se non esiste
            conn.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    points REAL DEFAULT 1200,
                    matches_won INTEGER DEFAULT 0,
                    matches_lost INTEGER DEFAULT 0,
                    matches_drawn INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Crea tabella matches se non esiste
            conn.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    winner_id INTEGER,
                    loser_id INTEGER,
                    is_draw BOOLEAN DEFAULT 0,
                    winner_points_change INTEGER,
                    loser_points_change INTEGER,
                    match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (winner_id) REFERENCES players (id),
                    FOREIGN KEY (loser_id) REFERENCES players (id)
                )
            ''')
            
            # Crea admin se non esiste
            cursor = conn.execute('SELECT id FROM users WHERE username = ?', ('admin',))
            if not cursor.fetchone():
                password = 'admin'
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                conn.execute('''
                    INSERT INTO users (username, password_hash, is_admin)
                    VALUES (?, ?, ?)
                ''', ('admin', password_hash, True))
                
            logger.info("Database inizializzato con successo")
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione del database: {str(e)}")
        raise

def calculate_points_change(winner_points, loser_points, is_draw=False):
    # Punti base
    base_points = 25
    base_draw_points = 15
    
    # Calcola la differenza di punti
    points_diff = abs(winner_points - loser_points)
    ratio = min(points_diff / 400, 1.5)  # Limita il bonus/malus al 150%
    
    if is_draw:
        # In caso di pareggio
        if winner_points > loser_points:
            # Il giocatore più debole (loser) ottiene un bonus
            return {
                'won': round(base_draw_points),  # Per il più forte
                'lost': round(base_draw_points * (1 + ratio * 0.3))  # Per il più debole (+30% max)
            }
        else:
            return {
                'won': round(base_draw_points * (1 + ratio * 0.3)),  # Per il più debole (+30% max)
                'lost': round(base_draw_points)  # Per il più forte
            }
    
    # In caso di vittoria/sconfitta
    if winner_points < loser_points:
        # Upset: il più debole ha battuto il più forte
        points_won = round(base_points * (1 + ratio))  # Bonus per vittoria contro più forte (+150% max)
        points_lost = round(base_points * (1 + ratio * 0.5))  # Penalità maggiore per sconfitta (+75% max)
    else:
        # Risultato atteso: il più forte ha battuto il più debole
        points_won = round(base_points * max(0.5, 1 - (ratio * 0.3)))  # Meno punti (-30% min)
        points_lost = round(base_points * max(0.5, 1 - (ratio * 0.3)))  # Meno punti persi
    
    return {
        'won': points_won,
        'lost': points_lost
    }

def generate_token(user_id, is_admin):
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION)
    return jwt.encode(
        {
            'user_id': user_id,
            'is_admin': is_admin,
            'exp': expiration
        },
        JWT_SECRET,
        algorithm='HS256'
    )

def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route('/api/rankings', methods=['GET'])
def get_rankings():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''
                SELECT * FROM players 
                ORDER BY points DESC
            ''')
            players = [
                {
                    'name': row[1],
                    'points': row[2],
                    'matches_won': row[3],
                    'matches_lost': row[4],
                    'matches_drawn': row[5]
                }
                for row in cursor.fetchall()
            ]
            return jsonify({'success': True, 'data': players})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''
                SELECT id, password_hash, is_admin 
                FROM users 
                WHERE username = ?
            ''', (username,))
            user = cursor.fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user[1]):
                token = generate_token(user[0], user[2])
                return jsonify({
                    'success': True,
                    'token': token,
                    'is_admin': bool(user[2])
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Credenziali non valide'
                }), 401
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500

def require_auth(f):
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token mancante'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token non valido'}), 401
        
        request.user = payload
        return f(*args, **kwargs)
    return decorated

@app.route('/api/match', methods=['POST'])
@require_auth
def record_match():
    try:
        data = request.get_json()
        winner = data['winner']
        loser = data['loser']
        is_draw = data.get('draw', False)

        with sqlite3.connect(DB_PATH) as conn:
            # Inserisci o ignora i nuovi giocatori
            conn.execute('INSERT OR IGNORE INTO players (name, points) VALUES (?, 1200)', (winner,))
            conn.execute('INSERT OR IGNORE INTO players (name, points) VALUES (?, 1200)', (loser,))
            
            # Ottieni i punteggi attuali
            cursor = conn.execute('SELECT id, points FROM players WHERE name = ?', (winner,))
            winner_data = cursor.fetchone()
            cursor = conn.execute('SELECT id, points FROM players WHERE name = ?', (loser,))
            loser_data = cursor.fetchone()

            winner_id, winner_points = winner_data
            loser_id, loser_points = loser_data

            # Calcola i punti da scambiare
            points = calculate_points_change(winner_points, loser_points, is_draw)

            if is_draw:
                # Aggiorna i punti per il pareggio
                conn.execute('''
                    UPDATE players 
                    SET points = points + ?, matches_drawn = matches_drawn + 1 
                    WHERE id = ?
                ''', (points['won'], winner_id))
                
                conn.execute('''
                    UPDATE players 
                    SET points = points + ?, matches_drawn = matches_drawn + 1 
                    WHERE id = ?
                ''', (points['lost'], loser_id))
            else:
                # Aggiorna i punti per vittoria/sconfitta
                conn.execute('''
                    UPDATE players 
                    SET points = points + ?, matches_won = matches_won + 1 
                    WHERE id = ?
                ''', (points['won'], winner_id))
                
                conn.execute('''
                    UPDATE players 
                    SET points = MAX(0, points - ?), matches_lost = matches_lost + 1 
                    WHERE id = ?
                ''', (points['lost'], loser_id))

            # Registra il match
            conn.execute('''
                INSERT INTO matches (winner_id, loser_id, is_draw, winner_points_change, loser_points_change)
                VALUES (?, ?, ?, ?, ?)
            ''', (winner_id, loser_id, is_draw, points['won'], points['lost']))

            # Aggiorna la classifica
            cursor = conn.execute('SELECT * FROM players ORDER BY points DESC')
            rankings = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'pointsExchange': points,
                'data': [{
                    'name': row[1],
                    'points': row[2],
                    'matches_won': row[3],
                    'matches_lost': row[4],
                    'matches_drawn': row[5]
                } for row in rankings]
            })

    except Exception as e:
        print(f"Errore: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register_user():
    # Verifica che la richiesta provenga da un admin
    auth_token = request.headers.get('Authorization')
    if not auth_token or 'admin-token' not in auth_token:
        return jsonify({
            'success': False,
            'error': 'Solo gli admin possono registrare nuovi utenti'
        }), 401

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_trusted = data.get('is_trusted', True)  # Default a True per utenti affidati

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT INTO users (username, password, is_trusted)
                VALUES (?, ?, ?)
            ''', (username, password, is_trusted))
            
        return jsonify({
            'success': True,
            'message': 'Utente registrato con successo'
        })
    except sqlite3.IntegrityError:
        return jsonify({
            'success': False,
            'error': 'Username già in uso'
        }), 400

def is_trusted_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute('SELECT is_trusted FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return bool(result and result[0])

@app.route('/api/player/<player_name>/history')
def get_player_history(player_name):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    m.match_date, 
                    w.name as winner_name, 
                    l.name as loser_name, 
                    m.winner_points_change, 
                    m.loser_points_change,
                    m.is_draw
                FROM matches m
                JOIN players w ON m.winner_id = w.id
                JOIN players l ON m.loser_id = l.id
                WHERE w.name = ? OR l.name = ?
                ORDER BY m.match_date DESC
            ''', (player_name, player_name))
            
            matches = cursor.fetchall()
            logger.info(f"Trovate {len(matches)} partite per {player_name}")
            
            formatted_matches = []
            for match in matches:
                formatted_match = {
                    'date': match[0],
                    'winner': match[1],
                    'loser': match[2],
                    'points_gained': match[3] if match[1] == player_name else match[4],
                    'points_lost': match[4] if match[1] == player_name else match[3],
                    'is_draw': bool(match[5])
                }
                formatted_matches.append(formatted_match)

            logger.info(f"Dati partite: {formatted_matches}")
            return jsonify({
                'success': True,
                'matches': formatted_matches
            })
            
    except Exception as e:
        logger.error(f"Errore nel recupero dello storico: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)