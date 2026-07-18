from pathlib import Path

def print_tree(path, prefix=""):
    entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "

        if entry.name == "venv":
            print(prefix + connector + "venv/")
            print(prefix + ("    " if i == len(entries) - 1 else "│   ") + "└── ...")
            continue

        print(prefix + connector + entry.name)

        if entry.is_dir():
            extension = "    " if i == len(entries) - 1 else "│   "
            print_tree(entry, prefix + extension)

print_tree(Path("."))