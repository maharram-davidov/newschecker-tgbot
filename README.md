# NewsChecker – Applied News Credibility Analysis

NewsChecker is an **applied AI and system integration project** that explores how news credibility can be analyzed using a combination of AI-assisted text analysis, source checking, and practical heuristics.

The project focuses on **pipeline design, experimentation, and system integration**, rather than building state-of-the-art models from scratch.

---

## 🔍 Project Motivation
Misinformation spreads rapidly through messaging platforms and social media.  
This project explores how news credibility signals can be extracted from:
- Textual content
- Source information
- Language patterns

The goal is to better understand the challenges and limitations of automated news verification.

---

## 🧠 System Overview
The system follows a multi-step analysis pipeline:

1. Input handling (text, URL, or image)
2. Content extraction and preprocessing
3. AI-assisted credibility analysis
4. Heuristic-based signal aggregation
5. Result presentation via Telegram bot or web interface

The system is designed for experimentation and comparative analysis.

---

## ⚙️ Analysis Approach
- AI-assisted text analysis (LLM-based)
- Rule-based and heuristic signals
- Source validation using external references
- Simple scoring mechanism for interpretability

The emphasis is on **understanding model behavior and failure cases**, not maximizing benchmark performance.

---

## 🧪 Evaluation Focus
Evaluation is qualitative and exploratory:
- Observing false positives and false negatives
- Identifying bias and sensational language
- Analyzing limitations of automated verification

This helps highlight why human oversight is still necessary.

---

## 🤖 Telegram Bot Integration
The analysis pipeline is integrated into a Telegram bot to:
- Enable real-time interaction
- Collect user feedback
- Test system behavior in practical scenarios

---

## ⚠️ Limitations
- AI-based analysis may hallucinate or overgeneralize
- Source verification is not exhaustive
- Credibility scoring is heuristic-based
- Cultural and contextual bias may exist

These limitations are documented intentionally for future improvement.

---

## 🔮 Possible Future Improvements
- More systematic evaluation metrics
- Comparison with classical NLP-based models
- Better separation between AI and rule-based logic
- Dataset-driven benchmarking

---

## 🛠️ How to Run
```bash
pip install -r requirements.txt
python main.py
