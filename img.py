import telebot
from telebot import types
from PIL import Image, ImageEnhance
import io

# Replace 'YOUR_TELEGRAM_BOT_API_TOKEN' with your actual bot token
API_TOKEN = '7500257227:AAHDOrxT3SjzvdIbXT1psVmT4kAnk-v-TZw'
bot = telebot.TeleBot(API_TOKEN)

# Global variable to store the last processed image
last_processed_image = None

# Step 1: Start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item = types.KeyboardButton("Upload Image")
    markup.add(item)
    bot.send_message(message.chat.id, "Welcome! Send me an image to start processing.", reply_markup=markup)

# Step 2: Handle photo uploads
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    global last_processed_image
    bot.send_message(message.chat.id, "Processing your image. Please wait...")
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Process the image
    image = Image.open(io.BytesIO(downloaded_file))

    # Save the original image to a global variable
    last_processed_image = io.BytesIO()
    image.save(last_processed_image, format='PNG')
    last_processed_image.seek(0)

    # Ask user for resolution and format
    markup = types.InlineKeyboardMarkup()
    btn_720p = types.InlineKeyboardButton("720p (PNG)", callback_data="resolution_720p_png")
    btn_1080p = types.InlineKeyboardButton("1080p (PNG)", callback_data="resolution_1080p_png")
    btn_4k = types.InlineKeyboardButton("4K (PNG)", callback_data="resolution_4k_png")
    btn_720p_jpg = types.InlineKeyboardButton("720p (JPG)", callback_data="resolution_720p_jpg")
    btn_1080p_jpg = types.InlineKeyboardButton("1080p (JPG)", callback_data="resolution_1080p_jpg")
    btn_4k_jpg = types.InlineKeyboardButton("4K (JPG)", callback_data="resolution_4k_jpg")
    markup.add(btn_720p, btn_1080p, btn_4k, btn_720p_jpg, btn_1080p_jpg, btn_4k_jpg)
    bot.send_message(message.chat.id, "Choose a resolution and format:", reply_markup=markup)

# Step 3: Handle resolution and format choices
@bot.callback_query_handler(func=lambda call: call.data.startswith('resolution_'))
def handle_resolution_and_format(call):
    global last_processed_image
    resolution, format = call.data.split('_')[1], call.data.split('_')[2]

    if last_processed_image:
        last_processed_image.seek(0)
        image = Image.open(last_processed_image)

        # Apply resolution change
        if resolution == '720p':
            image = image.resize((1280, 720), Image.ANTIALIAS)
        elif resolution == '1080p':
            image = image.resize((1920, 1080), Image.ANTIALIAS)
        elif resolution == '4k':
            image = image.resize((3840, 2160), Image.ANTIALIAS)

        # Save the resized image
        last_processed_image = io.BytesIO()
        image.save(last_processed_image, format=format.upper())
        last_processed_image.seek(0)

        # Ask for enhancements
        markup = types.InlineKeyboardMarkup()
        btn_brightness = types.InlineKeyboardButton("Enhance Brightness", callback_data="enhance_brightness")
        btn_contrast = types.InlineKeyboardButton("Enhance Contrast", callback_data="enhance_contrast")
        btn_sharpness = types.InlineKeyboardButton("Enhance Sharpness", callback_data="enhance_sharpness")
        btn_color = types.InlineKeyboardButton("Enhance Color", callback_data="enhance_color")
        btn_saturation = types.InlineKeyboardButton("Enhance Saturation", callback_data="enhance_saturation")
        markup.add(btn_brightness, btn_contrast, btn_sharpness, btn_color, btn_saturation)
        bot.send_message(call.message.chat.id, "Choose an enhancement option:", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "No image processed yet. Please upload an image first.")

# Step 4: Handle enhancement options
@bot.callback_query_handler(func=lambda call: call.data.startswith('enhance_'))
def handle_enhancement(call):
    global last_processed_image
    enhancement_type = call.data.split('_')[1]

    if last_processed_image:
        last_processed_image.seek(0)
        image = Image.open(last_processed_image)

        if enhancement_type == 'brightness':
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.5)  # Adjust brightness factor as needed
        elif enhancement_type == 'contrast':
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # Adjust contrast factor as needed
        elif enhancement_type == 'sharpness':
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)  # Adjust sharpness factor as needed
        elif enhancement_type == 'color':
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.5)  # Adjust color factor as needed
        elif enhancement_type == 'saturation':
            enhancer = ImageEnhance.Color(image)  # Saturation is controlled through color enhancement
            image = enhancer.enhance(1.5)  # Adjust saturation factor as needed

        # Save the enhanced image to a global variable
        last_processed_image = io.BytesIO()
        image.save(last_processed_image, format='PNG')
        last_processed_image.seek(0)

        # Ask user for output format and method
        markup = types.InlineKeyboardMarkup()
        btn_photo = types.InlineKeyboardButton("Send as Photo", callback_data="send_photo")
        btn_doc = types.InlineKeyboardButton("Send as Document", callback_data="send_doc")
        btn_jpg = types.InlineKeyboardButton("Convert to JPG", callback_data="convert_jpg")
        btn_png = types.InlineKeyboardButton("Convert to PNG", callback_data="convert_png")
        markup.add(btn_photo, btn_doc, btn_jpg, btn_png)
        bot.send_message(call.message.chat.id, "Choose the output format or method:", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "No image processed yet. Please upload an image first.")

# Step 5: Handle output format and method
@bot.callback_query_handler(func=lambda call: call.data.startswith('send_') or call.data.startswith('convert_'))
def handle_output_choice(call):
    global last_processed_image
    choice = call.data.split('_')[1]
    
    if last_processed_image:
        output_image = io.BytesIO()
        last_processed_image.seek(0)
        
        if choice in ['photo', 'doc']:
            # Send the image as photo or document
            if choice == 'photo':
                bot.send_photo(call.message.chat.id, photo=last_processed_image, caption="Here is your processed image.")
            elif choice == 'doc':
                output_image.write(last_processed_image.read())
                output_image.seek(0)
                bot.send_document(call.message.chat.id, document=output_image, caption="Here is your processed image.")
        elif choice in ['jpg', 'png']:
            # Convert to the selected format
            last_processed_image.seek(0)
            image = Image.open(last_processed_image)
            output_image = io.BytesIO()
            image.save(output_image, format=choice.upper())
            output_image.seek(0)
            bot.send_document(call.message.chat.id, document=output_image, caption=f"Your image in {choice.upper()} format.")
    else:
        bot.send_message(call.message.chat.id, "No image processed yet. Please upload an image first.")

# Run the bot
bot.polling()
