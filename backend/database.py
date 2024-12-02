import sqlite3
from datetime import datetime
from contextlib import contextmanager

class Database:
    def __init__(self, db_path='vocabulary.db'):
        """初始化数据库连接并创建必要的表"""
        self.db_path = db_path
        self._create_tables()

    @contextmanager
    def get_connection(self):
        """创建数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _create_tables(self):
        """创建所需的数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    total_score INTEGER DEFAULT 0
                )
            ''')

            # 单词表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    part_of_speech TEXT,
                    meaning TEXT NOT NULL,
                    frequency INTEGER DEFAULT 0,
                    correct_times INTEGER DEFAULT 0,
                    wrong_times INTEGER DEFAULT 0
                )
            ''')

            # 用户学习记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    word_id INTEGER,
                    is_correct BOOLEAN,
                    date DATE,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (word_id) REFERENCES words (id)
                )
            ''')

            conn.commit()

    def register_user(self, username, password):
        """注册新用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, password)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def login_user(self, username, password):
        """用户登录验证"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, password FROM users WHERE username = ?',
                (username,)
            )
            result = cursor.fetchone()
            
            if result and result[1] == password:
                return result[0]  # Return user ID
            return None

    def add_word(self, word, part_of_speech, meaning):
        """添加新单词"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO words (word, part_of_speech, meaning) VALUES (?, ?, ?)',
                    (word, part_of_speech, meaning)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_all_words(self):
        """获取所有单词"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM words')
            return cursor.fetchall()

    def get_wrong_words(self, user_id):
        """获取用户的错词本"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT w.* FROM words w
                JOIN learning_records lr ON w.id = lr.word_id
                WHERE lr.user_id = ? AND lr.is_correct = 0
            ''', (user_id,))
            return cursor.fetchall()

    def update_word_stats(self, word_id, is_correct):
        """更新单词的统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if is_correct:
                cursor.execute(
                    'UPDATE words SET frequency = frequency + 1, correct_times = correct_times + 1 WHERE id = ?',
                    (word_id,)
                )
            else:
                cursor.execute(
                    'UPDATE words SET frequency = frequency + 1, wrong_times = wrong_times + 1 WHERE id = ?',
                    (word_id,)
                )
            conn.commit()

    def update_user_score(self, user_id, score_change):
        """更新用户分数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET total_score = total_score + ? WHERE id = ?',
                (score_change, user_id)
            )
            conn.commit()

    def get_user_score(self, user_id):
        """获取用户总分"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT total_score FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0

    def add_learning_record(self, user_id, word_id, is_correct):
        """添加学习记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO learning_records (user_id, word_id, is_correct, date) VALUES (?, ?, ?, ?)',
                (user_id, word_id, is_correct, datetime.now().date())
            )
            conn.commit()
