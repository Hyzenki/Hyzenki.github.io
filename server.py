from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from functools import wraps
import sqlite3
import jwt
import datetime
import logging
import os
import bcrypt

app = Flask(__name__)
port = int(os.environ.get("PORT", 5000))

CORS(app, resources={
    r"/api/*": {
        "origins": [
            "null",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "https://hyzenki.github.io"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True
    }
})

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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Crea tabella matches se non esiste
            conn.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    winner_id INTEGER,
                    loser_id INTEGER,
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

def calculate_points_change(winner_points, loser_points):
    # Punti base
    base_points = 25
    
    # Calcola la differenza di punti
    points_diff = abs(winner_points - loser_points)
    ratio = min(points_diff ,base_points*1.5)  # Limita il bonus/malus al 150%
  
    
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
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION)
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
    @wraps(f)
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

            points = calculate_points_change(winner_points, loser_points)

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
                INSERT INTO matches (winner_id, loser_id, winner_points_change, loser_points_change)
                VALUES (?, ?, ?, ?)
            ''', (winner_id, loser_id, points['won'], points['lost']))

            return jsonify({
                'success': True,
                'pointsExchange': points
            })

    except Exception as e:
        logger.error(f"Errore nella registrazione del match: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register_user():
    auth_token = request.headers.get('Authorization')
    if not auth_token or 'admin-token' not in auth_token:
        return jsonify({
            'success': False,
            'error': 'Solo gli admin possono registrare nuovi utenti'
        }), 401

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_trusted = data.get('is_trusted', True)

    # Hash della password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT INTO users (username, password_hash, is_trusted)
                VALUES (?, ?, ?)
            ''', (username, hashed_password, is_trusted))
            
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
                    m.id,
                    m.match_date,
                    m.winner_id,
                    m.loser_id,
                    m.winner_points_change,
                    m.loser_points_change,
                    w.name as winner_name,
                    l.name as loser_name
                FROM matches m
                JOIN players w ON m.winner_id = w.id
                JOIN players l ON m.loser_id = l.id
                WHERE w.name = ? OR l.name = ?
                ORDER BY m.match_date DESC
            ''', (player_name, player_name))
            
            matches = cursor.fetchall()
            
            formatted_matches = [{
                'id': match[0],
                'date': match[1],
                'winner': match[6],
                'loser': match[7],
                'winner_points_change': match[4],
                'loser_points_change': match[5]
            } for match in matches]
            
            return jsonify({
                'success': True,
                'matches': formatted_matches
            })
            
    except Exception as e:
        logger.error(f"Errore nel recupero dello storico: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': 'PLDG ATP Rankings API'
    })


@app.route('/api/match/<int:match_id>', methods=['DELETE', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@require_auth
def delete_match(match_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Verifica che l'utente sia autenticato
        if not request.user:
            return jsonify({
                'success': False, 
                'error': 'Devi effettuare il login per eliminare le partite'
            }), 401

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Ottieni i dettagli del match
            cursor.execute('''
                SELECT winner_id, loser_id, winner_points_change, loser_points_change
                FROM matches
                WHERE id = ?
            ''', (match_id,))
            
            match = cursor.fetchone()
            if not match:
                return jsonify({'success': False, 'error': 'Partita non trovata'}), 404
                
            winner_id, loser_id, winner_points, loser_points = match
            
            # Ripristina i punti e le statistiche dei giocatori
            conn.execute('''
                UPDATE players 
                SET points = points - ?, matches_won = matches_won - 1 
                WHERE id = ?
            ''', (winner_points, winner_id))
            
            conn.execute('''
                UPDATE players 
                SET points = points + ?, matches_lost = matches_lost - 1 
                WHERE id = ?
            ''', (loser_points, loser_id))
            
            # Elimina il match
            conn.execute('DELETE FROM matches WHERE id = ?', (match_id,))
            
            return jsonify({'success': True})
            
    except Exception as e:
        logger.error(f"Errore nell'eliminazione del match: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)