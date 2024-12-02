from database import Database

def init_database():
    db = Database('vocabulary.db')
    
    # 添加一些示例单词
    sample_words = [
        ('apple', 'n.', '苹果'),
        ('beautiful', 'adj.', '美丽的'),
        ('computer', 'n.', '计算机'),
        ('develop', 'v.', '开发，发展'),
        ('efficient', 'adj.', '高效的'),
        ('framework', 'n.', '框架'),
        ('generate', 'v.', '生成'),
        ('hardware', 'n.', '硬件'),
        ('implement', 'v.', '实现'),
        ('javascript', 'n.', 'JavaScript编程语言')
    ]
    
    for word, pos, meaning in sample_words:
        db.add_word(word, pos, meaning)
    
    print("数据库初始化完成！")
    print("已添加示例单词，现在可以注册账号并开始使用了。")

if __name__ == '__main__':
    init_database()
