import sqlite3
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import logging
import hashlib

# Initialize logger
logger = logging.getLogger(__name__)

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

            # 用户单词学习进度表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS word_learning_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    word_id INTEGER,
                    next_review_date DATE,
                    review_interval INTEGER DEFAULT 1,
                    ease_factor REAL DEFAULT 2.5,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (word_id) REFERENCES words (id),
                    UNIQUE(user_id, word_id)
                )
            ''')

            # 打卡记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS checkin_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    checkin_date DATE NOT NULL,
                    checkin_type TEXT NOT NULL DEFAULT 'normal',  -- normal: 正常打卡, makeup: 补打卡
                    words_learned INTEGER DEFAULT 0,
                    correct_count INTEGER DEFAULT 0,
                    wrong_count INTEGER DEFAULT 0,
                    streak_days INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, checkin_date)
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
                # 检查单词是否已存在
                cursor.execute('SELECT * FROM words WHERE word = ?', (word,))
                existing_word = cursor.fetchone()
                
                if existing_word:
                    logger.warning(f"Word already exists: {word}")
                    return False
                
                # 插入新单词
                cursor.execute(
                    'INSERT INTO words (word, part_of_speech, meaning, frequency, correct_times, wrong_times) VALUES (?, ?, ?, 0, 0, 0)',
                    (word, part_of_speech, meaning)
                )
                conn.commit()
                logger.info(f"Added new word: {word}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error adding word: {e}")
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
        """更新单词的统计信息，支持多种学习场景"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 增加总频率
                cursor.execute(
                    'UPDATE words SET frequency = frequency + 1 WHERE id = ?',
                    (word_id,)
                )
                
                # 根据正确性更新统计
                if is_correct:
                    cursor.execute(
                        'UPDATE words SET correct_times = correct_times + 1 WHERE id = ?',
                        (word_id,)
                    )
                else:
                    cursor.execute(
                        'UPDATE words SET wrong_times = wrong_times + 1 WHERE id = ?',
                        (word_id,)
                    )
                
                conn.commit()
                logger.info(f"Updated word stats for word_id {word_id}: is_correct = {is_correct}")
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Error updating word stats: {e}")
                raise

    def update_user_score(self, user_id, score_change):
        """更新用户分数"""
        # Ensure user_id and score_change are valid
        if not isinstance(user_id, int):
            raise ValueError(f"Invalid user_id: {user_id}. Must be an integer.")
        
        if not isinstance(score_change, (int, float)):
            raise ValueError(f"Invalid score_change: {score_change}. Must be a number.")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET total_score = total_score + ? WHERE id = ?',
                (int(score_change), user_id)
            )
            conn.commit()
            
            # Optional: Log score change
            logger.info(f"User {user_id} score updated by {score_change}")

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

    def get_word_details(self, word_id):
        """获取特定单词的详细信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT word, part_of_speech, meaning FROM words WHERE id = ?', (word_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'word': result[0],
                    'part_of_speech': result[1],
                    'meaning': result[2]
                }
            return None

    def get_user_by_id(self, user_id):
        """
        根据用户ID获取用户信息
        
        :param user_id: 用户ID
        :return: 用户信息字典，如果未找到则返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, username FROM users WHERE id = ?', 
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': result[0],
                        'username': result[1]
                    }
                
                logger.warning(f"No user found with ID: {user_id}")
                return None
        
        except sqlite3.Error as e:
            logger.error(f"Database error when retrieving user by ID {user_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error when retrieving user by ID {user_id}: {str(e)}")
            return None

    def calculate_next_interval(self, current_interval, ease_factor, quality):
        """
        计算下一次复习间隔
        
        :param current_interval: 当前复习间隔（天）
        :param ease_factor: 简易度因子
        :param quality: 回答质量 (0-5)
        :return: (new_interval, new_ease_factor)
        """
        if quality < 3:
            # 如果回答质量低于3，重置间隔
            return 1, max(1.3, ease_factor - 0.2)
        
        # 更新简易度因子
        new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ease_factor = max(1.3, new_ease_factor)  # 确保简易度因子不小于1.3
        
        # 计算新间隔
        if current_interval == 1:
            new_interval = 6
        elif current_interval == 6:
            new_interval = 1
        else:
            new_interval = round(current_interval * new_ease_factor)
        
        return new_interval, new_ease_factor

    def update_word_progress(self, user_id, word_id, quality):
        """
        更新单词学习进度
        
        :param user_id: 用户ID
        :param word_id: 单词ID
        :param quality: 回答质量 (0-5)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取当前进度
            cursor.execute('''
                SELECT review_interval, ease_factor 
                FROM word_learning_progress 
                WHERE user_id = ? AND word_id = ?
            ''', (user_id, word_id))
            
            result = cursor.fetchone()
            
            if result:
                current_interval, current_ease = result
            else:
                current_interval, current_ease = 1, 2.5
            
            # 计算新的间隔和简易度
            new_interval, new_ease = self.calculate_next_interval(
                current_interval, current_ease, quality
            )
            
            # 计算下次复习日期
            next_review = (datetime.now().date() + 
                         timedelta(days=new_interval))
            
            # 更新或插入进度记录
            cursor.execute('''
                INSERT INTO word_learning_progress 
                    (user_id, word_id, next_review_date, review_interval, ease_factor)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, word_id) DO UPDATE SET
                    next_review_date = excluded.next_review_date,
                    review_interval = excluded.review_interval,
                    ease_factor = excluded.ease_factor
            ''', (user_id, word_id, next_review, new_interval, new_ease))
            
            conn.commit()

    def get_words_for_review(self, user_id, limit=10):
        """
        获取需要复习的单词
        
        :param user_id: 用户ID
        :param limit: 返回单词数量限制
        :return: 需要复习的单词列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取今天需要复习的单词
            cursor.execute('''
                SELECT 
                    w.id,
                    w.word,
                    w.part_of_speech,
                    w.meaning,
                    w.correct_times,
                    w.wrong_times,
                    wlp.next_review_date,
                    wlp.review_interval
                FROM words w
                LEFT JOIN word_learning_progress wlp 
                    ON w.id = wlp.word_id AND wlp.user_id = ?
                WHERE 
                    wlp.next_review_date <= date('now')
                    OR wlp.next_review_date IS NULL
                ORDER BY 
                    CASE 
                        WHEN wlp.next_review_date IS NULL THEN 1
                        ELSE 0 
                    END,
                    wlp.next_review_date ASC
                LIMIT ?
            ''', (user_id, limit))
            
            words = cursor.fetchall()
            return [{
                'id': w[0],
                'word': w[1],
                'part_of_speech': w[2],
                'meaning': w[3],
                'correct_times': w[4],
                'wrong_times': w[5],
                'next_review': w[6],
                'review_interval': w[7]
            } for w in words]

    def get_learning_details(self, user_id):
        """获取用户学习详情"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    date(created_at) as learning_date,
                    COUNT(CASE WHEN is_new = 1 THEN 1 END) as new_words,
                    COUNT(CASE WHEN is_new = 0 THEN 1 END) as review_words,
                    AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) as correct_rate,
                    SUM(study_time) as total_study_time,
                    MAX(streak_days) as streak
                FROM learning_records
                WHERE user_id = ?
                GROUP BY date(created_at)
                ORDER BY learning_date DESC
                LIMIT 30
            ''', (user_id,))
            
            rows = cursor.fetchall()
            return [{
                'date': row[0],
                'newWords': row[1],
                'reviewWords': row[2],
                'correctRate': row[3],
                'studyTime': row[4],
                'streak': row[5]
            } for row in rows]

    def get_time_distribution(self, user_id):
        """获取用户学习时间分布"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    strftime('%H', created_at) as hour,
                    COUNT(*) as count
                FROM learning_records
                WHERE user_id = ?
                GROUP BY hour
                ORDER BY hour
            ''', (user_id,))
            
            rows = cursor.fetchall()
            return [{
                'hour': row[0],
                'count': row[1]
            } for row in rows]

    def get_mastery_distribution(self, user_id):
        """获取用户单词掌握度分布"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN correct_times = 0 THEN '未掌握'
                        WHEN correct_times <= 2 THEN '初步掌握'
                        WHEN correct_times <= 5 THEN '较好掌握'
                        ELSE '完全掌握'
                    END as mastery_level,
                    COUNT(*) as count
                FROM word_learning_progress
                WHERE user_id = ?
                GROUP BY mastery_level
                ORDER BY 
                    CASE mastery_level
                        WHEN '未掌握' THEN 1
                        WHEN '初步掌握' THEN 2
                        WHEN '较好掌握' THEN 3
                        WHEN '完全掌握' THEN 4
                    END
            ''', (user_id,))
            
            rows = cursor.fetchall()
            return [{
                'level': row[0],
                'count': row[1]
            } for row in rows]

    def get_learning_history(self, user_id, limit=50):
        """获取用户学习历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    w.word,
                    lr.is_correct,
                    lr.is_new,
                    lr.created_at,
                    w.part_of_speech,
                    w.meaning
                FROM learning_records lr
                JOIN words w ON lr.word_id = w.id
                WHERE lr.user_id = ?
                ORDER BY lr.created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            return [{
                'word': row[0],
                'isCorrect': bool(row[1]),
                'isNew': bool(row[2]),
                'timestamp': row[3],
                'partOfSpeech': row[4],
                'meaning': row[5]
            } for row in rows]

    def schedule_word_review(self, user_id, word_id, days):
        """
        安排单词复习时间
        
        :param user_id: 用户ID
        :param word_id: 单词ID
        :param days: 几天后复习
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 计算下次复习日期
            next_review = (datetime.now().date() + timedelta(days=days))
            
            # 更新或插入进度记录
            cursor.execute('''
                INSERT INTO word_learning_progress 
                    (user_id, word_id, next_review_date, review_interval, ease_factor)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, word_id) DO UPDATE SET
                    next_review_date = excluded.next_review_date,
                    review_interval = excluded.review_interval,
                    ease_factor = excluded.ease_factor
            ''', (user_id, word_id, next_review, days, 2.5))
            
            conn.commit()

    def delete_word(self, word_id):
        """删除指定ID的单词"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 删除单词
                cursor.execute('DELETE FROM words WHERE id = ?', (word_id,))
                # 删除相关的学习记录
                cursor.execute('DELETE FROM learning_records WHERE word_id = ?', (word_id,))
                # 删除单词学习进度
                cursor.execute('DELETE FROM word_learning_progress WHERE word_id = ?', (word_id,))
                
                conn.commit()
                logger.info(f"Deleted word with id {word_id}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting word: {e}")
            return False

    def get_checkin_status(self, user_id, date=None):
        """
        获取用户指定日期的打卡状态
        
        :param user_id: 用户ID
        :param date: 指定日期，默认为今天
        :return: 打卡记录信息，如果没有则返回默认状态
        """
        import logging
        from datetime import date as dt_date
        logger = logging.getLogger(__name__)

        try:
            # 如果没有提供日期，使用今天的日期
            if date is None:
                date = dt_date.today()
            else:
                date = self._parse_date(date)
            
            logger.info(f"Getting checkin status for user {user_id} on {date}")

            # 首先检查用户是否存在
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
                user_exists = cursor.fetchone()
                
                if not user_exists:
                    logger.warning(f"User {user_id} not found")
                    return None

                # 查询今日打卡记录
                cursor.execute('''
                    SELECT id, checkin_type, words_learned, correct_count, 
                           wrong_count, streak_days, created_at, checkin_date
                    FROM checkin_records 
                    WHERE user_id = ? AND checkin_date = ?
                ''', (user_id, date))
                
                result = cursor.fetchone()
                if result:
                    logger.info(f"Checkin status found for user {user_id} on {date}")
                    
                    # 解析日期
                    created_at = self._parse_date(result[6])
                    checkin_date = self._parse_date(result[7])
                    
                    return {
                        'id': result[0],
                        'checkin_type': result[1],
                        'words_learned': result[2],
                        'correct_count': result[3],
                        'wrong_count': result[4],
                        'streak_days': result[5],
                        'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else None,
                        'checkin_date': checkin_date.strftime('%Y-%m-%d') if checkin_date else None
                    }
                
                # 如果没有今日打卡记录，返回默认状态
                logger.info(f"No checkin status found for user {user_id} on {date}")
                return {
                    'checkin_type': 'not_checked_in',
                    'words_learned': 0,
                    'correct_count': 0,
                    'wrong_count': 0,
                    'streak_days': 0,
                    'created_at': None,
                    'checkin_date': date.strftime('%Y-%m-%d')
                }
        
        except Exception as e:
            logger.error(f"Error getting checkin status for user {user_id} on {date}: {str(e)}", exc_info=True)
            raise

    def get_checkin_stats(self, user_id):
        """
        获取用户的打卡统计信息
        
        :param user_id: 用户ID
        :return: 打卡统计信息，如果没有记录则返回默认状态
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"Getting checkin stats for user {user_id}")

            # 首先检查用户是否存在
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
                user_exists = cursor.fetchone()
                
                if not user_exists:
                    logger.warning(f"User {user_id} not found")
                    return None

                # 获取总打卡天数
                cursor.execute('''
                    SELECT COUNT(DISTINCT checkin_date) 
                    FROM checkin_records 
                    WHERE user_id = ?
                ''', (user_id,))
                total_days_result = cursor.fetchone()
                total_days = total_days_result[0] if total_days_result else 0
                
                # 获取最长连续打卡天数
                cursor.execute('''
                    SELECT MAX(streak_days) 
                    FROM checkin_records 
                    WHERE user_id = ?
                ''', (user_id,))
                max_streak_result = cursor.fetchone()
                max_streak = max_streak_result[0] if max_streak_result else 0
                
                # 获取当前连续打卡天数和最后打卡日期
                cursor.execute('''
                    SELECT streak_days, checkin_date
                    FROM checkin_records 
                    WHERE user_id = ? 
                    ORDER BY checkin_date DESC 
                    LIMIT 1
                ''', (user_id,))
                last_record = cursor.fetchone()
                
                current_streak = last_record[0] if last_record else 0
                last_checkin_date = self._parse_date(last_record[1]) if last_record else None
                
                logger.info(f"Checkin stats for user {user_id}: total_days={total_days}, max_streak={max_streak}, current_streak={current_streak}")
                
                return {
                    'total_days': total_days,
                    'max_streak': max_streak,
                    'current_streak': current_streak,
                    'last_checkin': last_checkin_date.strftime('%Y-%m-%d') if last_checkin_date else None
                }
        
        except Exception as e:
            logger.error(f"Error getting checkin stats for user {user_id}: {str(e)}", exc_info=True)
            raise

    def submit_checkin(self, user_id, checkin_date=None, checkin_type='normal'):
        """
        提交打卡记录
        
        :param user_id: 用户ID
        :param checkin_date: 打卡日期，默认为今天
        :param checkin_type: 打卡类型（normal/makeup）
        :return: 打卡记录信息
        """
        import logging
        logger = logging.getLogger(__name__)

        if checkin_date is None:
            checkin_date = date.today()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 检查是否已经打卡
                cursor.execute('''
                    SELECT id FROM checkin_records 
                    WHERE user_id = ? AND checkin_date = ?
                ''', (user_id, checkin_date))
                
                if cursor.fetchone():
                    logger.warning(f"User {user_id} already checked in on {checkin_date}")
                    raise Exception('今日已打卡')
                
                # 获取今日学习数据
                cursor.execute('''
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct,
                           SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as wrong
                    FROM learning_records
                    WHERE user_id = ? AND date = ?
                ''', (user_id, checkin_date))
                
                stats = cursor.fetchone()
                logger.info(f"Learning stats for user {user_id} on {checkin_date}: {stats}")
                
                words_learned = stats[0] or 0
                correct_count = stats[1] or 0
                wrong_count = stats[2] or 0
                
                # 计算连续打卡天数
                cursor.execute('''
                    SELECT checkin_date, streak_days 
                    FROM checkin_records 
                    WHERE user_id = ? 
                    ORDER BY checkin_date DESC 
                    LIMIT 1
                ''', (user_id,))
                
                last_record = cursor.fetchone()
                streak_days = 1
                
                if last_record:
                    last_date = datetime.strptime(last_record[0], '%Y-%m-%d').date()
                    logger.info(f"Last checkin date: {last_date}, Current checkin date: {checkin_date}")
                    
                    if (checkin_date - last_date).days == 1:
                        # 连续打卡
                        streak_days = last_record[1] + 1
                    elif (checkin_date - last_date).days > 1 and checkin_type == 'makeup':
                        # 补打卡，连续天数延续
                        streak_days = last_record[1] + 1
                
                logger.info(f"Calculated streak days: {streak_days}")
                
                # 插入打卡记录
                cursor.execute('''
                    INSERT INTO checkin_records 
                        (user_id, checkin_date, checkin_type, words_learned, 
                         correct_count, wrong_count, streak_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, checkin_date, checkin_type, words_learned,
                      correct_count, wrong_count, streak_days))
                
                conn.commit()
                
                logger.info(f"Checkin successful for user {user_id} on {checkin_date}")
                
                return {
                    'checkin_date': checkin_date.strftime('%Y-%m-%d'),  # 转换为字符串
                    'checkin_type': checkin_type,
                    'words_learned': words_learned,
                    'correct_count': correct_count,
                    'wrong_count': wrong_count,
                    'streak_days': streak_days
                }
            
            except Exception as e:
                logger.error(f"Error in submit_checkin: {str(e)}")
                conn.rollback()
                raise

    def debug_checkin_records(self, user_id):
        """
        调试方法：检查用户的打卡记录
        
        :param user_id: 用户ID
        :return: 打卡记录详情
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"Debugging checkin records for user {user_id}")

            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否有任何打卡记录
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM checkin_records 
                    WHERE user_id = ?
                ''', (user_id,))
                total_records = cursor.fetchone()[0]
                logger.info(f"Total checkin records for user {user_id}: {total_records}")

                # 获取最近的打卡记录
                cursor.execute('''
                    SELECT id, user_id, checkin_date, checkin_type, words_learned, 
                           correct_count, wrong_count, streak_days, created_at
                    FROM checkin_records 
                    WHERE user_id = ?
                    ORDER BY checkin_date DESC
                    LIMIT 5
                ''', (user_id,))
                recent_records = cursor.fetchall()

                # 格式化最近记录
                formatted_records = []
                for record in recent_records:
                    formatted_records.append({
                        'id': record[0],
                        'user_id': record[1],
                        'checkin_date': record[2].strftime('%Y-%m-%d') if record[2] else None,
                        'checkin_type': record[3],
                        'words_learned': record[4],
                        'correct_count': record[5],
                        'wrong_count': record[6],
                        'streak_days': record[7],
                        'created_at': record[8].strftime('%Y-%m-%d %H:%M:%S') if record[8] else None
                    })

                return {
                    'total_records': total_records,
                    'recent_records': formatted_records
                }
        
        except Exception as e:
            logger.error(f"Error debugging checkin records for user {user_id}: {str(e)}", exc_info=True)
            raise

    def reset_user_checkin_progress(self, user_id):
        """
        重置用户的打卡进度
        
        :param user_id: 用户ID
        :return: 重置是否成功
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除用户的所有打卡记录
                cursor.execute('''
                    DELETE FROM checkin_records 
                    WHERE user_id = ?
                ''', (user_id,))
                
                # 提交事务
                conn.commit()
                
                logger.info(f"Successfully reset checkin progress for user {user_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error resetting checkin progress for user {user_id}: {str(e)}", exc_info=True)
            return False

    def _parse_date(self, date_value):
        """
        将不同格式的日期转换为日期对象
        
        :param date_value: 日期值，可以是字符串或日期对象
        :return: 日期对象或None
        """
        import logging
        from datetime import datetime, date

        logger = logging.getLogger(__name__)

        try:
            if date_value is None:
                return None
            
            if isinstance(date_value, date):
                return date_value
            
            if isinstance(date_value, datetime):
                return date_value.date()
            
            if isinstance(date_value, str):
                # 尝试多种日期格式
                date_formats = [
                    '%Y-%m-%d',  # 最常见的格式
                    '%Y/%m/%d',
                    '%d-%m-%Y',
                    '%d/%m/%Y',
                    '%Y-%m-%d %H:%M:%S'  # 带时间的格式
                ]
                
                for fmt in date_formats:
                    try:
                        return datetime.strptime(date_value, fmt).date()
                    except ValueError:
                        continue
                
                logger.warning(f"Unable to parse date: {date_value}")
                return None
            
            logger.warning(f"Unsupported date type: {type(date_value)}")
            return None
        
        except Exception as e:
            logger.error(f"Error parsing date {date_value}: {str(e)}")
            return None

    def debug_checkin_records(self, user_id):
        """
        调试方法：检查用户的打卡记录
        
        :param user_id: 用户ID
        :return: 打卡记录详情
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"Debugging checkin records for user {user_id}")

            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否有任何打卡记录
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM checkin_records 
                    WHERE user_id = ?
                ''', (user_id,))
                total_records = cursor.fetchone()[0]
                logger.info(f"Total checkin records for user {user_id}: {total_records}")

                # 获取最近的打卡记录
                cursor.execute('''
                    SELECT id, user_id, checkin_date, checkin_type, words_learned, 
                           correct_count, wrong_count, streak_days, created_at
                    FROM checkin_records 
                    WHERE user_id = ?
                    ORDER BY checkin_date DESC
                    LIMIT 5
                ''', (user_id,))
                recent_records = cursor.fetchall()

                # 格式化最近记录
                formatted_records = []
                for record in recent_records:
                    checkin_date = self._parse_date(record[2])
                    created_at = self._parse_date(record[8])
                    
                    formatted_records.append({
                        'id': record[0],
                        'user_id': record[1],
                        'checkin_date': checkin_date.strftime('%Y-%m-%d') if checkin_date else None,
                        'checkin_type': record[3],
                        'words_learned': record[4],
                        'correct_count': record[5],
                        'wrong_count': record[6],
                        'streak_days': record[7],
                        'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else None
                    })

                return {
                    'total_records': total_records,
                    'recent_records': formatted_records
                }
        
        except Exception as e:
            logger.error(f"Error debugging checkin records for user {user_id}: {str(e)}", exc_info=True)
            raise
