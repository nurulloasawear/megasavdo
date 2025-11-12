# blog_service/repository.py
from db import BlogDatabase
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)
db = BlogDatabase()

# ========================
# CATEGORIES
# ========================
def get_categories() -> List[Dict]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, slug FROM categories ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

def create_category(name: str, slug: str, description: str = "") -> int:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name, slug, description) VALUES (?, ?, ?)", (name, slug, description))
        return cursor.lastrowid

# ========================
# TAGS
# ========================
def get_tags() -> List[Dict]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, slug FROM tags ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

# ========================
# POSTS
# ========================
def create_post(data: Dict) -> int:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO posts 
            (title, slug, content, excerpt, image_url, author_id, category_id, 
             is_published, published_at, meta_title, meta_description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['title'], data['slug'], data['content'], data.get('excerpt'),
            data.get('image_url'), data['author_id'], data.get('category_id'),
            data.get('is_published', 0), data.get('published_at'),
            data.get('meta_title'), data.get('meta_description')
        ))
        post_id = cursor.lastrowid

        # Tags
        if data.get('tag_ids'):
            conn.executemany("INSERT OR IGNORE INTO post_tags (post_id, tag_id) VALUES (?, ?)",
                             [(post_id, tid) for tid in data['tag_ids']])
        return post_id

def get_post_by_slug(slug: str) -> Optional[Dict]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, c.name as category_name, u.username
            FROM posts p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN users u ON p.author_id = u.id
            WHERE p.slug = ? AND p.is_published = 1
        """, (slug,))
        row = cursor.fetchone()
        if not row:
            return None
        post = dict(row)

        # Tags
        cursor.execute("""
            SELECT t.id, t.name, t.slug FROM tags t
            JOIN post_tags pt ON t.id = pt.tag_id
            WHERE pt.post_id = ?
        """, (post['id'],))
        post['tags'] = [dict(r) for r in cursor.fetchall()]

        # View count
        conn.execute("UPDATE posts SET view_count = view_count + 1 WHERE id = ?", (post['id'],))
        return post

def get_posts(page: int = 1, limit: int = 10, category: str = None, tag: str = None) -> List[Dict]:
    offset = (page - 1) * limit
    query = """
        SELECT p.id, p.title, p.slug, p.excerpt, p.image_url, p.published_at, 
               c.name as category_name, u.username
        FROM posts p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN users u ON p.author_id = u.id
        WHERE p.is_published = 1
    """
    params = []

    if category:
        query += " AND c.slug = ?"
        params.append(category)
    if tag:
        query += " AND p.id IN (SELECT post_id FROM post_tags pt JOIN tags t ON pt.tag_id = t.id WHERE t.slug = ?)"
        params.append(tag)

    query += " ORDER BY p.published_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def search_posts(q: str, limit: int = 10) -> List[Dict]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, slug, excerpt FROM posts
            WHERE is_published = 1 AND (title LIKE ? OR content LIKE ?)
            ORDER BY published_at DESC LIMIT ?
        """, (f"%{q}%", f"%{q}%", limit))
        return [dict(row) for row in cursor.fetchall()]