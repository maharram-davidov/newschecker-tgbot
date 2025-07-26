"""
Flask web application for NewsChecker.

This module provides a web interface for news analysis.
"""

from flask import Flask, render_template, request, jsonify
import logging
from pathlib import Path

# Import from new structure
from ..config.settings import config
from ..core.analyzer import credibility_analyzer
from ..core.database import db
from ..core.cache import news_cache
from ..utils.security import security_validator
from ..utils.logging import enhanced_logger

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure Flask
    app.secret_key = config.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')
    
    # Set template folder
    template_dir = Path(__file__).parent.parent.parent.parent / 'templates'
    app.template_folder = str(template_dir)
    
    enhanced_logger.info("Flask application created")
    
    @app.route('/')
    def index():
        """Main page route."""
        try:
            return render_template('index.html')
        except Exception as e:
            enhanced_logger.error("Error rendering index page", error=e)
            return """
            <html>
            <head><title>NewsChecker</title></head>
            <body>
                <h1>NewsChecker Web Interface</h1>
                <p>Template not found. Running in development mode.</p>
                <form action="/analyze" method="POST">
                    <textarea name="content" placeholder="Enter news content here..." rows="10" cols="50"></textarea><br>
                    <input type="submit" value="Analyze">
                </form>
            </body>
            </html>
            """
    
    @app.route('/analyze', methods=['POST'])
    def analyze():
        """Analyze news content."""
        try:
            content = request.form.get('content', '').strip()
            
            if not content:
                return jsonify({'error': 'No content provided'}), 400
            
            # Security validation
            security_result = security_validator.validate_content(content, 'text')
            if not security_result['safe']:
                enhanced_logger.log_security_event('web_content_validation_failed', None, {
                    'errors': security_result['errors'],
                    'content_preview': content[:100]
                })
                return jsonify({'error': 'Content failed security validation'}), 400
            
            # Use sanitized content
            content = security_result.get('sanitized_content', content)
            
            # Check cache first
            cached_analysis = news_cache.get_cached_analysis(content)
            if cached_analysis:
                enhanced_logger.debug("Using cached analysis for web request")
                return jsonify({
                    'success': True,
                    'analysis': cached_analysis,
                    'cached': True
                })
            
            # Check database for duplicates
            duplicate_check = db.check_duplicate(content)
            if duplicate_check:
                enhanced_logger.debug("Using database duplicate for web request")
                return jsonify({
                    'success': True,
                    'analysis': duplicate_check['analysis_result'],
                    'credibility_score': duplicate_check['credibility_score'],
                    'analyzed_date': duplicate_check['analyzed_date'],
                    'from_database': True
                })
            
            # Perform new analysis - simplified for web interface
            credibility_analysis = credibility_analyzer.analyze_credibility(
                content, {'official_sources': [], 'news_sources': [], 'keywords': ''}, ''
            )
            
            # Create a simple analysis result
            analysis_result = f"""Web Analysis Results:

Content Analysis Score: {credibility_analysis['final_score']:.1f}/10
Credibility Level: {credibility_analysis['credibility_level']}

Warning Flags:
{chr(10).join(credibility_analysis['warning_flags']) if credibility_analysis['warning_flags'] else 'None detected'}

Recommendations:
{chr(10).join(credibility_analysis['recommendations'])}
"""
            
            # Cache the result
            news_cache.cache_analysis(content, analysis_result)
            
            # Save to database (with anonymous user_id)
            db.save_analysis(
                user_id=0,  # Anonymous web user
                news_content=content,
                news_type='web_text',
                keywords='',
                mentioned_sources='',
                official_sources=[],
                news_sources=[],
                analysis_result=analysis_result,
                credibility_score=int(credibility_analysis['final_score'])
            )
            
            enhanced_logger.info("Web analysis completed successfully")
            
            return jsonify({
                'success': True,
                'analysis': analysis_result,
                'credibility_score': credibility_analysis['final_score'],
                'credibility_level': credibility_analysis['credibility_level'],
                'warning_flags': credibility_analysis['warning_flags'],
                'recommendations': credibility_analysis['recommendations']
            })
            
        except Exception as e:
            enhanced_logger.error("Error in web analysis", error=e)
            return jsonify({'error': 'Analysis failed'}), 500
    
    @app.route('/health')
    def health():
        """Health check endpoint."""
        try:
            # Test database connection
            db_stats = db.get_database_stats()
            
            # Test cache
            cache_stats = news_cache.get_stats()
            
            return jsonify({
                'status': 'healthy',
                'database': {
                    'total_analyses': db_stats.get('total_analyses', 0),
                    'total_users': db_stats.get('total_users', 0)
                },
                'cache': {
                    'entries': cache_stats.get('total_entries', 0),
                    'memory_mb': cache_stats.get('memory_usage_mb', 0)
                }
            })
        except Exception as e:
            enhanced_logger.error("Health check failed", error=e)
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    
    @app.route('/stats')
    def stats():
        """Statistics endpoint."""
        try:
            db_stats = db.get_database_stats()
            cache_stats = news_cache.get_stats()
            
            return jsonify({
                'database_stats': db_stats,
                'cache_stats': cache_stats
            })
        except Exception as e:
            enhanced_logger.error("Error getting stats", error=e)
            return jsonify({'error': 'Failed to get stats'}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        enhanced_logger.error("Internal server error", error=error)
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        debug=config.WEB_DEBUG
    ) 