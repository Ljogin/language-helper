# File: app.py
# Streamlit Language Helper v1–v7
# GPT-4o + TTS-1 + Instructor + SQLite
# Autor: ChatGPT (GPT-5)

import os
import io
import sqlite3
import datetime
from typing import List, Dict

import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import instructor
from pydantic import BaseModel, Field

# ----------------------------------------
# KONFIGURACJA
# ----------------------------------------
st.set_page_config(page_title="Language Helper", page_icon="🌍", layout="wide")
st.title("🌍 Language Helper – nauka języków obcych")
st.caption("GPT-4o + TTS + analiza słownictwa + baza historii")

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
iclient = instructor.from_openai(client) if client else None

if not OPENAI_API_KEY:
    st.warning("⚠️ Brak klucza OPENAI_API_KEY w .env lub Streamlit Secrets")

# ----------------------------------------
# BAZA DANYCH HISTORII
# ----------------------------------------
DB_PATH = "translations.db"
conn = sqlite3.connect(DB_PATH)
conn.execute(
    """CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        input_lang TEXT,
        output_lang TEXT,
        original_text TEXT,
        result_text TEXT,
        explanation TEXT
    )"""
)
conn.commit()

# ----------------------------------------
# MODELE INSTRUCTOR (dla ciekawych słówek i gramatyki)
# ----------------------------------------
class Explanation(BaseModel):
    words: List[str] = Field(..., description="Lista słówek wartych zapamiętania")
    grammar_notes: List[str] = Field(..., description="Uwagi gramatyczne i konstrukcje")

# ----------------------------------------
# FUNKCJE POMOCNICZE
# ----------------------------------------
def translate_text(text: str, target_lang: str) -> str:
    """Tłumaczenie tekstu"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Tłumacz tekst z polskiego na {target_lang}."},
            {"role": "user", "content": text},
        ],
        temperature=0.6,
    )
    return resp.choices[0].message.content.strip()

def correct_text(text: str, lang: str) -> str:
    """Poprawianie tekstu w języku obcym"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Popraw błędy w tekście ({lang}) i napisz go naturalnie."},
            {"role": "user", "content": text},
        ],
        temperature=0.6,
    )
    return resp.choices[0].message.content.strip()

def beautify_text(text: str) -> str:
    """Ładne sformułowanie tekstu"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Przeredaguj tekst, aby był naturalny i ładnie brzmiący."},
            {"role": "user", "content": text},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()

def generate_explanation(text: str, lang: str) -> Explanation:
    """Generowanie listy słówek i wskazówek gramatycznych"""
    return iclient.chat.completions.create(
        model="gpt-4o-mini",
        response_model=Explanation,
        messages=[
            {
                "role": "system",
                "content": f"Przeanalizuj tekst ({lang}) i podaj listę słówek oraz krótkie notatki gramatyczne."
            },
            {"role": "user", "content": text},
        ],
        temperature=0.4,
    )

def generate_audio(text: str, lang: str) -> bytes:
    """Generowanie wersji audio"""
    lang_map = {"en": "alloy", "es": "verse", "de": "sage", "fr": "coral", "pl": "alloy"}
    voice = lang_map.get(lang, "alloy")
    audio = client.audio.speech.create(model="gpt-4o-mini-tts", voice=voice, input=text)
    return audio.read()

def save_to_history(input_lang, output_lang, text_in, text_out, explanation):
    conn.execute(
        "INSERT INTO history VALUES (NULL,?,?,?,?,?,?)",
        (
            datetime.datetime.now().isoformat(timespec="seconds"),
            input_lang,
            output_lang,
            text_in,
            text_out,
            json.dumps(explanation if explanation else {}),
        ),
    )
    conn.commit()

# ----------------------------------------
# INTERFEJS
# ----------------------------------------
mode = st.selectbox(
    "Wybierz tryb działania:",
    [
        "🇵🇱 Tłumaczenie z polskiego",
        "🌐 Tłumaczenie na wybrany język",
        "✏️ Poprawianie tekstu obcego",
        "💅 Upiększanie dowolnego tekstu",
    ],
)

text_input = st.text_area("Wpisz tekst:", height=150, placeholder="Wpisz tekst po polsku lub w języku obcym...")

col_lang1, col_lang2 = st.columns(2)
with col_lang1:
    target_lang = st.selectbox("Język docelowy:", ["en", "de", "es", "fr", "it", "pl"], index=0)
with col_lang2:
    gen_audio = st.checkbox("🎧 Wygeneruj wersję audio", value=True)

go_btn = st.button("🚀 Przetwórz")

# ----------------------------------------
# LOGIKA
# ----------------------------------------
if go_btn and text_input.strip():
    with st.spinner("Przetwarzanie..."):
        output = ""
        explanation = None

        if mode == "🇵🇱 Tłumaczenie z polskiego":
            output = translate_text(text_input, "english")
            explanation = generate_explanation(output, "english")

        elif mode == "🌐 Tłumaczenie na wybrany język":
            output = translate_text(text_input, target_lang)
            explanation = generate_explanation(output, target_lang)

        elif mode == "✏️ Poprawianie tekstu obcego":
            output = correct_text(text_input, target_lang)
            explanation = generate_explanation(output, target_lang)

        elif mode == "💅 Upiększanie dowolnego tekstu":
            output = beautify_text(text_input)
            explanation = generate_explanation(output, target_lang)

        # Zapis do historii
        save_to_history("auto", target_lang, text_input, output, explanation.model_dump() if explanation else {})

        # Wyświetlenie wyniku
        st.subheader("💬 Wynik:")
        st.write(output)

        # Wyjaśnienia
        if explanation:
            st.divider()
            st.subheader("📘 Ciekawe słówka:")
            st.markdown(", ".join(explanation.words))
            st.subheader("🧩 Konstrukcje gramatyczne:")
            for note in explanation.grammar_notes:
                st.markdown(f"- {note}")

        # Audio
        if gen_audio:
            try:
                st.divider()
                st.subheader("🔊 Wersja audio:")
                audio_bytes = generate_audio(output, target_lang)
                st.audio(audio_bytes, format="audio/mp3")
            except Exception as e:
                st.error(f"Nie udało się wygenerować dźwięku: {e}")

# ----------------------------------------
# HISTORIA
# ----------------------------------------
st.divider()
st.subheader("📜 Historia tłumaczeń")
rows = conn.execute("SELECT timestamp, input_lang, output_lang, original_text, result_text FROM history ORDER BY id DESC LIMIT 10").fetchall()
for r in rows:
    st.markdown(f"**[{r[0]}]** ({r[1]}→{r[2]})  \n🗣️ _{r[3]}_  \n➡️ **{r[4]}**")
