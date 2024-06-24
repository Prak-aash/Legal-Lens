import streamlit as st
import pandas as pd
from googletrans import Translator
from gtts import gTTS
from tempfile import NamedTemporaryFile
import re
import sounddevice as sd
import wavio
import numpy as np
import speech_recognition as sr

# Initialize the translator
translator = Translator()

# Load legal information from CSV
legal_file = 'intents.csv'
legal_df = pd.read_csv(legal_file)

def text_to_speech(text, lang):
    # Convert text to speech in the specified language
    tts = gTTS(text=text, lang=lang, slow=False)
    with NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tts.save(tmp_file.name)
        st.audio(tmp_file.name, format="audio/mp3")

def check_age_and_provide_info(query, lang):
    # Translate query to English if it's not in English
    if lang != "en":
        query = translator.translate(query, src=lang, dest="en").text
    
    # Identify the intent based on keywords
    intent = identify_intent(query)
    
    # Extract age from query if intent is related to driving license
    age = extract_age(query) if intent == "driving_license" else None
    
    # Validate age for driving license case
    if intent == "driving license":
        if age is None:
            return "Please provide your age to get information about obtaining a driving license."
        elif age < 18:
            return "You must be at least 18 years old to apply for a driving license in India."
        elif age > 100:
            return "You seem to be too old to apply for a driving license."
    
    # Get the response based on the identified intent and age (if applicable)
    if intent != 'unknown':
        response = get_legal_info(intent)
    else:
        response = "Sorry, I couldn't understand your query. Please try again."

    # Translate response back to the original language if needed
    if lang != "en":
        response = translator.translate(response, src="en", dest=lang).text

    return response

def identify_intent(query):
    # Convert query to lowercase for case insensitivity
    query = query.lower()
    
    # Search through each intent to find a match
    for index, row in legal_df.iterrows():
        if any(keyword in query for keyword in row['intents'].split(',')):
            return row['intents']

    # Return 'unknown' if no match is found
    return 'unknown'

def extract_age(query):
    # Extract age from query using regex
    try:
        match = re.search(r'\b(\d{2,3})\b', query)
        if match:
            return int(match.group())
        else:
            return None
    except Exception as e:
        st.write(f"Error extracting age: {e}")
        return None

def get_legal_info(intent):
    # Retrieve process from the CSV based on intent
    process = legal_df.loc[legal_df['intents'] == intent, 'process'].values[0]
    
    # Format the process as a step-by-step procedure
    return format_as_step_by_step(process)
    
def format_as_step_by_step(process):
    # Clean up the process string (remove quotes and leading/trailing spaces)
    process = process.strip('"')
    
    # Split into steps
    steps = process.split(". ")  # Split by period and space to maintain steps
    
    # Format as bullet points
    formatted_steps = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
    
    return formatted_steps

# Streamlit App
st.title("Legal Lens 🔎")
st.write("Niral Thiruvizha - Naan Mudhalvan")

# Function to record voice input and convert to text
def record_voice_input():
    lang_dict = {'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil'}
    
    try:
        # Voice input through microphone using sounddevice and wavio
        duration = 5  # seconds
        fs = 44100  # Sample rate
        st.write('## 🎤 Speak...')
        myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=2, dtype='int16')
        sd.wait()  # Wait until recording is finished
        wav_file = "recording.wav"
        wavio.write(wav_file, myrecording, fs, sampwidth=2)
        
        # Convert speech to text
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = recognizer.record(source)
            user_input = recognizer.recognize_google(audio_data, language='en-IN')  # Recognize speech using Google Speech Recognition

        detected_lang = translator.detect(user_input).lang  # Detect language of input
        st.write(f'## 🌍 Detected Language: {lang_dict.get(detected_lang, "Unknown")}')
        st.write(f'## 🗣️ You said: {user_input}')
        return user_input, detected_lang

    except sr.UnknownValueError:
        st.write("## 🚫 Could not understand audio")
    except sr.RequestError as e:
        st.write(f"## 🚫 Could not request results; {e}")
    except Exception as e:
        st.write(f"## 🚫 Error accessing microphone: {e}")

    return None, None  # Return None values if there's an error

# Container for search box-like layout
search_container = st.container()

with search_container:
    user_input = st.text_input("Enter your query")
    language = "auto"  # auto-detect language input

    # Placeholder for voice input button
    voice_input_button_placeholder = st.empty()

    if st.button("Submit"):
        if user_input:
            # Determine language of input
            detected_lang = translator.detect(user_input).lang

            # Process the query
            response = check_age_and_provide_info(user_input, detected_lang)

            st.markdown("## 💡 Step-By-Step Procedure:")
            st.markdown(response)  # Display as markdown to keep formatting

            st.write("## 🔊 Response Audio:")
            text_to_speech(response, lang=detected_lang)

            # Add download button for PDF
            if 'text_response' in st.session_state:
                import base64
                from fpdf import FPDF

                def create_pdf(response):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    for line in response.split('\n'):
                        pdf.cell(200, 10, txt=line, ln=True)
                    return pdf

                pdf = create_pdf(response)
                with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    pdf_output = tmp_file.name
                    pdf.output(pdf_output)

                with open(pdf_output, "rb") as file:
                    btn = st.download_button(
                        label="Download PDF",
                        data=file,
                        file_name="response.pdf",
                        mime="application/pdf"
                    )

    # Voice input button next to text input
    if voice_input_button_placeholder.button("🎙️ Record"):
        user_input, detected_lang = record_voice_input()
        if user_input:
            response = check_age_and_provide_info(user_input, detected_lang)
            st.markdown("## 💡 Step-By-Step Procedure:")
            st.markdown(response)  # Display as markdown to keep formatting

            st.write("## 🔊 Response Audio:")
            text_to_speech(response, lang=detected_lang)

            # Add download button for PDF
            if 'text_response' in st.session_state:
                import base64
                from fpdf import FPDF

                def create_pdf(response):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    for line in response.split('\n'):
                        pdf.cell(200, 10, txt=line, ln=True)
                    return pdf

                pdf = create_pdf(response)
                with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    pdf_output = tmp_file.name
                    pdf.output(pdf_output)

                with open(pdf_output, "rb") as file:
                    btn = st.download_button(
                        label="Download PDF",
                        data=file,
                        file_name="response.pdf",
                        mime="application/pdf"
                    )
