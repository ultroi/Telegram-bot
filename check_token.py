from dotenv import load_dotenv
import os

# Explicitly specify the path to the .env file
env_path = './.env'
load_dotenv(dotenv_path=env_path)

# Get the token from the .env file
Token = os.getenv("BOT_TOKEN")

# Print the token for debugging
print(f"Token: {Token}")

# Check if the token is None
if not Token:
    raise ValueError("No token found. Please check your .env file.")
else:
    print("Token loaded successfully!")
