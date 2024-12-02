from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restful import Api, Resource
from database import Database
import jwt
import logging
import traceback
import json
import sqlite3
import functools
import datetime
from sqlalchemy import text
import os
import traceback

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 配置应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_for_development')
app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']  # 为 JWT 使用相同的密钥

# Configure CORS
CORS(app, 
     resources={
         r"/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
             "supports_credentials": True,
             "expose_headers": ["Content-Type", "Authorization"]
         }
     })

api = Api(app)

# JWT配置
# app.config['SECRET_KEY'] = 'your-secret-key'  # 在生产环境中应该使用环境变量

db = Database()

@app.before_request
def log_request_info():
    """Log detailed request information"""
    logger.debug("=" * 50)
    logger.debug("Request Details:")
    logger.debug(f"Method: {request.method}")
    logger.debug(f"URL: {request.url}")
    logger.debug(f"Headers:\n" + "\n".join(f"  {k}: {v}" for k, v in request.headers.items()))
    
    if request.data:
        try:
            # Try to parse and log JSON data
            data = json.loads(request.data)
            # Hide password in logs
            if 'password' in data:
                data['password'] = '****'
            logger.debug(f"JSON Body: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            logger.debug(f"Raw Body: {request.data}")
    
    logger.debug("=" * 50)

@app.after_request
def after_request(response):
    """Log response and add CORS headers"""
    logger.debug("=" * 50)
    logger.debug("Response Details:")
    logger.debug(f"Status: {response.status}")
    logger.debug(f"Headers:\n" + "\n".join(f"  {k}: {v}" for k, v in response.headers.items()))
    
    try:
        if response.json:
            logger.debug(f"JSON Response: {json.dumps(response.json, indent=2, ensure_ascii=False)}")
    except:
        if response.data:
            logger.debug(f"Raw Response: {response.data}")
    
    logger.debug("=" * 50)

    # Add CORS headers
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Expose-Headers', 'Content-Type,Authorization')
    
    return response

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    logger.error("=" * 50)
    logger.error("Unhandled Exception:")
    logger.error(f"Type: {type(error).__name__}")
    logger.error(f"Message: {str(error)}")
    logger.error("Traceback:")
    logger.error(traceback.format_exc())
    logger.error("=" * 50)
    
    # Additional context logging
    try:
        # Log request details if available
        logger.error("Request Details:")
        logger.error(f"Method: {request.method}")
        logger.error(f"URL: {request.url}")
        logger.error(f"Headers: {request.headers}")
        
        # Try to log request body safely
        if request.data:
            try:
                logger.error(f"Request Body: {request.data.decode('utf-8')}")
            except Exception as decode_error:
                logger.error(f"Could not decode request body: {decode_error}")
    except Exception as context_error:
        logger.error(f"Error logging request context: {context_error}")
    
    # Determine a user-friendly error message based on error type
    if isinstance(error, sqlite3.Error):
        error_message = "数据库操作错误"
    elif isinstance(error, jwt.ExpiredSignatureError):
        error_message = "认证令牌已过期"
    elif isinstance(error, jwt.InvalidTokenError):
        error_message = "无效的认证令牌"
    else:
        error_message = "服务器遇到未知错误"
    
    return {
        'message': '服务器内部错误',
        'error_type': type(error).__name__,
        'error_details': str(error),
        'user_message': error_message,
        'timestamp': datetime.datetime.now().isoformat()
    }, 500

def token_required(f):
    """JWT token验证装饰器"""
    @functools.wraps(f)
    def decorated(self, *args, **kwargs):
        token = None
        
        # 检查授权头
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            logger.warning("No token provided")
            return jsonify({
                'message': 'Authentication token is missing',
                'error_type': 'MissingToken'
            }), 401
        
        try:
            # 解码 token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # 获取用户 ID
            current_user = data.get('user_id')
            
            if not current_user:
                logger.error("Invalid token: No user ID found")
                return jsonify({
                    'message': 'Invalid token',
                    'error_type': 'InvalidToken'
                }), 401
            
            # 检查用户是否存在
            user = db.get_user_by_id(current_user)
            if not user:
                logger.warning(f"Token contains non-existent user ID: {current_user}")
                return jsonify({
                    'message': 'User not found',
                    'error_type': 'UserNotFound',
                    'user_id': current_user
                }), 401
            
            # 将用户 ID 传递给被装饰的函数
            return f(self, current_user, *args, **kwargs)
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return jsonify({
                'message': 'Token has expired',
                'error_type': 'TokenExpired'
            }), 401
        
        except jwt.InvalidTokenError:
            logger.error("Invalid token")
            return jsonify({
                'message': 'Invalid token',
                'error_type': 'InvalidToken'
            }), 401
        
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}")
            return jsonify({
                'message': 'Authentication failed',
                'error_type': 'UnexpectedError',
                'error_details': str(e)
            }), 401
    
    return decorated

class AuthResource(Resource):
    def post(self):
        """用户登录"""
        logger.info("Received login request")
        try:
            data = request.get_json()
            logger.debug("Request data: %s", {**data, 'password': '****'} if data else None)
            
            if not data:
                logger.error("No JSON data received")
                return {'message': 'No data provided'}, 400
                
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                logger.error("Missing username or password")
                return {'message': 'Missing username or password'}, 400

            user_id = db.login_user(username, password)
            if user_id:
                token = jwt.encode({
                    'user_id': user_id,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
                    'iat': datetime.datetime.utcnow()  # 签发时间
                }, app.config['SECRET_KEY'], algorithm='HS256')  # 指定算法
                logger.info("Login successful for user: %s", username)
                return {'token': token, 'user_id': user_id}
            logger.warning("Invalid credentials for user: %s", username)
            return {'message': 'Invalid credentials'}, 401
            
        except Exception as e:
            logger.error("Error during login: %s", str(e), exc_info=True)
            return {'message': 'Internal server error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

class RegisterResource(Resource):
    def post(self):
        """用户注册"""
        logger.info("Received registration request")
        try:
            data = request.get_json()
            logger.debug("Request data: %s", {**data, 'password': '****'} if data else None)
            
            if not data:
                logger.error("No JSON data received")
                return {'message': 'No data provided'}, 400
                
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                logger.error("Missing username or password")
                return {'message': 'Missing username or password'}, 400

            if db.register_user(username, password):
                logger.info("Registration successful for user: %s", username)
                return {'message': 'Registration successful'}, 201
                
            logger.warning("Username already exists: %s", username)
            return {'message': 'Username already exists'}, 409
            
        except Exception as e:
            logger.error("Error during registration: %s", str(e), exc_info=True)
            return {'message': 'Internal server error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

class WordResource(Resource):
    @token_required
    def get(self, current_user):
        """获取所有单词"""
        try:
            words = db.get_all_words()
            logger.info("Fetched all words for user: %s", current_user)
            return jsonify([{
                'id': word[0],
                'word': word[1],
                'part_of_speech': word[2],
                'meaning': word[3],
                'frequency': word[4],
                'correct_times': word[5],
                'wrong_times': word[6]
            } for word in words])
            
        except Exception as e:
            logger.error("Error during fetching words: %s", str(e), exc_info=True)
            return {'message': 'Internal server error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    @token_required
    def put(self, current_user, word_id):
        """
        更新单词信息
        """
        try:
            data = request.get_json()
            logger.debug(f"Received word update data: {data}")
            logger.debug(f"Current user: {current_user}, Word ID: {word_id}")

            # Validate input data
            if not isinstance(data, dict):
                logger.error(f"Invalid input data type: {type(data)}")
                return jsonify({
                    'message': '无效的输入数据',
                    'error_details': f'Expected dict, got {type(data)}'
                }), 400

            # Use the database method directly instead of SQLAlchemy
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, check if the word exists
                cursor.execute('SELECT * FROM words WHERE id = ?', (word_id,))
                existing_word = cursor.fetchone()
                
                if not existing_word:
                    logger.warning(f"Word not found with ID: {word_id}")
                    return jsonify({'message': 'Word not found'}), 404

                # Prepare update query
                update_fields = []
                update_values = []

                # Validate and add update fields
                if 'word' in data:
                    if not isinstance(data['word'], str):
                        logger.error(f"Invalid word type: {type(data['word'])}")
                        return jsonify({
                            'message': '单词格式错误',
                            'error_details': f'Expected str, got {type(data["word"])}'
                        }), 400
                    update_fields.append('word = ?')
                    update_values.append(data['word'])
                
                if 'part_of_speech' in data:
                    if not isinstance(data.get('part_of_speech', ''), str):
                        logger.error(f"Invalid part_of_speech type: {type(data['part_of_speech'])}")
                        return jsonify({
                            'message': '词性格式错误',
                            'error_details': f'Expected str, got {type(data["part_of_speech"])}'
                        }), 400
                    update_fields.append('part_of_speech = ?')
                    update_values.append(data['part_of_speech'])
                
                if 'meaning' in data:
                    if not isinstance(data['meaning'], str):
                        logger.error(f"Invalid meaning type: {type(data['meaning'])}")
                        return jsonify({
                            'message': '释义格式错误',
                            'error_details': f'Expected str, got {type(data["meaning"])}'
                        }), 400
                    update_fields.append('meaning = ?')
                    update_values.append(data['meaning'])

                if not update_fields:
                    logger.warning("No update fields provided")
                    return jsonify({
                        'message': '没有提供更新字段',
                        'error_details': '至少需要更新一个字段'
                    }), 400

                # Add word_id to the end of values list for WHERE clause
                update_values.append(word_id)

                # Construct and execute update query
                update_query = f"UPDATE words SET {', '.join(update_fields)} WHERE id = ?"
                logger.debug(f"Update query: {update_query}")
                logger.debug(f"Update values: {update_values}")

                cursor.execute(update_query, update_values)
                conn.commit()

                logger.info(f"Word {word_id} updated successfully")
                return jsonify({
                    'message': '单词更新成功',
                    'updated_fields': list(data.keys())
                }), 200

        except sqlite3.Error as e:
            logger.error(f"SQLite error updating word: {str(e)}")
            return jsonify({
                'message': '数据库操作错误',
                'error_details': str(e)
            }), 500
        except Exception as e:
            logger.error(f"Unexpected error updating word: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'message': '更新单词失败',
                'error_details': str(e)
            }), 500

class WrongWordsResource(Resource):
    @token_required
    def get(self, current_user):
        """获取错词本"""
        try:
            # 使用数据库连接获取错误单词
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取用户学习记录中错误次数多于正确次数的单词
                cursor.execute('''
                    SELECT DISTINCT 
                        w.id, 
                        w.word, 
                        w.part_of_speech,
                        w.meaning,
                        w.correct_times,
                        w.wrong_times,
                        w.frequency
                    FROM words w
                    JOIN learning_records lr ON w.id = lr.word_id
                    WHERE lr.user_id = ? 
                    AND w.wrong_times > w.correct_times
                    ORDER BY w.wrong_times DESC
                    LIMIT 20
                ''', (current_user,))
                
                wrong_words = cursor.fetchall()
                
                result = [
                    {
                        'id': word[0],
                        'word': word[1],
                        'part_of_speech': word[2],
                        'meaning': word[3],
                        'correct_times': word[4],
                        'wrong_times': word[5],
                        'frequency': word[6]
                    } for word in wrong_words
                ]
                
                return result, 200
        
        except Exception as e:
            logger.error(f"Error retrieving wrong words: {str(e)}")
            return {
                'message': '获取错误单词失败',
                'error': str(e),
                'error_type': type(e).__name__
            }, 500

class ScoreResource(Resource):
    @token_required
    def get(self, current_user):
        """获取用户成绩"""
        try:
            # Validate current_user is an integer
            if not isinstance(current_user, int):
                logger.error(f"Invalid current_user type: {type(current_user)}")
                return {'message': 'Authentication error', 'error': 'Invalid user ID'}, 401

            # Retrieve user score
            score = db.get_user_score(current_user)
            
            logger.info(f"Retrieved score for user {current_user}: {score}")
            
            return {
                'message': 'Score retrieved successfully',
                'score': score,
                'user_id': current_user
            }, 200
        
        except Exception as e:
            logger.error(f"Error retrieving score for user {current_user}: {str(e)}", exc_info=True)
            return {'message': 'Internal server error', 'error': str(e)}, 500

class LearningResource(Resource):
    def post(self):
        """提交学习结果"""
        try:
            # 从请求头获取 token
            token = None
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
            
            if not token:
                logger.warning("No token provided")
                return {
                    'message': 'Authentication token is missing',
                    'error_type': 'MissingToken'
                }, 401
            
            try:
                # 解码 token
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                
                # 获取用户 ID
                current_user = data.get('user_id')
                
                # 确保 current_user 是整数
                if not isinstance(current_user, int):
                    try:
                        current_user = int(current_user)
                    except (ValueError, TypeError):
                        logger.error(f"Invalid user ID type: {type(current_user)}")
                        return {
                            'message': 'Invalid user ID',
                            'error_type': 'InvalidUserID',
                            'current_user_type': str(type(current_user))
                        }, 401
                
                if not current_user:
                    logger.error("Invalid token: No user ID found")
                    return {
                        'message': 'Invalid token',
                        'error_type': 'InvalidToken'
                    }, 401
                
                # 验证用户是否存在
                user = db.get_user_by_id(current_user)
                if not user:
                    logger.warning(f"Token contains non-existent user ID: {current_user}")
                    return {
                        'message': 'User not found',
                        'error_type': 'UserNotFound',
                        'user_id': current_user
                    }, 401
                
                # Parse request data
                request_data = request.get_json()
                logger.debug(f"Received learning data: {request_data}")

                # Validate word_id
                word_id = request_data.get('word_id')
                if not word_id:
                    logger.error("Missing word_id")
                    return {
                        'message': 'Missing word_id', 
                        'error': 'word_id is required',
                        'error_type': 'MissingWordID'
                    }, 400
                
                # Ensure word_id is an integer
                try:
                    word_id = int(word_id)
                except ValueError:
                    logger.error(f"Invalid word_id: {word_id}")
                    return {
                        'message': 'Invalid word_id', 
                        'error': 'word_id must be an integer',
                        'error_type': 'InvalidWordID'
                    }, 400

                # Validate is_correct
                is_correct = request_data.get('is_correct')
                if is_correct is None:
                    logger.error("Missing is_correct")
                    return {
                        'message': 'Missing is_correct', 
                        'error': 'is_correct is required',
                        'error_type': 'MissingIsCorrect'
                    }, 400
                
                # Validate is_correct is a boolean
                if not isinstance(is_correct, bool):
                    logger.error(f"Invalid is_correct: {is_correct}")
                    return {
                        'message': 'Invalid is_correct', 
                        'error': 'is_correct must be a boolean',
                        'error_type': 'InvalidIsCorrect'
                    }, 400

                # Additional database validation
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    # Check if word exists
                    cursor.execute('SELECT id FROM words WHERE id = ?', (word_id,))
                    if not cursor.fetchone():
                        logger.error(f"Word not found: {word_id}")
                        return {
                            'message': 'Word not found', 
                            'error': f'No word exists with id {word_id}',
                            'error_type': 'WordNotFound'
                        }, 404

                # Proceed with learning record update
                db.update_word_stats(word_id, is_correct)
                
                # Calculate score change
                score_change = 10 if is_correct else -10
                
                # Safely update user score
                try:
                    db.update_user_score(current_user, score_change)
                except ValueError as ve:
                    logger.error(f"Score update error: {ve}")
                    return {
                        'message': 'Invalid score update', 
                        'error': str(ve),
                        'error_type': 'ScoreUpdateError'
                    }, 400
                
                # Optional: Add learning record
                db.add_learning_record(current_user, word_id, is_correct)
                
                logger.info(f"Learning record updated for user: {current_user}, word: {word_id}, correct: {is_correct}")
                
                # Retrieve word details for response
                word_details = db.get_word_details(word_id)
                
                return {
                    'message': 'Learning record updated',
                    'word_id': word_id,
                    'is_correct': is_correct,
                    'score_change': score_change,
                    'correct_word': word_details
                }, 200
            
            except jwt.ExpiredSignatureError:
                logger.warning("Token has expired")
                return {
                    'message': 'Token has expired',
                    'error_type': 'TokenExpired'
                }, 401
            
            except jwt.InvalidTokenError:
                logger.error("Invalid token")
                return {
                    'message': 'Invalid token',
                    'error_type': 'InvalidToken'
                }, 401
            
            except Exception as e:
                logger.error(f"Unexpected authentication error: {str(e)}")
                return {
                    'message': 'Authentication failed',
                    'error_type': 'UnexpectedAuthError',
                    'error_details': str(e)
                }, 401
        
        except Exception as e:
            logger.error(f"Unexpected error during learning: {str(e)}", exc_info=True)
            return {
                'message': 'Internal server error', 
                'error': str(e), 
                'traceback': traceback.format_exc(),
                'error_type': 'UnexpectedError'
            }, 500

class ResetProgressResource(Resource):
    @token_required
    def post(self, current_user):
        """
        Reset user's learning progress
        """
        try:
            # 记录重置请求
            logger.info(f"Reset progress request received for user: {current_user}")
            
            # 使用数据库连接重置进度
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. 首先获取用户学习过的单词
                cursor.execute('''
                    SELECT DISTINCT word_id 
                    FROM learning_records 
                    WHERE user_id = ?
                ''', (current_user,))
                learned_words = cursor.fetchall()
                
                # 2. 重置这些单词的统计数据
                if learned_words:
                    word_ids = [word[0] for word in learned_words]
                    placeholders = ','.join('?' * len(word_ids))
                    cursor.execute(f'''
                        UPDATE words 
                        SET correct_times = 0, wrong_times = 0 
                        WHERE id IN ({placeholders})
                    ''', word_ids)
                
                # 3. 重置单词学习记录
                cursor.execute('''
                    DELETE FROM learning_records 
                    WHERE user_id = ?
                ''', (current_user,))
                
                # 4. 重置用户分数
                cursor.execute('''
                    UPDATE users 
                    SET total_score = 0 
                    WHERE id = ?
                ''', (current_user,))
                
                # 提交所有更改
                conn.commit()
            
            # 记录重置操作
            logger.info(f"User {current_user} successfully reset their learning progress")
            
            return {
                'message': '学习进度已成功重置',
                'score': 0
            }, 200
        
        except Exception as e:
            # 详细的错误日志
            logger.error(f"Error resetting user progress for user {current_user}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                'message': '重置失败，请稍后重试',
                'error': str(e),
                'error_type': type(e).__name__
            }, 500

class LearningStatsResource(Resource):
    @token_required
    def get(self, current_user):
        """获取用户学习统计"""
        try:
            # 使用数据库连接获取学习统计
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        COUNT(DISTINCT word_id) as total_learned,
                        ROUND(AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END), 2) as correct_rate,
                        MAX(date) as last_learning_date
                    FROM learning_records
                    WHERE user_id = ?
                ''', (current_user,))
                
                stats = cursor.fetchone()
                
                result = {
                    'totalLearned': stats[0] or 0,
                    'correctRate': stats[1] or 0,
                    'lastLearningDate': stats[2]
                }
                
                return result, 200
        
        except Exception as e:
            logger.error(f"Error retrieving learning stats: {str(e)}")
            return {
                'message': '获取学习统计失败',
                'error': str(e),
                'error_type': type(e).__name__
            }, 500

class LearningTrendResource(Resource):
    @token_required
    def get(self, current_user):
        """获取用户学习趋势"""
        try:
            # 使用数据库连接获取学习趋势
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    WITH weeks AS (
                        SELECT 
                            strftime('%Y-%W', date) AS week,
                            COUNT(DISTINCT word_id) AS words_learned,
                            ROUND(AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END), 2) AS weekly_accuracy
                        FROM learning_records
                        WHERE user_id = ?
                        GROUP BY week
                        ORDER BY week DESC
                        LIMIT 4
                    )
                    SELECT 
                        week, 
                        words_learned, 
                        weekly_accuracy
                    FROM weeks
                    ORDER BY week
                ''', (current_user,))
                
                trend_data = cursor.fetchall()
                
                result = [
                    {
                        'week': row[0],
                        'wordsLearned': row[1],
                        'accuracy': row[2]
                    } for row in trend_data
                ]
                
                return result, 200
        
        except Exception as e:
            logger.error(f"Error retrieving learning trend: {str(e)}")
            return {
                'message': '获取学习趋势失败',
                'error': str(e),
                'error_type': type(e).__name__
            }, 500

class MultipleChoiceResource(Resource):
    @token_required
    def get(self, current_user):
        """获取随机多选题"""
        try:
            # 使用数据库连接获取随机单词
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 随机选择一个单词作为正确答案
                cursor.execute('''
                    SELECT id, word, meaning 
                    FROM words 
                    ORDER BY RANDOM() 
                    LIMIT 1
                ''')
                correct_word = cursor.fetchone()
                
                if not correct_word:
                    return {
                        'message': '词库中没有单词',
                        'error_type': 'EmptyWordBank'
                    }, 404
                
                # 随机选择3个不同的单词作为干扰选项
                cursor.execute('''
                    SELECT meaning 
                    FROM words 
                    WHERE id != ? 
                    ORDER BY RANDOM() 
                    LIMIT 3
                ''', (correct_word[0],))
                
                wrong_words = cursor.fetchall()
                
                # 如果没有足够的干扰选项，返回错误
                if len(wrong_words) < 3:
                    return {
                        'message': '词库中单词数量不足',
                        'error_type': 'InsufficientWords'
                    }, 400
                
                # 构建选项列表（包含正确答案和干扰选项）
                options = [word[0] for word in wrong_words]
                options.append(correct_word[2])
                
                # 随机打乱选项顺序
                import random
                random.shuffle(options)
                
                return {
                    'id': correct_word[0],     # 添加单词ID
                    'question': correct_word[1],  # 英文单词
                    'options': options,           # 打乱后的中文选项
                    'correct_answer': correct_word[2]  # 正确的中文含义
                }, 200
                
        except Exception as e:
            logger.error(f"Error generating multiple choice question: {str(e)}")
            return {
                'message': '生成题目失败',
                'error': str(e),
                'error_type': type(e).__name__
            }, 500

class RandomWordResource(Resource):
    @token_required
    def get(self, current_user):
        """获取随机单词进行背诵"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取用户已经掌握的单词（正确次数大于错误次数的单词）
                cursor.execute('''
                    SELECT word_id
                    FROM learning_records
                    WHERE user_id = ?
                    GROUP BY word_id
                    HAVING SUM(CASE WHEN is_correct = 1 THEN 1 ELSE -1 END) > 0
                ''', (current_user,))
                mastered_words = {row[0] for row in cursor.fetchall()}
                
                # 优先选择未掌握的单词，按错误次数降序排序
                cursor.execute('''
                    SELECT 
                        w.id,
                        w.word,
                        w.part_of_speech,
                        w.meaning,
                        w.correct_times,
                        w.wrong_times
                    FROM words w
                    WHERE w.id NOT IN (
                        SELECT word_id
                        FROM learning_records
                        WHERE user_id = ?
                        GROUP BY word_id
                        HAVING SUM(CASE WHEN is_correct = 1 THEN 1 ELSE -1 END) > 0
                    )
                    ORDER BY 
                        w.wrong_times DESC,
                        RANDOM()
                    LIMIT 10
                ''', (current_user,))
                
                unmastered_words = cursor.fetchall()
                
                # 如果未掌握的单词不足10个，补充一些随机单词
                if len(unmastered_words) < 10:
                    remaining_count = 10 - len(unmastered_words)
                    cursor.execute('''
                        SELECT 
                            w.id,
                            w.word,
                            w.part_of_speech,
                            w.meaning,
                            w.correct_times,
                            w.wrong_times
                        FROM words w
                        WHERE w.id NOT IN ({})
                        ORDER BY RANDOM()
                        LIMIT ?
                    '''.format(','.join('?' * len(unmastered_words)) if unmastered_words else 'SELECT -1'),
                    tuple(word[0] for word in unmastered_words) + (remaining_count,))
                    
                    unmastered_words.extend(cursor.fetchall())
                
                # 格式化返回数据
                words_data = [{
                    'id': word[0],
                    'word': word[1],
                    'part_of_speech': word[2],
                    'meaning': word[3],
                    'correct_times': word[4],
                    'wrong_times': word[5]
                } for word in unmastered_words]
                
                return words_data, 200
                
        except Exception as e:
            logger.error(f"Error fetching random words: {str(e)}")
            return {
                'message': '获取单词失败',
                'error': str(e),
                'error_type': type(e).__name__
            }, 500

# 注册API路由
api.add_resource(AuthResource, '/api/auth/login')
api.add_resource(RegisterResource, '/api/auth/register')
api.add_resource(WordResource, '/api/words', '/api/words/<int:word_id>')
api.add_resource(WrongWordsResource, '/api/wrong-words')
api.add_resource(ScoreResource, '/api/score')
api.add_resource(LearningResource, '/api/learn')
api.add_resource(ResetProgressResource, '/api/reset')
api.add_resource(LearningStatsResource, '/api/learning-stats')
api.add_resource(LearningTrendResource, '/api/learning-trend')
api.add_resource(MultipleChoiceResource, '/api/multiple-choice')
api.add_resource(RandomWordResource, '/api/random-words')

if __name__ == '__main__':
    logger.info("Starting Flask server on http://127.0.0.1:5000")
    app.run(debug=True)
