from flask import Flask, request
from flask_cors import CORS
from flask_restful import Api, Resource
from database import Database
import jwt
import logging
import traceback
import json
import sqlite3
import functools
from datetime import datetime
from sqlalchemy import text
import os
import traceback
from datetime import date

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
        'timestamp': datetime.now().isoformat()
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
            return {
                'message': 'Authentication token is missing',
                'error_type': 'MissingToken'
            }, 401
        
        try:
            # 解码 token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # 获取用户 ID
            current_user = data.get('user_id')
            
            if not current_user:
                logger.error("Invalid token: No user ID found")
                return {
                    'message': 'Invalid token',
                    'error_type': 'InvalidToken'
                }, 401
            
            # 检查用户是否存在
            user = db.get_user_by_id(current_user)
            if not user:
                logger.warning(f"Token contains non-existent user ID: {current_user}")
                return {
                    'message': 'User not found',
                    'error_type': 'UserNotFound',
                    'user_id': current_user
                }, 401
            
            # 将用户 ID 传递给被装饰的函数
            return f(self, current_user, *args, **kwargs)
        
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
                'error_type': 'UnexpectedError',
                'error_details': str(e)
            }, 401
    
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
                    'exp': datetime.utcnow() + datetime.timedelta(days=1),
                    'iat': datetime.utcnow()  # 签发时间
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
            return [{
                'id': word[0],
                'word': word[1],
                'part_of_speech': word[2],
                'meaning': word[3],
                'frequency': word[4],
                'correct_times': word[5],
                'wrong_times': word[6]
            } for word in words]
            
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
                return {
                    'message': '无效的输入数据',
                    'error_details': f'Expected dict, got {type(data)}'
                }, 400

            # Use the database method directly instead of SQLAlchemy
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, check if the word exists
                cursor.execute('SELECT * FROM words WHERE id = ?', (word_id,))
                existing_word = cursor.fetchone()
                
                if not existing_word:
                    logger.warning(f"Word not found with ID: {word_id}")
                    return {'message': 'Word not found'}, 404

                # Prepare update query
                update_fields = []
                update_values = []

                # Validate and add update fields
                if 'word' in data:
                    if not isinstance(data['word'], str):
                        logger.error(f"Invalid word type: {type(data['word'])}")
                        return {
                            'message': '单词格式错误',
                            'error_details': f'Expected str, got {type(data["word"])}'
                        }, 400
                    update_fields.append('word = ?')
                    update_values.append(data['word'])
                
                if 'part_of_speech' in data:
                    if not isinstance(data.get('part_of_speech', ''), str):
                        logger.error(f"Invalid part_of_speech type: {type(data['part_of_speech'])}")
                        return {
                            'message': '词性格式错误',
                            'error_details': f'Expected str, got {type(data["part_of_speech"])}'
                        }, 400
                    update_fields.append('part_of_speech = ?')
                    update_values.append(data['part_of_speech'])
                
                if 'meaning' in data:
                    if not isinstance(data['meaning'], str):
                        logger.error(f"Invalid meaning type: {type(data['meaning'])}")
                        return {
                            'message': '释义格式错误',
                            'error_details': f'Expected str, got {type(data["meaning"])}'
                        }, 400
                    update_fields.append('meaning = ?')
                    update_values.append(data['meaning'])

                if not update_fields:
                    logger.warning("No update fields provided")
                    return {
                        'message': '没有提供更新字段',
                        'error_details': '至少需要更新一个字段'
                    }, 400

                # Add word_id to the end of values list for WHERE clause
                update_values.append(word_id)

                # Construct and execute update query
                update_query = f"UPDATE words SET {', '.join(update_fields)} WHERE id = ?"
                logger.debug(f"Update query: {update_query}")
                logger.debug(f"Update values: {update_values}")

                cursor.execute(update_query, update_values)
                conn.commit()

                logger.info(f"Word {word_id} updated successfully")
                return {
                    'message': '单词更新成功',
                    'updated_fields': list(data.keys())
                }, 200

        except sqlite3.Error as e:
            logger.error(f"SQLite error updating word: {str(e)}")
            return {
                'message': '数据库操作错误',
                'error_details': str(e)
            }, 500
        except Exception as e:
            logger.error(f"Unexpected error updating word: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'message': '更新单词失败',
                'error_details': str(e)
            }, 500

    @token_required
    def post(self, current_user):
        """
        添加新单词
        """
        try:
            data = request.get_json()
            logger.debug(f"Received new word data: {data}")
            logger.debug(f"Current user: {current_user}")

            # 验证输入数据
            if not isinstance(data, dict):
                logger.error(f"Invalid input data type: {type(data)}")
                return {
                    'message': '无效的输入数据',
                    'error_details': f'Expected dict, got {type(data)}'
                }, 400

            # 必填字段验证
            required_fields = ['word', 'part_of_speech', 'meaning']
            for field in required_fields:
                if field not in data or not data[field]:
                    logger.error(f"Missing required field: {field}")
                    return {
                        'message': f'缺少必填字段：{field}',
                        'error_details': f'Field {field} is required'
                    }, 400

            # 字段类型验证
            if not isinstance(data['word'], str):
                return {
                    'message': '单词格式错误',
                    'error_details': f'Expected str, got {type(data["word"])}'
                }, 400

            if not isinstance(data['part_of_speech'], str):
                return {
                    'message': '词性格式错误',
                    'error_details': f'Expected str, got {type(data["part_of_speech"])}'
                }, 400

            if not isinstance(data['meaning'], str):
                return {
                    'message': '释义格式错误',
                    'error_details': f'Expected str, got {type(data["meaning"])}'
                }, 400

            # 使用数据库方法添加单词
            result = db.add_word(
                word=data['word'], 
                part_of_speech=data['part_of_speech'], 
                meaning=data['meaning']
            )

            if result:
                # 获取最后插入的单词ID
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT last_insert_rowid()')
                    word_id = cursor.fetchone()[0]

                logger.info(f"Word added successfully: {data['word']}")
                return {
                    'message': '单词添加成功',
                    'word': {
                        'id': word_id,
                        'word': data['word'],
                        'part_of_speech': data['part_of_speech'],
                        'meaning': data['meaning']
                    }
                }, 201
            else:
                logger.warning(f"Failed to add word: {data['word']}")
                return {
                    'message': '单词添加失败',
                    'error_details': '可能是单词已存在或数据库错误'
                }, 400

        except sqlite3.Error as e:
            logger.error(f"SQLite error adding word: {str(e)}")
            return {
                'message': '数据库操作错误',
                'error_details': str(e)
            }, 500
        except Exception as e:
            logger.error(f"Unexpected error adding word: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'message': '添加单词失败',
                'error_details': str(e)
            }, 500

    @token_required
    def delete(self, current_user, word_id):
        """删除指定单词"""
        try:
            # 验证单词是否存在
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM words WHERE id = ?', (word_id,))
                word = cursor.fetchone()
                
                if not word:
                    logger.warning(f"Attempted to delete non-existent word: {word_id}")
                    return {
                        'message': '单词不存在',
                        'error_type': 'WordNotFound'
                    }, 404
            
            # 执行删除
            result = db.delete_word(word_id)
            
            if result:
                logger.info(f"User {current_user} deleted word {word_id}")
                return {
                    'message': '单词删除成功',
                    'word_id': word_id
                }, 200
            else:
                logger.error(f"Failed to delete word {word_id}")
                return {
                    'message': '删除单词失败',
                    'error_type': 'DeletionFailed'
                }, 500
        
        except Exception as e:
            logger.error(f"Unexpected error deleting word: {e}")
            return {
                'message': '服务器内部错误',
                'error_type': 'InternalServerError',
                'details': str(e)
            }, 500

class WrongWordsResource(Resource):
    @token_required
    def get(self, current_user):
        """获取错词本"""
        try:
            logger.info(f"Retrieving wrong words for user: {current_user}")
            
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
                
                logger.info(f"Found {len(wrong_words)} wrong words for user {current_user}")
                
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
                
                # 记录返回的错误单词详情
                for word in result:
                    logger.debug(f"Wrong word: {word['word']} - Wrong times: {word['wrong_times']}, Correct times: {word['correct_times']}")
                
                return result, 200
        
        except Exception as e:
            logger.error(f"Error retrieving wrong words for user {current_user}: {str(e)}")
            logger.error(traceback.format_exc())  # 打印完整的堆栈跟踪
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
    @token_required
    def post(self, current_user):
        """提交学习结果"""
        try:
            data = request.get_json()
            if not data:
                return {'message': '没有提供数据'}, 400

            word_id = data.get('word_id')
            is_correct = data.get('is_correct')

            if not word_id or is_correct is None:
                return {'message': '缺少必要参数'}, 400

            # 更新学习记录
            db.add_learning_record(current_user, word_id, is_correct)
            
            # 更新单词统计
            db.update_word_stats(word_id, is_correct)
            
            # 更新用户分数 - 根据正确性给予不同分数
            score_change = 3 if is_correct else -2
            db.update_user_score(current_user, score_change)

            return {
                'message': '学习记录已更新',
                'score_change': score_change,
                'is_correct': is_correct
            }, 200

        except Exception as e:
            logger.error(f"Error submitting learning result: {str(e)}")
            return {
                'message': '提交学习记录失败',
                'error': str(e)
            }, 500

class ResetProgressResource(Resource):
    @token_required
    def post(self, current_user):
        """重置用户的学习进度"""
        try:
            # 开始重置进度的事务
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 重置单词学习进度
                cursor.execute('DELETE FROM user_words WHERE user_id = ?', (current_user,))
                
                # 重置复习记录
                cursor.execute('DELETE FROM review_records WHERE user_id = ?', (current_user,))
                
                # 重置打卡记录
                cursor.execute('DELETE FROM checkin_records WHERE user_id = ?', (current_user,))
                
                # 重置用户统计信息
                cursor.execute('''
                    UPDATE users 
                    SET 
                        total_learned_words = 0, 
                        total_review_words = 0, 
                        total_correct_words = 0, 
                        total_wrong_words = 0,
                        current_streak = 0,
                        max_streak = 0
                    WHERE id = ?
                ''', (current_user,))
                
                # 提交事务
                conn.commit()
                
                logger.info(f"User {current_user} has reset all progress")
                
                return {
                    'message': '成功重置所有学习进度',
                    'success': True
                }, 200
        
        except Exception as e:
            logger.error(f"Error resetting progress for user {current_user}: {str(e)}", exc_info=True)
            return {
                'message': '重置进度失败',
                'error': str(e)
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

class ReviewWordsResource(Resource):
    @token_required
    def get(self, current_user):
        """获取需要复习的单词"""
        try:
            words = db.get_words_for_review(current_user)
            return {
                'message': '获取复习单词成功',
                'words': words
            }, 200
        except Exception as e:
            logger.error(f"Error getting review words: {str(e)}")
            return {
                'message': '获取复习单词失败',
                'error': str(e)
            }, 500

    @token_required
    def post(self, current_user):
        """提交复习结果"""
        try:
            data = request.get_json()
            if not data:
                return {'message': '没有提供数据'}, 400

            word_id = data.get('word_id')
            quality = data.get('quality')

            if not word_id or quality is None:
                return {'message': '缺少必要参数'}, 400

            if not isinstance(quality, int) or quality < 0 or quality > 5:
                return {'message': '质量评分必须是0-5之间的整数'}, 400

            # 更新复习进度
            db.update_word_progress(current_user, word_id, quality)
            
            # 更新学习记录
            is_correct = quality >= 3
            db.add_learning_record(current_user, word_id, is_correct)
            
            # 更新单词统计
            db.update_word_stats(word_id, is_correct)
            
            # 更新用户分数
            score_change = quality * 2  # 根据质量评分给予相应分数
            db.update_user_score(current_user, score_change)

            # 返回成功响应
            return {
                'message': '复习结果提交成功',
                'score_change': score_change,
                'is_correct': is_correct
            }, 200

        except Exception as e:
            logger.error(f"Error submitting review result: {str(e)}")
            return {
                'message': '提交复习结果失败',
                'error': str(e),
                'error_type': type(e).__name__
            }, 500

class LearningDetailsResource(Resource):
    @token_required
    def get(self, current_user):
        """获取学习详情统计数据"""
        try:
            details = db.get_learning_details(current_user)
            return {
                'message': '获取学习详情成功',
                'data': details
            }, 200
        except Exception as e:
            logger.error(f"Error getting learning details: {str(e)}")
            return {
                'message': '获取学习详情失败',
                'error': str(e)
            }, 500

class TimeDistributionResource(Resource):
    @token_required
    def get(self, current_user):
        """获取学习时间分布数据"""
        try:
            distribution = db.get_time_distribution(current_user)
            return {
                'message': '获取时间分布成功',
                'data': distribution
            }, 200
        except Exception as e:
            logger.error(f"Error getting time distribution: {str(e)}")
            return {
                'message': '获取时间分布失败',
                'error': str(e)
            }, 500

class MasteryDistributionResource(Resource):
    @token_required
    def get(self, current_user):
        """获取单词掌握度分布"""
        try:
            distribution = db.get_mastery_distribution(current_user)
            return {
                'message': '获取掌握度分布成功',
                'data': distribution
            }, 200
        except Exception as e:
            logger.error(f"Error getting mastery distribution: {str(e)}")
            return {
                'message': '获取掌握度分布失败',
                'error': str(e)
            }, 500

class LearningHistoryResource(Resource):
    @token_required
    def get(self, current_user):
        """获取学习历史记录"""
        try:
            limit = request.args.get('limit', default=50, type=int)
            history = db.get_learning_history(current_user, limit)
            return {
                'message': '获取学习历史成功',
                'data': history
            }, 200
        except Exception as e:
            logger.error(f"Error getting learning history: {str(e)}")
            return {
                'message': '获取学习历史失败',
                'error': str(e)
            }, 500

class ScheduleReviewResource(Resource):
    @token_required
    def post(self, current_user):
        """安排单词复习时间"""
        try:
            data = request.get_json()
            if not data:
                return {'message': '没有提供数据'}, 400

            word_id = data.get('word_id')
            days = data.get('days')

            if not word_id or not days:
                return {'message': '缺少必要参数'}, 400

            if not isinstance(days, int) or days < 1:
                return {'message': '天数必须是大于0的整数'}, 400

            # 安排复习时间
            db.schedule_word_review(current_user, word_id, days)
            
            return {
                'message': f'已安排{days}天后复习'
            }, 200

        except Exception as e:
            logger.error(f"Error scheduling review: {str(e)}")
            return {
                'message': '安排复习失败',
                'error': str(e)
            }, 500

class CheckinResource(Resource):
    @token_required
    def get(self, current_user):
        """获取打卡状态和统计信息"""
        try:
            logger.info(f"Fetching checkin status for user {current_user}")
            
            # 调试：检查用户的打卡记录
            try:
                debug_info = db.debug_checkin_records(current_user)
                logger.info(f"Debug checkin records: {debug_info}")
            except Exception as debug_error:
                logger.warning(f"Error in debug_checkin_records: {str(debug_error)}")
            
            # 获取今日打卡状态
            today_status = None
            try:
                today_status = db.get_checkin_status(current_user)
                logger.info(f"Today's checkin status: {today_status}")
            except Exception as status_error:
                logger.warning(f"Error getting today's checkin status: {str(status_error)}")
            
            # 获取打卡统计信息
            stats = None
            try:
                stats = db.get_checkin_stats(current_user)
                logger.info(f"Checkin stats: {stats}")
            except Exception as stats_error:
                logger.warning(f"Error getting checkin stats: {str(stats_error)}")
            
            # 如果两个方法都失败，抛出异常
            if today_status is None and stats is None:
                raise Exception(f"无法获取用户 {current_user} 的打卡信息")
            
            return {
                'message': '获取打卡信息成功',
                'today_status': today_status,
                'stats': stats
            }, 200
        except Exception as e:
            logger.error(f"Error getting checkin info for user {current_user}: {str(e)}", exc_info=True)
            return {
                'message': '获取打卡信息失败',
                'error': str(e),
                'details': traceback.format_exc()
            }, 500

    @token_required
    def post(self, current_user):
        """提交打卡"""
        try:
            data = request.get_json()
            if not data:
                logger.warning(f"User {current_user} attempted to check in with no data")
                return {'message': '没有提供数据'}, 400

            # 获取打卡日期和类型，默认为今天的正常打卡
            checkin_date_str = data.get('date')
            checkin_type = data.get('type', 'normal')

            # 如果没有提供日期，使用今天的日期
            if checkin_date_str:
                try:
                    checkin_date = datetime.strptime(checkin_date_str, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Invalid date format: {checkin_date_str}")
                    return {'message': '日期格式错误，应为YYYY-MM-DD'}, 400
            else:
                checkin_date = date.today()

            logger.info(f"User {current_user} attempting to check in on {checkin_date} with type {checkin_type}")

            # 提交打卡
            result = db.submit_checkin(current_user, checkin_date, checkin_type)
            
            return {
                'message': '打卡成功',
                'data': result
            }, 200

        except Exception as e:
            logger.error(f"Error submitting checkin for user {current_user}: {str(e)}")
            return {
                'message': str(e),  # 直接返回具体的错误信息
                'error': str(e)
            }, 400

# 注册API路由
api.add_resource(AuthResource, '/api/auth/login')
api.add_resource(RegisterResource, '/api/auth/register')
api.add_resource(WordResource, '/api/words', '/api/words/<int:word_id>')
api.add_resource(WrongWordsResource, '/api/wrong-words')
api.add_resource(ScoreResource, '/api/score')
api.add_resource(LearningResource, '/api/learn')
api.add_resource(ResetProgressResource, '/api/reset-progress')
api.add_resource(LearningStatsResource, '/api/learning-stats')
api.add_resource(LearningTrendResource, '/api/learning-trend')
api.add_resource(MultipleChoiceResource, '/api/multiple-choice')
api.add_resource(RandomWordResource, '/api/random-word')
api.add_resource(ReviewWordsResource, '/api/review-words')
api.add_resource(LearningDetailsResource, '/api/learning-details')
api.add_resource(TimeDistributionResource, '/api/time-distribution')
api.add_resource(MasteryDistributionResource, '/api/mastery-distribution')
api.add_resource(LearningHistoryResource, '/api/learning-history')
api.add_resource(ScheduleReviewResource, '/api/schedule-review')
api.add_resource(CheckinResource, '/api/checkin')

if __name__ == '__main__':
    app.run(debug=True)
