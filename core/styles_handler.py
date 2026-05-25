import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_styles():
    directory = os.path.join(_ROOT, "ui", "styles")
    tcss_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".tcss"):
                tcss_files.append(os.path.join(root, file))
    return tcss_files