from flask import Flask, render_template, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
import re
import requests
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

refresh=False
# Paths to the directories containing your images
import os

PARENT_FOLDER = r'F:\GBData\__SCREENIMAGES__\__SCREENS__'

IMAGE_FOLDERS = {
    folder: os.path.join(PARENT_FOLDER, folder)
    for folder in os.listdir(PARENT_FOLDER)
    if os.path.isdir(os.path.join(PARENT_FOLDER, folder))
}

print(list(IMAGE_FOLDERS.keys())
)


# Global variables to store the list of images
images = {key: [] for key in IMAGE_FOLDERS.keys()}

# =========================================================
# DISPLAY STATUS / HEARTBEAT
# =========================================================

display_status = {
    page: {
        "sid": None,
        "current_media": None,
        "last_seen": 0
    }
    for page in IMAGE_FOLDERS.keys()
}

def preserve_order_sort(files):
    sorted_files = []
    
    for file in files:
        match = re.match(r"(\d+)-(.+)", file)  # Match "30-openhouse.JPG"
        if match:
            prefix, name = match.groups()  # Extract number and name after it
            sorted_files.append((name.lower(), file))
        else:
            sorted_files.append((file.lower(), file))  # Keep non-numbered files in order

    # Sort based on extracted name for numbered files but keep original order otherwise
    sorted_files.sort(key=lambda x: x[0])

    return [x[1] for x in sorted_files]  # Return sorted filenames
def update_image_list(page):
    global images
    folder = IMAGE_FOLDERS[page]

    files = [
        f for f in os.listdir(folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4')) 
        and f.lower() != "background.jpg"
    ]

    images[page] = preserve_order_sort(files)
    # Print the sorted list
    print(images[page])
class ImageFolderHandler(FileSystemEventHandler):
    def __init__(self, page):
        self.last_run_time = 0
        super().__init__()
        self.page = page
      

    def on_modified(self, event):
        if time.time() - self.last_run_time > 20:  # Wait 20 seconds to avoid rapid reprocessing
            self.last_run_time = time.time()
            self._update_images()

    def on_created(self, event):
        self.on_modified(event)

    def on_deleted(self, event):
        self.on_modified(event)

    def _update_images(self):
        update_image_list(self.page)
        updatePage(self.page)
        
def updatePage(page):
    print("Updated")
    socketio.start_background_task(target=emit_update_images, page=page)

def emit_update_images(page):
    socketio.emit('message', "updated")
    socketio.emit('update_images', {'page': page, 'images': images[page]})

@app.route('/')
def index():
    return render_template('main2.html', FOLDER_NAMES = list(IMAGE_FOLDERS.keys())
 )
@app.route('/calc')
def calc():
    return render_template('calc.html', FOLDER_NAMES = list(IMAGE_FOLDERS.keys())
 )

@app.route('/Refresh')
def refresh():
    socketio.emit('refresh', "connected")
    return 'All pages refreshed'
# ---- Add this near other routes in appnew.py ----

from flask import render_template, send_from_directory

import os
@app.route('/proxy')
def proxy():
    import requests
    from flask import Response

    target = "https://vangoghdesigns.com/"
    resp = requests.get(target)
    headers = dict(resp.headers)

    # Remove the security headers that block iframes
    headers.pop("Content-Security-Policy", None)
    headers.pop("X-Frame-Options", None)

    return Response(resp.content, mimetype='text/html')

@app.route('/webframe')
def webframe():
    """Render the main web frame page with the hamburger and iframe."""
    # You can pass dynamic URLs or files here if needed
    links = [
        {"name": "🏠 Company Website", "url": "/proxy"},
        {"name": "📘 Product Catalog", "url": "/static/cat (1).pdf"},
        {"name": "📄 User Manual", "url": "/static/cat (2).pdf"},
        {"name": "🌐 Example External Page", "url": "/static/cat (3).pdf"},
    ]
    default_url = links[0]["url"]
    return render_template('webframe.html', links=links, default_url=default_url)


@app.route('/static/pdfs/<path:filename>')
def serve_pdf(filename):
    """Serve PDF files stored under static/pdfs/"""
    pdf_dir = os.path.join(app.root_path, 'static', 'pdfs')
    return send_from_directory(pdf_dir, filename)

@app.route('/api/displays')
def api_displays():
    now = time.time()
    result = {}

    for screen, info in display_status.items():
        age = now - info["last_seen"] if info["last_seen"] else None

        if age is None:
            status = "offline"
        elif age < 30:
            status = "online"
        elif age < 90:
            status = "stale"
        else:
            status = "offline"

        result[screen] = {
            "status": status,
            "current_media": info["current_media"],
            "last_seen_seconds": round(age, 1) if age is not None else None
        }

    return jsonify(result)
@app.route('/displays')
def displays_dashboard():
    return render_template(
        'displays.html',
        FOLDER_NAMES=list(IMAGE_FOLDERS.keys())
    )

@app.route('/<page>')
def page(page):
    if page not in IMAGE_FOLDERS:
        return 'Page not found', 404
    update_image_list(page)

    return render_template('index.html', page=page, images=images[page])

@app.route('/images/<page>/<filename>')
def image(page, filename):
    if page not in IMAGE_FOLDERS:
        return 'Page not found', 404
    folder = IMAGE_FOLDERS[page]
    print(folder)
    return send_from_directory(folder, filename)

@app.route('/api/images/<page>')
def api_images(page):
    if page not in IMAGE_FOLDERS:
        return 'Page not found', 404
    update_image_list(page)
    return jsonify(images[page])

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    socketio.emit('message', "connected")
    

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join')
def handle_join(room):
    join_room(room)
    emit('message', f'Client has joined the room {room}', room=room)

@socketio.on('leave')
def handle_leave(room):
    leave_room(room)
    emit('message', f'Client has left the room {room}', room=room)

@socketio.on('display_register')
def handle_display_register(data):
    screen = data.get('screen')

    if screen not in display_status:
        print(f"Unknown display attempted registration: {screen}")
        return

    display_status[screen]["sid"] = request.sid
    display_status[screen]["last_seen"] = time.time()

    # Each physical display gets its own Socket.IO room
    room = f"display:{screen}"
    join_room(room)

    print(f"DISPLAY ONLINE: {screen} | SID: {request.sid}")

    emit('display_registered', {
        'screen': screen,
        'status': 'online'
    })


@socketio.on('refresh_display')
def handle_refresh_display(data):
    screen = data.get('screen')

    if screen not in display_status:
        return

    print(f"REMOTE REFRESH: {screen}")

    socketio.emit(
        'refresh',
        {'reason': 'remote'},
        room=f"display:{screen}"
    )

@socketio.on('display_heartbeat')
def handle_display_heartbeat(data):
    screen = data.get('screen')
    current_media = data.get('current_media')

    if screen not in display_status:
        return

    display_status[screen]["sid"] = request.sid
    display_status[screen]["current_media"] = current_media
    display_status[screen]["last_seen"] = time.time()

def start_observers():
    observers = []
    for page, folder in IMAGE_FOLDERS.items():
        event_handler = ImageFolderHandler(page)  
        observer = Observer()
        observer.schedule(event_handler, path=folder, recursive=False)
        observer.start()
        observers.append(observer)
        print(f"Started observing {folder}")

   
if __name__ == '__main__':
    start_observers()
    
    socketio.run(app, host='0.0.0.0', port=80, debug=False)
