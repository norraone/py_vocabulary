from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restful import Api, Resource
from database import Database
import jwt
import datetime

app = Flask(__name__)
CORS(app)
api = Api(app)

# JWT配置
app.config['SECRET_KEY'] = 'your-secret-key'  # 在生产环境中应该使用环境变量

db = Database()

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
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return {'message': 'Missing username or password'}, 400

        user_id = db.login_user(username, password)
        if user_id:
            token = jwt.encode({
                'user_id': user_id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
            }, app.config['SECRET_KEY'])
            return {'token': token, 'user_id': user_id}
        return {'message': 'Invalid credentials'}, 401

class RegisterResource(Resource):
    def post(self):
        """用户注册"""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return {'message': 'Missing username or password'}, 400

        if db.register_user(username, password):
            return {'message': 'Registration successful'}, 201
        return {'message': 'Username already exists'}, 409

class WordResource(Resource):
    @token_required
    def get(self, current_user):
        """获取所有单词"""
        words = db.get_all_words()
        return jsonify([{
            'id': word[0],
            'word': word[1],
            'part_of_speech': word[2],
            'meaning': word[3],
            'frequency': word[4],
            'correct_times': word[5],
            'wrong_times': word[6]
        } for word in words])

class WrongWordsResource(Resource):
    @token_required
    def get(self, current_user):
        """获取错词本"""
        words = db.get_wrong_words(current_user)
        return jsonify([{
            'id': word[0],
            'word': word[1],
            'part_of_speech': word[2],
            'meaning': word[3],
            'frequency': word[4],
            'correct_times': word[5],
            'wrong_times': word[6]
        } for word in words])

class ScoreResource(Resource):
    @token_required
    def get(self, current_user):
        """获取用户成绩"""
        score = db.get_user_score(current_user)
        streak_days = db.get_streak_days(current_user)
        return {
            'score': score,
            'streak_days': streak_days
        }

class CheckinResource(Resource):
    @token_required
    def post(self, current_user):
        """用户打卡"""
        streak_days = db.get_streak_days(current_user)
        return {
            'message': 'Checkin successful',
            'streak_days': streak_days
        }

class LearningResource(Resource):
    @token_required
    def post(self, current_user):
        """提交学习结果"""
        data = request.get_json()
        word_id = data.get('word_id')
        is_correct = data.get('is_correct')

        if word_id is None or is_correct is None:
            return {'message': 'Missing word_id or is_correct'}, 400

        db.update_word_stats(word_id, is_correct)
        score_change = 10 if is_correct else -10
        db.update_user_score(current_user, score_change)
        
        return {
            'message': 'Learning record updated',
            'score_change': score_change
        }

# 注册API路由
api.add_resource(AuthResource, '/api/auth/login')
api.add_resource(RegisterResource, '/api/auth/register')
api.add_resource(WordResource, '/api/words')
api.add_resource(WrongWordsResource, '/api/words/wrong')
api.add_resource(ScoreResource, '/api/score')
api.add_resource(CheckinResource, '/api/checkin')
api.add_resource(LearningResource, '/api/learning')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
