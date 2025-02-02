import os
import time
import json
import shutil
import werkzeug.datastructures as ds
from flask import Response, send_file
from utils.storage_pojos import HttpJsonResponse, ModelList
from utils.utils import HISTORY, DEFAULT, FILES_DIRECTORY
import modelhost_talker as mh_talker


def save_file(file: ds.FileStorage, tag: str, file_name: str, description: str):
    MODEL_ROOT_DIR = os.path.join(FILES_DIRECTORY, tag)
    history_file = os.path.join(MODEL_ROOT_DIR, HISTORY)
    default_file = os.path.join(MODEL_ROOT_DIR, DEFAULT)

    # Create a new model storage directory
    if not os.path.exists(MODEL_ROOT_DIR):
        os.makedirs(MODEL_ROOT_DIR)
        open(history_file, 'x')
        open(default_file, 'x')
        with open(history_file, "w") as hf:
            hf.write('{}')
        with open(default_file, "w") as lf:
            lf.write('0')

    # Check the default file to find the version of the new file
    with open(os.path.join(MODEL_ROOT_DIR, DEFAULT), 'r') as default:
        last_directory = int(default.read())
        new_directory_version = str(last_directory + 1)
        model_path = os.path.join(MODEL_ROOT_DIR, new_directory_version)

    # Check the existence of the version directory and save it
    if not os.path.exists(model_path):
        os.makedirs(model_path)

    model_location = os.path.join(model_path, file_name)
    file.save(model_location)

    # Update history file
    with open(os.path.join(MODEL_ROOT_DIR, HISTORY), 'r+') as fh:
        data = json.load(fh)
        ts = time.time()
        time_string = time.strftime('%H:%M:%S %d/%m/%Y', time.localtime(ts))
        data[new_directory_version] = {"path": model_path, "file": file_name,
                                       "time": time_string, "description": description}
        fh.seek(0)
        fh.write(json.dumps(data, sort_keys=True))
        fh.close()

    # Rewrite the default file with the new version
    with open(os.path.join(MODEL_ROOT_DIR, DEFAULT), 'w') as fl:
        fl.write(new_directory_version)


def delete_file(name: str, version: str):
    default_file = os.path.join(FILES_DIRECTORY, name, DEFAULT)
    history_file = os.path.join(FILES_DIRECTORY, name, HISTORY)

    directories = []

    # Clean the history file
    with open(history_file, 'r') as hf:
        data_history = json.load(hf)
        for i in data_history:
            i = int(i)
            directories.append(i)
        if version == 'default':
            version = directories[-1]
        del data_history[str(version)]

    no_files = False

    # Check if the directory will be empty
    try:
        new_default_file = directories[-2]
    except IndexError:
        no_files = True

    # If the directory is empty: remove. Else: manage versions
    if no_files:
        tag_directory = os.path.join(FILES_DIRECTORY, name)
        shutil.rmtree(tag_directory)
    else:
        # Open the default file and check the file version
        with open(default_file, 'r') as lf:
            data_default = lf.read()
            if data_default == version or version == 'default':
                version = data_default
            lf.close()

        # Rewrite the default file with the last version available
        with open(default_file, 'w') as lf:
            if int(data_default) == int(version):
                lf.write(str(new_default_file))
            else:
                lf.write(data_default)
            lf.close()

        # Rewrite the history file without the information of the removed file
        with open(history_file, 'w') as hf:
            hf.write(json.dumps(data_history, sort_keys=True))
            hf.close()

        # Remove the file
        directory_file = os.path.join(FILES_DIRECTORY, name, str(version))
        shutil.rmtree(directory_file)


def download_file(name: str, version: str):
    # Return the file
    try:
        # Check default file
        if version == 'default':
            with open(os.path.join(FILES_DIRECTORY, name, DEFAULT), 'r') as df:
                version = df.read()
                df.close()
        directory_path = os.path.join(FILES_DIRECTORY, name, version)

        file_name = os.listdir(directory_path)[0]
        file = os.path.join(directory_path, file_name)
        return send_file(path_or_file=file,
                         mimetype='application/octet-stream',
                         as_attachment=True,
                         download_name=file_name)
    except FileNotFoundError:
        return HttpJsonResponse(
            422, http_status_description='File not found, please check the model name is correct!').get_response()


def get_directory_file(tag: str):
    with open(os.path.join(FILES_DIRECTORY, tag, DEFAULT), 'r') as df:
        version = df.read()
        df.close()
    directory_path = os.path.join(FILES_DIRECTORY, tag, version)
    file_name = os.listdir(directory_path)[0].__str__()
    path_file = os.path.join(directory_path, file_name)
    return path_file


def update_default(name: str, version: str):
    version = str(version)
    directory_path = os.path.join(FILES_DIRECTORY, name)

    try:
        new_default_file = os.listdir(
            os.path.join(directory_path, version))[0]
    except FileNotFoundError:
        return HttpJsonResponse(
            422,
            http_status_description='Version not found, please check the version!').get_response()

    try:
        # Rewrite .default file with the new default tag
        with open(os.path.join(directory_path, DEFAULT), 'w') as lf:
            lf.write(version)
            lf.close()

        response = HttpJsonResponse(
            200,
            http_status_description=f'The tag {name} with the version {version} has been set as default').get_response()

    except FileNotFoundError:
        response = HttpJsonResponse(
            422,
            http_status_description='File not found, please check the model name!').get_response()

    return response


def get_information(name: str):
    directory_path = os.path.join(FILES_DIRECTORY, name)

    # Read the history file
    with open(os.path.join(directory_path, HISTORY), 'r') as hf:
        data = hf.read()
        output = json.loads(data)
        return output


def get_model_list():
    model_list = []

    for model_directory in os.listdir(FILES_DIRECTORY):

        with open(os.path.join(FILES_DIRECTORY, model_directory, DEFAULT), 'r') as df:
            version = df.read()
            df.close()

        directory_path = os.path.join(
            FILES_DIRECTORY, model_directory, version)

        file_name = os.listdir(directory_path)[0]

        if file_name is not None:
            model_list.append(file_name)
        else:
            pass

    return ModelList(
        200, http_status_description='Model list provided', model_list=model_list).get_response()


def update_models():
    for tag in os.listdir(FILES_DIRECTORY):
        with open(os.path.join(FILES_DIRECTORY, tag, DEFAULT), 'r') as df:
            version = df.read()
            df.close()

        path_file = os.path.join(FILES_DIRECTORY, tag, version)
        filename = os.listdir(path_file)[0]
        filedirectory = os.path.join(path_file, filename)
        mh_talker.upload_new_model(tag=tag, new_model=open(filedirectory, 'rb'), filename=filename)

    response = HttpJsonResponse(
        200,
        http_status_description=f'Models updated successful').get_response()
    return response
