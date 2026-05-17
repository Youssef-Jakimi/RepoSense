"""
Vercel serverless function handler for FastAPI.
This file is the entry point for Vercel's Python runtime.
"""
from api.main import app

# Vercel expects a variable named 'app' or 'handler'
# FastAPI app is already defined in api.main, so we just import it

# Made with Bob
