FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the project files
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Set environment variables
ENV BOT_TOKEN=your_actual_bot_token
ENV API_ID=your_actual_api_id
ENV API_HASH=your_actual_api_hash

# Run the bot
CMD ["python", "main.py"]
