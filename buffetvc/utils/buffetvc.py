import os
import time
import json
import shutil
import werkzeug.datastructures as ds

archivos_folder = "files"
extern_folder = 'modelhostfiles'


def save_file(file: ds.FileStorage, tag: str, file_name: str):
    model_folder = os.path.join(archivos_folder, tag)
    # Creation of the name folder to the model and the history/latest files
    if not os.path.exists(model_folder):
        os.makedirs(model_folder)
        history_file = os.path.join(model_folder, '.history')
        latest_file = os.path.join(model_folder, '.latest')
        open(history_file, 'x')
        open(latest_file, 'x')
        with open(history_file, "w") as hf:
            hf.write('{}')
        with open(latest_file, "w") as hf:
            hf.write('0')

    # Check the latest file to find the version of the new file
    with open(os.path.join(model_folder, '.latest'), 'r') as fl:
        last_folder = int(fl.read())
        new_folder = str(last_folder + 1)
        folder_dir = os.path.join(model_folder, new_folder)

    # Check the existence of the version folder
    if not os.path.exists(folder_dir):
        os.makedirs(folder_dir)

    # Save the file
    intern_path = os.path.join(folder_dir, file_name)
    file.save(intern_path)

    # Rewrite the history file with the new data
    with open(os.path.join(model_folder, '.history'), 'r+') as fh:
        data = json.load(fh)
        ts = time.time()
        time_string = time.strftime('%H:%M:%S %d/%m/%Y', time.localtime(ts))
        data[new_folder] = {"folder": folder_dir, "file": file_name, "time": time_string, "timestamp": ts}
        fh.seek(0)
        fh.write(json.dumps(data, sort_keys=True))
        fh.close()

    # Rewrite the latest file with the new version
    with open(os.path.join(model_folder, '.latest'), 'w') as fl:
        fl.write(new_folder)

    # Save the file into the bind volume shared with the modelhosts
    extern_model_folder = os.path.join(extern_folder, tag)
    if not os.path.exists(extern_model_folder):
        os.makedirs(extern_model_folder)
    extern_path = os.path.join(extern_model_folder, file_name)

    # Check if extern_path is empty, if not, remove the file inside
    if len(os.listdir(extern_model_folder)) != 0:
        for file_to_remove in os.listdir(extern_model_folder):

            print(f'file_to_remove: {file_to_remove}')

            filer = os.path.join(extern_model_folder, file_to_remove)
            print(filer)
            os.remove(filer)

    shutil.copy(intern_path, extern_path)


def remove_file(name: str, version: str):
    latest_file = os.path.join(archivos_folder, name, '.latest')
    history_file = os.path.join(archivos_folder, name, '.history')

    folders = []

    # Open the history file and removes the data of the file
    with open(history_file, 'r') as hf:
        data_history = json.load(hf)
        for i in data_history:
            i = int(i)
            folders.append(i)
        if version == 'latest':
            version = folders[-1]
        del data_json[str(version)]

    with open(latest_file, 'r') as fl:
        data = fl.read()
        if data == version or version == 'latest':
            version = data
        fl.close()
    with open(latest_file, 'w') as fl:
        if int(data) == int(version):
            fl.write(str(folders[-1]-1))
        else:
            fl.write(data)
        fl.close()

    with open(history_file, 'w') as fh:
        fh.write(json.dumps(data_json, sort_keys=True))
        fh.close()
    folder_file = os.path.join(archivos_folder, name, str(version))
    shutil.rmtree(folder_file)
