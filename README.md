# Xəbər Doğruluq Analiz Botu

Bu Telegram botu, istifadəçilərin göndərdiyi xəbərlərin doğruluğunu analiz edir və xəbərin etibarlılığını yoxlayır.

## Xüsusiyyətlər

- Xəbər linkləri və mətnləri analiz edə bilir
- Şəkil formatında göndərilən xəbərləri oxuya və analiz edə bilir (OCR)
- Xəbərdə istinad edilən mənbələri yoxlayır
- Rəsmi mənbələrdə doğrulama aparır
- Digər xəbər mənbələrində yoxlama edir
- Xəbərin doğruluğu, etibarlılığı və bitərəfliyi haqqında ətraflı analiz təqdim edir

## Quraşdırma

1. Python 3.7 və ya daha yüksək versiya tələb olunur

2. Tesseract OCR quraşdırın:
   - Windows: https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`

3. Tesseract dil paketlərini yükləyin:
   - Windows: Tesseract quraşdırıcısından seçin
   - Linux: `sudo apt-get install tesseract-ocr-aze tesseract-ocr-eng`
   - macOS: `brew install tesseract-lang`

4. Lazımi Python paketlərini yükləyin:
```bash
pip install -r requirements.txt
```

5. `.env` faylını yaradın və aşağıdakı məlumatları əlavə edin:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
SERPAPI_API_KEY=your_serpapi_api_key_here
```

## API Açarlarının Alınması

### Telegram Bot Token
1. Telegram-da @BotFather ilə danışın
2. `/newbot` əmrini göndərin
3. Botunuz üçün ad və istifadəçi adı seçin
4. BotFather sizə bot tokeni verəcək

### Google Gemini API Açarı
1. [Google AI Studio](https://makersuite.google.com/app/apikey) saytına daxil olun
2. API açarı yaradın
3. Açarı `.env` faylında `GEMINI_API_KEY` dəyişəninə əlavə edin

### SerpAPI Açarı
1. [SerpAPI](https://serpapi.com/) saytına daxil olun
2. Pulsuz hesab yaradın
3. API açarınızı alın
4. Açarı `.env` faylında `SERPAPI_API_KEY` dəyişəninə əlavə edin

## İstifadə

1. Botu başladın:
```bash
python bot.py
```

2. Telegram-da botunuzu tapın və `/start` əmrini göndərin

3. Botu istifadə etmək üçün:
   - Bir xəbər linki göndərin
   - Və ya xəbər mətni birbaşa yazın
   - Və ya xəbər şəkli göndərin
   - Bot avtomatik olaraq xəbəri analiz edəcək və nəticələri sizə göstərəcək

## Analiz Nəticələri

Bot hər xəbər üçün aşağıdakı analizi təqdim edir:

- Doğruluq Qiymətləndirməsi
- Mənbə Etibarlılığı
- Bitərəflik Analizi
- Xəbərdə İstinad Edilən Mənbələrin Doğrulanması
- Rəsmi Mənbələrdə Doğrulama
- Digər Xəbər Mənbələrində Doğrulama
- Xəbərdarlıqlar və Qeydlər

## Yoxlanılan Mənbələr

### Rəsmi Mənbələr
- gov.az (Azərbaycan hökuməti)
- who.int (Dünya Səhiyyət Təşkilatı)
- un.org (BMT)
- president.az (Azərbaycan Prezidenti)
- meclis.gov.az (Azərbaycan Milli Məclisi)
- ec.europa.eu (Avropa Komissiyası)
- unicef.org (UNİCEF)
- unhcr.org (BMT Məcburi Köçkünlər üzrə Ali Komissarlığı)
- worldbank.org (Dünya Bankı)
- imf.org (Beynəlxalq Valyuta Fondu)

### Xəbər Mənbələri
- bbc.com (BBC)
- reuters.com (Reuters)
- apnews.com (Associated Press)
- aa.com.tr (Anadolu Ajansı)
- azertag.az (AzərTAC)
- report.az (Report)
- apa.az (APA)
- azvision.az (AzVision)

## Təhlükəsizlik

- API açarlarınızı heç vaxt başqaları ilə paylaşmayın
- `.env` faylını `.gitignore` faylına əlavə edin
- Mütəmadi olaraq API açarlarınızı yeniləyin

## Dəstək

Hər hansı bir problem və ya sualınız varsa, zəhmət olmasa məlumat verin. 