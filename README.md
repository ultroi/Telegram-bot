# Telegram Raja Chor Sipahi Mantri Game Bot

This is a Telegram bot for playing the Raja Chor Sipahi Mantri game in a group chat. 

## How to Use

1. **Start the Bot**: Send a message to the bot in a private chat to initiate interaction.
2. **Start a Game**: Use the `/startgame` command in a group chat to start a new game.
3. **Join the Game**: Use the `/join` command to join the game within the given time limit.
4. **Leave the Game**: Use the `/leave` command to leave the game if you no longer wish to participate.
5. **Make a Guess**: If you are the Mantri, use the `/guess <player_name>` command to guess who the Chor is.

## Setup

1. **Install Dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

2. **Run the Bot**:
    ```sh
    python bot.py
    ```

## Commands

- `/start`: Initiates interaction with the bot in private chat.
- `/startgame`: Starts a new game in a group chat.
- `/join`: Joins the ongoing game.
- `/leave`: Leaves the current game.
- `/guess <player_name>`: Makes a guess if you are the Mantri.

## License

This project is licensed under the MIT License.
