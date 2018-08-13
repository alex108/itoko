import os
from io import BytesIO

import magic
from flask import (
    Blueprint, current_app, abort, flash, jsonify, make_response, redirect,
    request, render_template, send_file, url_for
)

from erio_cabinet.crypto import generate_key, DecryptionError
from erio_cabinet.files import file_from_file_storage, read_file
from erio_cabinet.util import request_wants_json, get_content_disposition
from erio_cabinet.shorten import shorten_filename, find_shortened

main_blueprint = Blueprint('main', __name__, template_folder='templates')

# TODO: Delete me when done on Windows
magic = magic.Magic(magic_file='c:\\Windows\\System32\\magic.mgc', mime=True)


@main_blueprint.route('/')
def home_page():
    return render_template('index.html')


@main_blueprint.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', category='error')
        return redirect(url_for('home_page'))

    file = request.files['file']
    # Hacky way to check if the string contained is a true value.
    encrypt = request.form.get('encrypt') in ['1', 'true', 'on']
    permanent = request.form.get('permanent') in ['1', 'true', 'on']
    shorten = request.form.get('shorten') in ['1', 'true', 'on']

    if file.filename == '':
        flash('No file selected', category='error')
        return redirect(url_for('home_page'))

    file = file_from_file_storage(file)

    if encrypt:
        key = generate_key()
        file = file.encrypt(key)

    if permanent:
        folder = current_app.config['PERMANENT_UPLOAD_FOLDER']
    else:
        folder = current_app.config['UPLOAD_FOLDER']

    file.save(folder)

    if encrypt:
        file_url = '{site_url}/u/{filename}?key={key}'.format(
            site_url=current_app.config['SITE_URL'],
            filename=file.filename,
            key=key.decode('utf-8')
        )
    else:
        file_url = '{site_url}/u/{filename}'.format(
            site_url=current_app.config['SITE_URL'],
            filename=file.filename
        )

    if shorten:
        short_name = shorten_filename(file.filename)
        if encrypt:
            short_url = '{site_url}/s/{short_name}?key={key}'.format(
                site_url=current_app.config['SITE_URL'],
                short_name=short_name,
                key=key.decode('utf-8')
            )
        else:
            short_url = '{site_url}/s/{short_name}'.format(
                site_url=current_app.config['SITE_URL'],
                short_name=short_name
            )
    else:
        short_url = None

    if request_wants_json():
        return jsonify(url=file_url, short_url=short_url)
    return render_template('upload_successful.html', file_url=file_url,
                           short_url=short_url)


@main_blueprint.route('/u/<filename>')
@main_blueprint.route('/s/<short_filename>')
def serve_file(filename=None, short_filename=None):
    if not filename:
        if not short_filename:
            abort(404)
        filename = find_shortened(short_filename)
    if not filename:
        return abort(404)

    # Probe permanent folder first, then the temporary folder
    full_filename = os.path.join(current_app.config['PERMANENT_UPLOAD_FOLDER'],
                                 filename)
    if not os.path.exists(full_filename):
        full_filename = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                     filename)
    key = request.args.get('key')

    if not os.path.exists(full_filename):
        return abort(404)

    file = read_file(full_filename)

    if file.is_encrypted():
        try:
            # Put an empty key if none was provided
            file = file.decrypt((key or '').encode('utf-8'))
        except DecryptionError:
            return abort(403)

    mimetype = magic.from_buffer(file.data)  # , mime=True)  TODO: put this back
    io = BytesIO(file.data)
    response = make_response(send_file(io, mimetype=mimetype))

    # Add filename, set as attachment if not allowed inline
    response.headers['Content-Disposition'] = get_content_disposition(
        file.original_filename,
        mimetype
    )
    return response