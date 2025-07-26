import sqlite3
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path
import logging

class NewsDatabase:
    """Database manager for news analysis storage and retrieval."""
    
    def __init__(self, db_path: str = "news_checker.db"):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up logging first
        self.logger = logging.getLogger(__name__)
        
        # Create database and tables
        self._create_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        return conn
    
    def _create_tables(self):
        """Create all necessary tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main news analysis table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    news_content TEXT NOT NULL,
                    news_type TEXT NOT NULL DEFAULT 'text',
                    keywords TEXT,
                    mentioned_sources TEXT,
                    official_sources TEXT,
                    news_sources TEXT,
                    analysis_result TEXT NOT NULL,
                    credibility_score INTEGER,
                    analyzed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    total_analyses INTEGER DEFAULT 0,
                    first_analysis_date TIMESTAMP,
                    last_analysis_date TIMESTAMP,
                    average_credibility_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Source verification table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS source_verification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    source_name TEXT NOT NULL,
                    source_type TEXT,
                    verification_status TEXT,
                    verification_details TEXT,
                    verified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES news_analysis (id) ON DELETE CASCADE
                )
            ''')
            
            # Cache table for frequently accessed data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    content_hash TEXT PRIMARY KEY,
                    cached_result TEXT NOT NULL,
                    cache_type TEXT NOT NULL DEFAULT 'analysis',
                    expiry_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    execution_time_ms REAL NOT NULL,
                    success BOOLEAN NOT NULL DEFAULT 1,
                    error_details TEXT,
                    user_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_analysis_user_id ON news_analysis(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_analysis_content_hash ON news_analysis(content_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_analysis_date ON news_analysis(analyzed_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_cache_hash ON analysis_cache(content_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(operation_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_stats_user_id ON user_stats(user_id)')
            
            conn.commit()
            self.logger.info("Database tables created/verified successfully")
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash for content to detect duplicates."""
        # Normalize content for consistent hashing
        normalized = content.strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def save_analysis(self, user_id: int, news_content: str, news_type: str,
                     keywords: str, mentioned_sources: str, official_sources: List,
                     news_sources: List, analysis_result: str, credibility_score: int) -> Optional[int]:
        """
        Save a news analysis to the database.
        
        Returns:
            The ID of the saved analysis, or None if saving failed
        """
        try:
            content_hash = self._generate_content_hash(news_content)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert the analysis
                cursor.execute('''
                    INSERT OR REPLACE INTO news_analysis 
                    (user_id, content_hash, news_content, news_type, keywords, mentioned_sources,
                     official_sources, news_sources, analysis_result, credibility_score, analyzed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    content_hash,
                    news_content,
                    news_type,
                    keywords,
                    mentioned_sources,
                    json.dumps(official_sources, ensure_ascii=False),
                    json.dumps(news_sources, ensure_ascii=False),
                    analysis_result,
                    credibility_score,
                    datetime.now()
                ))
                
                analysis_id = cursor.lastrowid
                
                # Update user statistics
                self._update_user_stats(cursor, user_id, credibility_score)
                
                conn.commit()
                self.logger.info(f"Analysis saved successfully with ID: {analysis_id}")
                return analysis_id
                
        except Exception as e:
            self.logger.error(f"Error saving analysis: {e}")
            return None
    
    def _update_user_stats(self, cursor: sqlite3.Cursor, user_id: int, credibility_score: int):
        """Update user statistics."""
        # Get current stats
        cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
        stats = cursor.fetchone()
        
        current_time = datetime.now()
        
        if stats:
            # Update existing stats
            new_total = stats['total_analyses'] + 1
            new_avg = ((stats['average_credibility_score'] or 0) * stats['total_analyses'] + credibility_score) / new_total
            
            cursor.execute('''
                UPDATE user_stats 
                SET total_analyses = ?, last_analysis_date = ?, average_credibility_score = ?, updated_at = ?
                WHERE user_id = ?
            ''', (new_total, current_time, new_avg, current_time, user_id))
        else:
            # Create new stats
            cursor.execute('''
                INSERT INTO user_stats 
                (user_id, total_analyses, first_analysis_date, last_analysis_date, average_credibility_score)
                VALUES (?, 1, ?, ?, ?)
            ''', (user_id, current_time, current_time, credibility_score))
    
    def check_duplicate(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Check if content has been analyzed before.
        
        Returns:
            Analysis data if duplicate found, None otherwise
        """
        try:
            content_hash = self._generate_content_hash(content)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT analysis_result, credibility_score, analyzed_date 
                    FROM news_analysis 
                    WHERE content_hash = ? 
                    ORDER BY analyzed_date DESC 
                    LIMIT 1
                ''', (content_hash,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'analysis_result': result['analysis_result'],
                        'credibility_score': result['credibility_score'],
                        'analyzed_date': result['analyzed_date']
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"Error checking duplicate: {e}")
            return None
    
    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting user stats: {e}")
            return None
    
    def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get analysis history for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, news_type, keywords, credibility_score, analyzed_date
                    FROM news_analysis 
                    WHERE user_id = ? 
                    ORDER BY analyzed_date DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting user history: {e}")
            return []
    
    def get_analysis_by_id(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific analysis by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM news_analysis WHERE id = ?', (analysis_id,))
                
                result = cursor.fetchone()
                if result:
                    analysis = dict(result)
                    # Parse JSON fields
                    if analysis['official_sources']:
                        analysis['official_sources'] = json.loads(analysis['official_sources'])
                    if analysis['news_sources']:
                        analysis['news_sources'] = json.loads(analysis['news_sources'])
                    return analysis
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting analysis by ID: {e}")
            return None
    
    def save_performance_metric(self, operation_type: str, execution_time_ms: float, 
                               success: bool = True, error_details: str = None, user_id: int = None):
        """Save performance metrics for monitoring."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO performance_metrics 
                    (operation_type, execution_time_ms, success, error_details, user_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (operation_type, execution_time_ms, success, error_details, user_id))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving performance metric: {e}")
    
    def get_performance_stats(self, operation_type: Optional[str] = None, 
                            hours_back: int = 24) -> Dict[str, Any]:
        """Get performance statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                where_clause = "WHERE timestamp >= datetime('now', '-{} hours')".format(hours_back)
                if operation_type:
                    where_clause += f" AND operation_type = '{operation_type}'"
                
                cursor.execute(f'''
                    SELECT 
                        operation_type,
                        COUNT(*) as total_operations,
                        AVG(execution_time_ms) as avg_time,
                        MIN(execution_time_ms) as min_time,
                        MAX(execution_time_ms) as max_time,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count
                    FROM performance_metrics 
                    {where_clause}
                    GROUP BY operation_type
                ''')
                
                results = cursor.fetchall()
                return {row['operation_type']: dict(row) for row in results}
                
        except Exception as e:
            self.logger.error(f"Error getting performance stats: {e}")
            return {}
    
    def cleanup_old_data(self, days_old: int = 90):
        """Clean up old data to maintain database performance."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Clean old analyses
                cursor.execute('''
                    DELETE FROM news_analysis 
                    WHERE analyzed_date < datetime('now', '-{} days')
                '''.format(days_old))
                
                # Clean old performance metrics
                cursor.execute('''
                    DELETE FROM performance_metrics 
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(days_old))
                
                # Clean expired cache entries
                cursor.execute('''
                    DELETE FROM analysis_cache 
                    WHERE expiry_date < datetime('now')
                ''')
                
                conn.commit()
                self.logger.info(f"Cleaned up data older than {days_old} days")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get general database statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Count analyses
                cursor.execute('SELECT COUNT(*) as count FROM news_analysis')
                stats['total_analyses'] = cursor.fetchone()['count']
                
                # Count users
                cursor.execute('SELECT COUNT(*) as count FROM user_stats')
                stats['total_users'] = cursor.fetchone()['count']
                
                # Average credibility score
                cursor.execute('SELECT AVG(credibility_score) as avg FROM news_analysis')
                result = cursor.fetchone()
                stats['avg_credibility_score'] = result['avg'] if result['avg'] else 0
                
                # Most active users
                cursor.execute('''
                    SELECT user_id, total_analyses 
                    FROM user_stats 
                    ORDER BY total_analyses DESC 
                    LIMIT 5
                ''')
                stats['top_users'] = [dict(row) for row in cursor.fetchall()]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}

# Global database instance
db = NewsDatabase() 