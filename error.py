import os
import requests
import base64
import json
import re
import subprocess
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv(dotenv_path='.env')
TOKEN = os.getenv("BOT_TOKEN_1")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Ensure this is correctly set in .env
GITHUB_TOKEN = "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"
REPO_OWNER = 'ultroi'
REPO_NAME = 'Telegram-bot'
FILE_PATH = 'game.py'  # Path to the file in your repo

# Check for tokens
if not TOKEN or not GITHUB_TOKEN:
    raise ValueError("Bot token or GitHub token is missing.")

# GitHub API URL
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

def fetch_file_content() -> str:
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(f"{GITHUB_API_URL}/contents/{FILE_PATH}", headers=headers)
    response.raise_for_status()
    file_data = response.json()
    return base64.b64decode(file_data['content']).decode('utf-8'), file_data['sha']

def update_file_content(content: str, sha: str) -> None:
    headers = {'Authorization': f'token {GITHUB_TOKEN}', 'Content-Type': 'application/json'}
    data = {
        'message': 'Fix errors in the code',
        'content': base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        'sha': sha
    }
    response = requests.put(f"{GITHUB_API_URL}/contents/{FILE_PATH}", headers=headers, data=json.dumps(data))
    response.raise_for_status()

def delete_file() -> None:
    headers = {'Authorization': f'token {GITHUB_TOKEN}', 'Content-Type': 'application/json'}
    file_content, file_sha = fetch_file_content()
    data = {
        'message': 'Delete erroneous code',
        'sha': file_sha
    }
    response = requests.delete(f"{GITHUB_API_URL}/contents/{FILE_PATH}", headers=headers, data=json.dumps(data))
    response.raise_for_status()

def analyze_and_fix_error(error_message: str) -> str:
    if 'SyntaxError' in error_message:
        return "Syntax errors typically involve incorrect syntax. Check your code for missing colons, parentheses, or incorrect indentation."
    elif 'ImportError' in error_message:
        return "Import errors occur if libraries are missing or incorrectly named. Ensure all dependencies are installed and correctly imported."
    elif 'NameError' in error_message:
        return "Name errors are due to using undefined variables or functions. Ensure all names are spelled correctly and defined."
    else:
        return "General error. Review the error message and code carefully."

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != -1002201661092:
        return

    file_content, file_sha = fetch_file_content()

    fixed_code = apply_repository_specific_fixes(file_content)
    
    try:
        result = subprocess.run(['python3', '-c', fixed_code], capture_output=True, text=True)
        if result.returncode != 0:
            error_message = result.stderr
            suggestion = analyze_and_fix_error(error_message)
            response_message = f"Execution failed:\n{error_message}\nSuggestion: {suggestion}"
            
            # Delete erroneous code and provide fixed code
            delete_file()
            await update.message.reply_text(f"{response_message}\n\nThe erroneous code has been deleted. Please provide the fixed code.")
        else:
            response_message = f"Execution result:\n{result.stdout}"
            await update.message.reply_text(response_message)
    except Exception as e:
        response_message = f"Unexpected error occurred: {e}"

    await update.message.reply_text(response_message)

def apply_repository_specific_fixes(code: str) -> str:
    # Example repository-specific fix
    if 'SyntaxError' in code:
        code = re.sub(r'(\d+)\s+(\d+)', r'\1 + \2', code)
    return code

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    
    application.run_polling()

if __name__ == '__main__':
    main()
