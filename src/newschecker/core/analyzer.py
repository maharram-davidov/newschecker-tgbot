import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class CredibilityAnalyzer:
    """
    Advanced credibility analysis system for news content.
    
    This analyzer evaluates news credibility based on multiple factors:
    - Source verification and reputation
    - Content quality and structure
    - Fact-checking indicators
    - Language patterns and bias detection
    - Temporal relevance
    """
    
    def __init__(self):
        """Initialize the credibility analyzer with scoring parameters."""
        self.logger = logging.getLogger(__name__)
        
        # Scoring weights for different factors
        self.weights = {
            'source_credibility': 0.30,      # 30% - Source verification and reputation
            'content_quality': 0.25,         # 25% - Content structure and quality
            'factual_indicators': 0.20,      # 20% - Fact-checking indicators
            'language_analysis': 0.15,       # 15% - Language patterns and bias
            'temporal_relevance': 0.10       # 10% - Recency and relevance
        }
        
        # Credibility thresholds
        self.credibility_thresholds = {
            'high': 7.5,
            'medium': 5.0,
            'low': 2.5
        }
        
        # Warning flag patterns
        self.warning_patterns = {
            'sensational_language': [
                r'\b(SHOCKING|BREAKING|EXCLUSIVE|URGENT|ALERT)\b',
                r'\b(müdhiş|şok edici|fövqəladə|təcili)\b',
                r'!{2,}',  # Multiple exclamation marks
                r'\b(EVERYONE MUST KNOW|hamı bilməlidir)\b'
            ],
            'emotional_manipulation': [
                r'\b(you won\'t believe|inanmayacaqsınız)\b',
                r'\b(doctors hate|həkimlər nifrət edir)\b',
                r'\b(secret that|gizli sirr)\b',
                r'\b(they don\'t want you to know|bilməyinizi istəmirlər)\b'
            ],
            'unverified_claims': [
                r'\b(according to anonymous|anonim mənbəyə görə)\b',
                r'\b(insider sources|daxili mənbələr)\b',
                r'\b(leaked information|sızan məlumat)\b',
                r'\b(exclusive sources|ekskluziv mənbələr)\b'
            ],
            'conspiracy_indicators': [
                r'\b(cover-up|ört-basdır)\b',
                r'\b(hidden truth|gizli həqiqət)\b',
                r'\b(they control|onlar idarə edir)\b',
                r'\b(wake up people|oyanın insanlar)\b'
            ]
        }
        
        # Trusted source indicators
        self.trusted_indicators = [
            'reuters', 'ap news', 'bbc', 'dw', 'cnn', 'who.int', 'gov.az',
            'president.az', 'mfa.gov.az', 'azernews.az', 'trend.az'
        ]
        
        # Quality indicators
        self.quality_indicators = {
            'has_date': r'\d{1,2}[./]\d{1,2}[./]\d{2,4}',
            'has_author': r'(by |tərəfindən |müəllif:)',
            'has_quotes': r'[""„"].*?[""„"]',
            'has_statistics': r'\d+[%‰]|\d+\s*(min|max|ortalama|average)',
            'proper_grammar': True  # Will be analyzed separately
        }

    def analyze_credibility(self, content: str, search_results: Dict[str, Any], 
                          mentioned_sources: str) -> Dict[str, Any]:
        """
        Perform comprehensive credibility analysis.
        
        Args:
            content: News content to analyze
            search_results: Results from news source searches
            mentioned_sources: Extracted source information
            
        Returns:
            Dict containing analysis results and scores
        """
        try:
            self.logger.debug("Starting credibility analysis")
            
            # Initialize analysis results
            analysis = {
                'source_score': 0.0,
                'content_score': 0.0,
                'factual_score': 0.0,
                'language_score': 0.0,
                'temporal_score': 0.0,
                'final_score': 0.0,
                'credibility_level': 'unknown',
                'warning_flags': [],
                'positive_indicators': [],
                'recommendations': []
            }
            
            # Analyze each component
            analysis['source_score'] = self._analyze_source_credibility(search_results, mentioned_sources)
            analysis['content_score'] = self._analyze_content_quality(content)
            analysis['factual_score'] = self._analyze_factual_indicators(content, search_results)
            analysis['language_score'] = self._analyze_language_patterns(content)
            analysis['temporal_score'] = self._analyze_temporal_relevance(search_results)
            
            # Calculate final weighted score
            analysis['final_score'] = (
                analysis['source_score'] * self.weights['source_credibility'] +
                analysis['content_score'] * self.weights['content_quality'] +
                analysis['factual_score'] * self.weights['factual_indicators'] +
                analysis['language_score'] * self.weights['language_analysis'] +
                analysis['temporal_score'] * self.weights['temporal_relevance']
            )
            
            # Determine credibility level
            analysis['credibility_level'] = self._determine_credibility_level(analysis['final_score'])
            
            # Generate warning flags and recommendations
            analysis['warning_flags'] = self._generate_warning_flags(content, analysis)
            analysis['positive_indicators'] = self._generate_positive_indicators(content, search_results, analysis)
            analysis['recommendations'] = self._generate_recommendations(analysis)
            
            self.logger.debug(f"Credibility analysis completed. Final score: {analysis['final_score']:.2f}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in credibility analysis: {e}")
            return self._get_default_analysis()

    def _analyze_source_credibility(self, search_results: Dict[str, Any], mentioned_sources: str) -> float:
        """Analyze credibility based on sources."""
        score = 5.0  # Base score
        
        try:
            # Check official sources
            official_sources = search_results.get('official_sources', [])
            if official_sources:
                score += 2.0  # Boost for official source confirmation
                score += min(len(official_sources) * 0.5, 2.0)  # Additional boost for multiple sources
            
            # Check news sources
            news_sources = search_results.get('news_sources', [])
            if news_sources:
                # Analyze source diversity and credibility
                trusted_count = 0
                for source in news_sources:
                    url = source.get('link', '').lower()
                    if any(trusted in url for trusted in self.trusted_indicators):
                        trusted_count += 1
                
                if trusted_count > 0:
                    score += min(trusted_count * 0.3, 1.5)
                
                # Boost for source diversity
                unique_domains = set()
                for source in news_sources:
                    url = source.get('link', '')
                    if url:
                        domain = url.split('/')[2] if len(url.split('/')) > 2 else url
                        unique_domains.add(domain)
                
                if len(unique_domains) > 1:
                    score += min(len(unique_domains) * 0.2, 1.0)
            
            # Analyze mentioned sources
            if mentioned_sources:
                if any(indicator in mentioned_sources.lower() for indicator in self.trusted_indicators):
                    score += 1.0
                
                # Check for specific source types
                if 'rəsmi' in mentioned_sources.lower() or 'official' in mentioned_sources.lower():
                    score += 0.5
                if 'nazirlik' in mentioned_sources.lower() or 'ministry' in mentioned_sources.lower():
                    score += 0.5
            
            return min(score, 10.0)
            
        except Exception as e:
            self.logger.error(f"Error in source credibility analysis: {e}")
            return 5.0

    def _analyze_content_quality(self, content: str) -> float:
        """Analyze content quality indicators."""
        score = 5.0  # Base score
        
        try:
            # Length analysis
            if len(content) > 200:
                score += 0.5
            if len(content) > 500:
                score += 0.5
            
            # Structure analysis
            sentences = content.split('.')
            if len(sentences) > 3:
                score += 0.5
            
            # Check for quality indicators
            for indicator, pattern in self.quality_indicators.items():
                if indicator == 'proper_grammar':
                    continue  # Skip for now
                
                if re.search(pattern, content, re.IGNORECASE):
                    score += 0.3
            
            # Paragraph structure
            paragraphs = content.split('\n')
            if len(paragraphs) > 1:
                score += 0.3
            
            # Check for proper capitalization
            if content[0].isupper() if content else False:
                score += 0.2
            
            return min(score, 10.0)
            
        except Exception as e:
            self.logger.error(f"Error in content quality analysis: {e}")
            return 5.0

    def _analyze_factual_indicators(self, content: str, search_results: Dict[str, Any]) -> float:
        """Analyze factual indicators and verification."""
        score = 5.0  # Base score
        
        try:
            # Check for specific facts, dates, numbers
            if re.search(r'\d{4}', content):  # Years
                score += 0.5
            if re.search(r'\d+[%‰]', content):  # Percentages
                score += 0.3
            if re.search(r'\$\d+|\d+\s*(dollar|manat|azn)', content, re.IGNORECASE):  # Money amounts
                score += 0.3
            
            # Cross-reference with search results
            official_sources = search_results.get('official_sources', [])
            news_sources = search_results.get('news_sources', [])
            
            if official_sources:
                # Check if content aligns with official sources
                content_lower = content.lower()
                for source in official_sources[:3]:  # Check top 3
                    snippet = source.get('snippet', '').lower()
                    if snippet:
                        # Simple similarity check
                        common_words = set(content_lower.split()) & set(snippet.split())
                        if len(common_words) > 5:
                            score += 0.5
            
            if news_sources:
                # Check consistency across multiple news sources
                consistent_reports = 0
                content_lower = content.lower()
                
                for source in news_sources[:5]:  # Check top 5
                    snippet = source.get('snippet', '').lower()
                    if snippet:
                        common_words = set(content_lower.split()) & set(snippet.split())
                        if len(common_words) > 3:
                            consistent_reports += 1
                
                if consistent_reports > 1:
                    score += min(consistent_reports * 0.3, 1.5)
            
            return min(score, 10.0)
            
        except Exception as e:
            self.logger.error(f"Error in factual indicators analysis: {e}")
            return 5.0

    def _analyze_language_patterns(self, content: str) -> float:
        """Analyze language patterns for bias and sensationalism."""
        score = 8.0  # Start with high score, deduct for issues
        
        try:
            content_lower = content.lower()
            
            # Check for warning patterns
            for pattern_type, patterns in self.warning_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        score -= min(len(matches) * 0.5, 2.0)
            
            # Check for excessive punctuation
            exclamation_count = content.count('!')
            if exclamation_count > 3:
                score -= min(exclamation_count * 0.2, 1.5)
            
            # Check for ALL CAPS (indicates shouting)
            caps_words = re.findall(r'\b[A-Z]{3,}\b', content)
            if len(caps_words) > 2:
                score -= min(len(caps_words) * 0.1, 1.0)
            
            # Check for balanced language
            if any(word in content_lower for word in ['however', 'although', 'but', 'lakin', 'ancaq']):
                score += 0.3  # Bonus for balanced language
            
            return max(score, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error in language pattern analysis: {e}")
            return 6.0

    def _analyze_temporal_relevance(self, search_results: Dict[str, Any]) -> float:
        """Analyze temporal relevance and recency."""
        score = 5.0  # Base score
        
        try:
            current_time = datetime.now()
            
            # Check official sources recency
            official_sources = search_results.get('official_sources', [])
            for source in official_sources:
                # This would require date extraction from search results
                # For now, give bonus for having any official sources
                score += 0.5
                break
            
            # Check news sources recency
            news_sources = search_results.get('news_sources', [])
            if news_sources:
                # Assume recent if we found sources (would need better date parsing)
                score += min(len(news_sources) * 0.1, 1.0)
            
            return min(score, 10.0)
            
        except Exception as e:
            self.logger.error(f"Error in temporal relevance analysis: {e}")
            return 5.0

    def _determine_credibility_level(self, score: float) -> str:
        """Determine credibility level based on score."""
        if score >= self.credibility_thresholds['high']:
            return 'Yüksək Etibarlı'
        elif score >= self.credibility_thresholds['medium']:
            return 'Orta Etibarlı'
        elif score >= self.credibility_thresholds['low']:
            return 'Aşağı Etibarlı'
        else:
            return 'Şübhəli'

    def _generate_warning_flags(self, content: str, analysis: Dict[str, Any]) -> List[str]:
        """Generate warning flags based on analysis."""
        flags = []
        
        try:
            # Language-based warnings
            if analysis['language_score'] < 5.0:
                flags.append('⚠️ Sensasiya dili və ya qərəzli ifadələr aşkar edildi')
            
            # Source-based warnings
            if analysis['source_score'] < 4.0:
                flags.append('⚠️ Mənbələr kifayət qədər etibarlı deyil')
            
            # Content quality warnings
            if analysis['content_score'] < 4.0:
                flags.append('⚠️ Məzmun keyfiyyəti aşağıdır')
            
            # Factual warnings
            if analysis['factual_score'] < 4.0:
                flags.append('⚠️ Faktiki məlumatlar təsdiq edilməyib')
            
            # Check for specific warning patterns
            content_lower = content.lower()
            for pattern_type, patterns in self.warning_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        if pattern_type == 'sensational_language':
                            flags.append('⚠️ Sensasiyalı dil istifadə edilib')
                        elif pattern_type == 'emotional_manipulation':
                            flags.append('⚠️ Emosional manipulyasiya əlamətləri')
                        elif pattern_type == 'unverified_claims':
                            flags.append('⚠️ Təsdiqlənməmiş iddialar')
                        elif pattern_type == 'conspiracy_indicators':
                            flags.append('⚠️ Sui-qəsd nəzəriyyəsi əlamətləri')
                        break
            
            return list(set(flags))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Error generating warning flags: {e}")
            return []

    def _generate_positive_indicators(self, content: str, search_results: Dict[str, Any], 
                                    analysis: Dict[str, Any]) -> List[str]:
        """Generate positive credibility indicators."""
        indicators = []
        
        try:
            # Source-based positives
            if analysis['source_score'] > 7.0:
                indicators.append('✅ Etibarlı mənbələr tərəfindən təsdiqlənib')
            
            if search_results.get('official_sources'):
                indicators.append('✅ Rəsmi mənbələrdə məlumat tapılıb')
            
            # Content quality positives
            if analysis['content_score'] > 7.0:
                indicators.append('✅ Yüksək keyfiyyətli məzmun strukturu')
            
            # Language positives
            if analysis['language_score'] > 7.0:
                indicators.append('✅ Bitərəf və professional dil')
            
            # Factual positives
            if analysis['factual_score'] > 7.0:
                indicators.append('✅ Faktiki məlumatlar təsdiqlənib')
            
            # Multiple source confirmation
            news_sources = search_results.get('news_sources', [])
            if len(news_sources) > 2:
                indicators.append('✅ Müxtəlif mənbələr tərəfindən təsdiqlənib')
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error generating positive indicators: {e}")
            return []

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        try:
            credibility_level = analysis['credibility_level']
            final_score = analysis['final_score']
            
            if credibility_level == 'Yüksək Etibarlı':
                recommendations.append('💡 Bu xəbər etibarlı görünür, lakin digər mənbələrlə də yoxlamaq faydalıdır')
            elif credibility_level == 'Orta Etibarlı':
                recommendations.append('💡 Əlavə mənbələrlə yoxlamaq tövsiyə olunur')
                recommendations.append('💡 Rəsmi mənbələrə müraciət edin')
            elif credibility_level == 'Aşağı Etibarlı':
                recommendations.append('💡 Bu xəbəri ehtiyatla qarşılayın')
                recommendations.append('💡 Digər etibarlı mənbələrdən yoxlayın')
                recommendations.append('💡 Paylaşmazdan əvvəl təsdiqləyin')
            else:  # Şübhəli
                recommendations.append('💡 Bu xəbər şübhəlidir - paylaşmayın')
                recommendations.append('💡 Rəsmi mənbələrdən təsdiq axtarın')
                recommendations.append('💡 Yanlış məlumat ola bilər')
            
            # Specific recommendations based on scores
            if analysis['source_score'] < 5.0:
                recommendations.append('💡 Mənbələrin etibarlılığını yoxlayın')
            
            if analysis['factual_score'] < 5.0:
                recommendations.append('💡 Faktiki məlumatları digər mənbələrlə müqayisə edin')
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return ['💡 Həmişə çoxlu mənbədən yoxlayın']

    def _get_default_analysis(self) -> Dict[str, Any]:
        """Return default analysis in case of errors."""
        return {
            'source_score': 5.0,
            'content_score': 5.0,
            'factual_score': 5.0,
            'language_score': 5.0,
            'temporal_score': 5.0,
            'final_score': 5.0,
            'credibility_level': 'Naməlum',
            'warning_flags': ['⚠️ Analiz xətası baş verdi'],
            'positive_indicators': [],
            'recommendations': ['💡 Digər mənbələrlə yoxlayın']
        }

# Global credibility analyzer instance
credibility_analyzer = CredibilityAnalyzer() 