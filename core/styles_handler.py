import os

directory = "/ui/styles"  # change this to your target directory

def load_styles():
    tcss_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".tcss"):
                tcss_files.append(os.path.join(root, file))

    return tcss_files
