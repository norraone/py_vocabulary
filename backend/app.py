from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restful import Api, Resource
from database import Database
import jwt
import datetime
import logging
import json
import traceback

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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
app.config['SECRET_KEY'] = 'your-secret-key'  # 在生产环境中应该使用环境变量

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
    
    return {'message': 'Internal server error', 'error': str(error)}, 500

def token_required(f):
    """JWT token验证装饰器"""
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return {'message': 'Token is missing'}, 401
        try:
            token = token.split(' ')[1]  # Bearer token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['user_id']
        except:
            return {'message': 'Token is invalid'}, 401
        return f(current_user, *args, **kwargs)
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
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
                }, app.config['SECRET_KEY'])
                logger.info("Login successful for user: %s", username)
                return {'token': token, 'user_id': user_id}
            logger.warning("Invalid credentials for user: %s", username)
            return {'message': 'Invalid credentials'}, 401
            
        except Exception as e:
            logger.error("Error during login: %s", str(e), exc_info=True)
            return {'message': 'Internal server error'}, 500

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
            return {'message': 'Internal server error'}, 500

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
            return {'message': 'Internal server error'}, 500

class WrongWordsResource(Resource):
    @token_required
    def get(self, current_user):
        """获取错词本"""
        try:
            words = db.get_wrong_words(current_user)
            logger.info("Fetched wrong words for user: %s", current_user)
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
            logger.error("Error during fetching wrong words: %s", str(e), exc_info=True)
            return {'message': 'Internal server error'}, 500

class ScoreResource(Resource):
    @token_required
    def get(self, current_user):
        """获取用户成绩"""
        try:
            score = db.get_user_score(current_user)
            streak_days = db.get_streak_days(current_user)
            logger.info("Fetched score for user: %s", current_user)
            return {
                'score': score,
                'streak_days': streak_days
            }
            
        except Exception as e:
            logger.error("Error during fetching score: %s", str(e), exc_info=True)
            return {'message': 'Internal server error'}, 500

class CheckinResource(Resource):
    @token_required
    def post(self, current_user):
        """用户打卡"""
        try:
            streak_days = db.get_streak_days(current_user)
            logger.info("Checkin successful for user: %s", current_user)
            return {
                'message': 'Checkin successful',
                'streak_days': streak_days
            }
            
        except Exception as e:
            logger.error("Error during checkin: %s", str(e), exc_info=True)
            return {'message': 'Internal server error'}, 500

class LearningResource(Resource):
    @token_required
    def post(self, current_user):
        """提交学习结果"""
        try:
            data = request.get_json()
            logger.debug("Request data: %s", data if data else None)
            
            if not data:
                logger.error("No JSON data received")
                return {'message': 'No data provided'}, 400
                
            word_id = data.get('word_id')
            is_correct = data.get('is_correct')

            if word_id is None or is_correct is None:
                logger.error("Missing word_id or is_correct")
                return {'message': 'Missing word_id or is_correct'}, 400

            db.update_word_stats(word_id, is_correct)
            score_change = 10 if is_correct else -10
            db.update_user_score(current_user, score_change)
            logger.info("Learning record updated for user: %s", current_user)
            return {
                'message': 'Learning record updated',
                'score_change': score_change
            }
            
        except Exception as e:
            logger.error("Error during learning: %s", str(e), exc_info=True)
            return {'message': 'Internal server error'}, 500

# 注册API路由
api.add_resource(AuthResource, '/api/auth/login')
api.add_resource(RegisterResource, '/api/auth/register')
api.add_resource(WordResource, '/api/words')
api.add_resource(WrongWordsResource, '/api/words/wrong')
api.add_resource(ScoreResource, '/api/score')
api.add_resource(CheckinResource, '/api/checkin')
api.add_resource(LearningResource, '/api/learning')

if __name__ == '__main__':
    logger.info("Starting Flask server on http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
