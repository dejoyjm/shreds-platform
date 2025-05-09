def scan_for_core_references(base_dir):
    print(f"🔍 Scanning for 'core' under: {base_dir}\n")

    for root, dirs, files in os.walk(base_dir):
        # Skip virtual environments
        if "venv" in root or "venv311" in root:
            continue

        for file in files:
            if file.endswith(ALLOWED_EXTENSIONS):
                path = os.path.join(root, file)
                try:
                    with open(path, encoding="utf-8") as f:
                        for i, line in enumerate(f, start=1):
                            if SEARCH_TERM in line:
                                print(f"{path}:{i} → {line.strip()}")
                except Exception as e:
                    print(f"⚠️ Skipped {path} due to: {e}")
