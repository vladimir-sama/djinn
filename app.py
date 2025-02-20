from flask import Flask, send_from_directory, render_template, redirect, abort, jsonify, url_for, request, session
import time, datetime, string, re, os, sys, glob, json, subprocess, threading, random, secrets
from typing import Dict, TypedDict, Any, Callable, Tuple, Union, Optional, List, Set, NotRequired
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from mimetypes import guess_type
import shlex

class Game(TypedDict):
    title:str
    image:str
    description:str
    command:List[str]
    is_shell:bool
    time_played:int
    last_played:int
    time_added:int


file_dir : str = os.path.dirname(os.path.realpath(__file__))
frozen_dir = os.path.dirname(sys.executable)
executable_dir : str = file_dir
if getattr(sys, 'frozen', False):
    executable_dir = os.path.dirname(sys.executable)
config_directory : str = os.path.join(executable_dir, 'config')
config_file : str = os.path.join(config_directory, 'config.json')

thread_dict : Dict[str, List[Union[threading.Thread, bool]]] = {}

library_items : Dict[str, Game] = {}

if os.path.isfile(config_file):
    with open(config_file, 'r') as file:
        library_items = json.load(file)

def save_config() -> None:
    with open(config_file, 'w') as file:
        json.dump(library_items, file, indent=4)

app : Flask = Flask(__name__)

@app.route('/')
def library() -> Union[str, Any]:
    view_library_items : Dict[str, Game] = library_items.copy()
    for game in view_library_items.values():
        game['time_added_str'] = datetime.datetime.fromtimestamp(game['time_added']).strftime('%d/%m/%Y %H:%M')
        game['last_played_str'] = datetime.datetime.fromtimestamp(game['last_played']).strftime('%d/%m/%Y %H:%M') if game['last_played']  > 0 else 'never'
    return render_template('library.html', library_items=view_library_items, thread_items=thread_dict)

@app.route('/info/')
def info() -> Union[str, Any]:
    return render_template('info.html')

@app.route('/add', methods=['GET', 'POST'])
def add_item() -> Union[str, Any]:
    if request.method == 'POST':
        item_title : Optional[str] = request.form.get('item_name')
        item_command : Optional[str] = request.form.get('item_command')
        item_is_shell : Optional[str] = request.form.get('item_shell')
        item_icon : Optional[FileStorage] = request.files.get('item_icon')
        if not item_title:
            return render_template('add.html', message_errors='Title is empty')
        if item_title in [item['title'] for item in library_items.values()]:
            return render_template('add.html', message_errors='Title already exists')
        if not item_command:
            return render_template('add.html', message_errors='Command is empty')
        item_id : str = ''.join(secrets.choice(string.digits) for _ in range(6))
        while item_id in library_items.keys():
            item_id = ''.join(secrets.choice(string.digits) for _ in range(6))
        image : str = 'light_tiles.png'
        if item_icon:
            file_name : str = item_id + '.' + item_icon.filename.rsplit('.', 1)[1].lower()
            item_icon.save(os.path.join(config_directory, file_name))
            image = file_name
        library_items[item_id] = {
            'title' : item_title,
            'image' : image,
            'command' : shlex.split(item_command),
            'is_shell' : item_is_shell == 'on',
            'last_played' : 0,
            'time_played' : 0,
            'time_added' : int(time.time()),
        }
        save_config()
        return redirect(url_for('library'))
    return render_template('add.html')

@app.route('/image/<item_id>')
def item_image(item_id:str) -> Union[str, Any]:
    if not item_id in library_items.keys():
        abort(404)
    return send_from_directory(config_directory, library_items[item_id]['image'])

@app.route('/exec/<item_id>')
def exec_item(item_id:str) -> Union[str, Any]:
    if not item_id in library_items.keys():
        abort(404)
    if item_id in thread_dict.keys():
        thread_dict[item_id][1] = False
        thread_dict[item_id][0].join()
        return redirect(url_for('library'))
    t : threading.Thread = threading.Thread(None, lambda: run_command(item_id))
    t.daemon = False
    t.start()
    library_items[item_id]['last_played'] = int(time.time())
    save_config()
    thread_dict[item_id] = [t, True]
    return redirect(url_for('library'))

def run_command(item_id:str) -> None:
    time_started : int = int(time.time())
    process : subprocess.Popen = subprocess.Popen(library_items[item_id]['command'], shell=library_items[item_id]['is_shell'])
    while not isinstance(process.poll(), int):
        time.sleep(0.10)
        if not thread_dict[item_id][1]:
            process.kill()
    library_items[item_id]['time_played'] += int(time.time()) - time_started
    save_config()
    thread_dict.pop(item_id)

if __name__ == '__main__':
    try:
        app.run('0.0.0.0', 5555, True)
    except KeyboardInterrupt:
        for t in thread_dict.values():
            t[0].join()
