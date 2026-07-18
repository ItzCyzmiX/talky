from dotenv import load_dotenv
import os
import groq

load_dotenv()

groq_client = groq.Groq(api_key=os.getenv("GROQ_KEY"))
