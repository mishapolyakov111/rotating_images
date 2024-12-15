import os
import imghdr
import numpy as np
from flask import Flask, request, render_template, send_from_directory, flash
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm
import logging

app = Flask(__name__)
app.config['GIF_FOLDER'] = "static/gifs"
app.config['IMAGES_FOLDER'] = "static/images"
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Ограничение: 10 MB
app.secret_key = "supersecretkey"  # Для flash-сообщений


def is_image(file_path):
    """Проверяет, является ли файл изображением"""
    valid_image_formats = {"jpeg", "png", "gif", "bmp", "tiff"}
    file_type = imghdr.what(file_path)
    return file_type in valid_image_formats


def create_rotating_frames(img, num_frames, direction):
    diagonal = int(np.ceil((img.width**2 + img.height**2) ** 0.5))
    canvas_size = (diagonal, diagonal)

    frames = []
    for angle in tqdm(np.linspace(0, 360, num_frames, endpoint=False)):
        rotated_frame = img.rotate(direction * angle, resample=Image.BICUBIC, expand=True)

        canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 0))
        offset = ((canvas_size[0] - rotated_frame.width) // 2, (canvas_size[1] - rotated_frame.height) // 2)
        canvas.paste(rotated_frame, offset, rotated_frame)

        final_frame = Image.new("RGB", canvas.size, (255, 255, 255))
        final_frame.paste(canvas, mask=canvas.split()[3])

        frames.append(final_frame.convert("P", dither=Image.NONE))
    return frames


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("image")
        speed = int(request.form.get("speed", 50))  # Скорость кадра в миллисекундах
        num_frames = int(request.form.get("frames", 36))  # Количество кадров
        direction = -1 if request.form.get("direction", "clockwise") == "clockwise" else 1

        if file:
            filepath = os.path.join(app.config['IMAGES_FOLDER'], file.filename)
            file.save(filepath)

            if os.path.exists(filepath):
                print(f"Файл {filepath} успешно сохранён.")
            else:
                print(f"Ошибка: файл {filepath} не был сохранён.")

            # Проверка: является ли файл изображением
            if not is_image(filepath):
                os.remove(filepath)  # Удаляем невалидный файл
                flash("Файл не является изображением. Пожалуйста, загрузите допустимый файл.", "error")
                return render_template("index.html")

            # Дополнительная проверка через Pillow (на случай некорректных файлов)
            try:
                img = Image.open(filepath).convert("RGBA")
            except UnidentifiedImageError:
                os.remove(filepath)  # Удаляем файл, если он невалидный
                flash("Не удалось обработать изображение. Загрузите допустимый файл.", "error")
                return render_template("index.html")

            # Создание GIF
            frames = create_rotating_frames(img, num_frames, direction)

            filename_without_ext = os.path.splitext(file.filename)[0]
            gif_path = os.path.join(app.config['GIF_FOLDER'], f"rotating_{filename_without_ext}.gif")
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=speed,
                loop=0,
                disposal=2,
            )
            if os.path.exists(gif_path):
                print(f"Файл {gif_path} успешно сохранён.")
            else:
                print(f"Ошибка: файл {gif_path} не был сохранён.")

            return render_template("index.html", gif_path=f"static/gifs/rotating_{filename_without_ext}.gif")

    return render_template("index.html")


@app.route("/static/gifs/<path:filename>")
def gifs(filename):
    try:
        file_path = os.path.join(app.root_path, 'static/gifs', filename)
        logging.info(f"Trying to serve file: {file_path}")
        return send_from_directory(os.path.join(app.root_path, 'static/gifs'), filename)
    except Exception as e:
        logging.error(f"Error serving file: {str(e)}")
        return "Error serving file", 500


if __name__ == "__main__":
    os.makedirs(app.config['IMAGES_FOLDER'], exist_ok=True)
    os.makedirs(app.config['GIF_FOLDER'], exist_ok=True)

    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    if os.getenv("FLASK_ENV") == "production":
        app.run(host=host, debug=False, port=port)
    else:
        app.run(host=host, debug=True, port=port)