# blog_service/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BlogDB")

class BlogDatabase:
    def __init__(self, db_path: str = 'blog.db'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"DB xato: {e}")
            raise
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            # 1. categories
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. tags
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. posts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    excerpt TEXT,
                    image_url TEXT,
                    author_id INTEGER NOT NULL,
                    category_id INTEGER,
                    is_published BOOLEAN DEFAULT 0,
                    published_at DATETIME,
                    meta_title TEXT,
                    meta_description TEXT,
                    view_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    FOREIGN KEY (author_id) REFERENCES users(id)
                )
            """)

            # 4. post_tags
            conn.execute("""
                CREATE TABLE IF NOT EXISTS post_tags (
                    post_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (post_id, tag_id),
                    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(is_published)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_post_tags_tag ON post_tags(tag_id)")

            # Trigger
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_post_ts
                AFTER UPDATE ON posts FOR EACH ROW
                BEGIN
                    UPDATE posts SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)