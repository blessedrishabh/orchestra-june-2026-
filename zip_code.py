import os
import zipfile

def zip_code_directory(source_dir, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude unwanted directories
            dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', '.git']]
            for file in files:
                # Exclude scratch scripts if any
                if file in ['check_output.py', '.env']:
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)
                print(f"Added {arcname}")

if __name__ == '__main__':
    zip_code_directory('code', 'code.zip')
    print("\nSuccessfully created code.zip")
