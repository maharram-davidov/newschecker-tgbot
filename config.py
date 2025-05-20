 # Rəsmi mənbələr
OFFICIAL_SOURCES = [
    "gov.az",           # Azərbaycan hökuməti
    "who.int",          # Dünya Səhiyyət Təşkilatı
    "un.org",           # BMT
    "president.az",     # Azərbaycan Prezidenti
    "meclis.gov.az",    # Azərbaycan Milli Məclisi
    "ec.europa.eu",     # Avropa Komissiyası
    "unicef.org",       # UNİCEF
    "unhcr.org",        # BMT Məcburi Köçkünlər üzrə Ali Komissarlığı
    "worldbank.org",    # Dünya Bankı
    "imf.org"           # Beynəlxalq Valyuta Fondu
]

# Xəbər mənbələri
NEWS_SOURCES = [
    "bbc.com",          # BBC
    "reuters.com",      # Reuters
    "apnews.com",       # Associated Press
    "aa.com.tr",        # Anadolu Ajansı
    "azertag.az",       # AzərTAC
    "report.az",        # Report
    "apa.az",           # APA
    "azvision.az"       # AzVision
]

def get_official_search_params(keywords, date_range, api_key):
    """Rəsmi mənbələrdə axtarış parametrlərini qaytarır"""
    sites = " OR ".join([f"site:{site}" for site in OFFICIAL_SOURCES])
    return {
        "engine": "google",
        "q": f"{keywords} {sites} {date_range}",
        "api_key": api_key,
        "num": 5
    }

def get_news_search_params(keywords, date_range, api_key):
    """Xəbər mənbələrində axtarış parametrlərini qaytarır"""
    sites = " OR ".join([f"site:{site}" for site in NEWS_SOURCES])
    return {
        "engine": "google",
        "q": f"{keywords} {sites} {date_range}",
        "api_key": api_key,
        "num": 5
    }