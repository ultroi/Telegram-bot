import telebot
from telebot import types
from PIL import Image, ImageEnhance
import io

API_TOKEN = '7500257227:AAHDOrxT3SjzvdIbXT1psVmT4kAnk-v-TZw'
bot = telebot.TeleBot(API_TOKEN)

# Global variables to store the last processed image and settings
last_processed_image = None
current_resolution = None
current_format = None
enhancements_applied = []

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
    global last_processed_image, current_resolution, current_format, enhancements_applied
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

    # Reset the settings
    current_resolution = None
    current_format = None
    enhancements_applied = []

    # Ask user for resolution and format
    markup = types.InlineKeyboardMarkup()
    btn_720p = types.InlineKeyboardButton("720p", callback_data="resolution_720p")
    btn_1080p = types.InlineKeyboardButton("1080p", callback_data="resolution_1080p")
    btn_4k = types.InlineKeyboardButton("4K", callback_data="resolution_4k")
    markup.add(btn_720p, btn_1080p, btn_4k)
    bot.send_message(message.chat.id, "Choose a resolution:", reply_markup=markup)

# Step 3: Handle resolution choices and ask for format
@bot.callback_query_handler(func=lambda call: call.data.startswith('resolution_'))
def handle_resolution(call):
    global last_processed_image, current_resolution
    resolution = call.data.split('_')[1]

    if last_processed_image:
        last_processed_image.seek(0)
        image = Image.open(last_processed_image)

        # Apply resolution change
        if resolution == '720p':
            image = image.resize((1280, 720), Image.Resampling.LANCZOS)
        elif resolution == '1080p':
            image = image.resize((1920, 1080), Image.Resampling.LANCZOS)
        elif resolution == '4k':
            image = image.resize((3840, 2160), Image.Resampling.LANCZOS)

        # Save the resized image
        last_processed_image = io.BytesIO()
        image.save(last_processed_image, format='PNG')
        last_processed_image.seek(0)
        current_resolution = resolution

        # Ask for format conversion
        markup = types.InlineKeyboardMarkup()
        btn_jpg = types.InlineKeyboardButton("Convert to JPG", callback_data="convert_jpg")
        btn_png = types.InlineKeyboardButton("Convert to PNG", callback_data="convert_png")
        btn_back = types.InlineKeyboardButton("Back", callback_data="back_resolution")
        markup.add(btn_jpg, btn_png)
        markup.add(btn_back)
        bot.edit_message_text("Choose the output format:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# Step 4: Handle format conversion and ask for enhancements
@bot.callback_query_handler(func=lambda call: call.data.startswith('convert_') or call.data == 'back_resolution')
def handle_conversion(call):
    global last_processed_image, current_format

    if call.data == 'back_resolution':
        # Go back to the resolution step
        handle_photo(call.message)
        return

    format = call.data.split('_')[1]

    if last_processed_image:
        last_processed_image.seek(0)
        image = Image.open(last_processed_image)
        
        # Save the image in the selected format
        last_processed_image = io.BytesIO()
        image.save(last_processed_image, format=format.upper())
        last_processed_image.seek(0)
        current_format = format

        # Ask for enhancements
        markup = types.InlineKeyboardMarkup()
        btn_brightness = types.InlineKeyboardButton("Enhance Brightness", callback_data="enhance_brightness")
        btn_contrast = types.InlineKeyboardButton("Enhance Contrast", callback_data="enhance_contrast")
        btn_sharpness = types.InlineKeyboardButton("Enhance Sharpness", callback_data="enhance_sharpness")
        btn_color = types.InlineKeyboardButton("Enhance Color", callback_data="enhance_color")
        btn_next = types.InlineKeyboardButton("Next", callback_data="next_enhancement")
        btn_back = types.InlineKeyboardButton("Back", callback_data="back_format")
        markup.add(btn_brightness, btn_contrast, btn_sharpness, btn_color)
        markup.add(btn_next)
        markup.add(btn_back)
        bot.edit_message_text("Choose enhancement options (You can choose multiple):", call.message.chat.id, call.message.message_id, reply_markup=markup)

# Step 5: Handle enhancement options (allow multiple selections)
@bot.callback_query_handler(func=lambda call: call.data.startswith('enhance_') or call.data in ['next_enhancement', 'back_format'])
def handle_enhancement(call):
    global last_processed_image, enhancements_applied

    if call.data == 'back_format':
        # Go back to the format selection step
        handle_resolution(call)
        return

    if call.data == 'next_enhancement':
        # Proceed to the next step
        show_summary(call.message)
        return

    enhancement_type = call.data.split('_')[1]

    if last_processed_image:
        last_processed_image.seek(0)
        image = Image.open(last_processed_image)

        # Apply selected enhancement
        if enhancement_type == 'brightness':
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.5)
        elif enhancement_type == 'contrast':
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
        elif enhancement_type == 'sharpness':
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
        elif enhancement_type == 'color':
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.5)

        # Save the enhanced image
        last_processed_image = io.BytesIO()
        image.save(last_processed_image, format=image.format)
        last_processed_image.seek(0)
        enhancements_applied.append(enhancement_type.capitalize())

        bot.answer_callback_query(call.id, f"{enhancement_type.capitalize()} enhancement applied! Choose another or proceed to sending.")

# Step 6: Final step - Show summary and choose sending method
def show_summary(message):
    summary = f"Resolution: {current_resolution}\nFormat: {current_format}\nEnhancements: {', '.join(enhancements_applied)}"
    
    markup = types.InlineKeyboardMarkup()
    btn_send_photo = types.InlineKeyboardButton("Send as Photo", callback_data="send_photo")
    btn_send_doc = types.InlineKeyboardButton("Send as Document", callback_data="send_doc")
    btn_back = types.InlineKeyboardButton("Back", callback_data="back_enhancement")
    markup.add(btn_send_photo, btn_send_doc)
    markup.add(btn_back)
    
    bot.send_message(message.chat.id, f"Summary:\n{summary}\nChoose how to send the image:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['send_photo', 'send_doc', 'back_enhancement'])
def handle_output_choice(call):
    global last_processed_image

    if call.data == 'back_enhancement':
        # Go back to the enhancement selection step
        handle_conversion(call)
        return

    if last_processed_image:
        last_processed_image.seek(0)
        
        if call.data == 'send_photo':
            bot.send_photo(call.message.chat.id, photo=last_processed_image, caption="Here is your processed image.")
        elif call.data == 'send_doc':
            bot.send_document(call.message.chat.id, document=last_processed_image, caption="Here is your processed image.")
    else:
        bot.send_message(call.message.chat.id, "No image processed yet. Please upload an image first.")

# Run the bot
bot.polling()
