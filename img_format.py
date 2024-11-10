import os
import json
from PIL import Image

# Set the directories
base_dir = 'assets'
images_dir = os.path.join(base_dir, 'images')
json_dir = base_dir  # Assuming JSON files are directly under the base 'assets'

# Function to check if a PNG has alpha
def has_alpha(img_path):
    with Image.open(img_path) as img:
        return img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)

# Function to convert PNG to JPG
def convert_to_jpg(png_path):
    jpg_path = png_path.replace('.png', '.jpg')
    with Image.open(png_path) as img:
        rgb_img = img.convert('RGB')  # Convert to RGB
        rgb_img.save(jpg_path, 'JPEG', quality=80)
    return jpg_path

# Function to update JSON files and keep formatting
def update_json_references(old_name, new_name):
    for json_file in os.listdir(json_dir):
        if json_file.endswith('.json'):
            json_path = os.path.join(json_dir, json_file)
            with open(json_path, 'r') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError as e:
                    print(f"Error reading {json_path}: {e}")
                    continue
            
            # Convert data to a string to handle any replacement
            data_str = json.dumps(data, indent=4)  # Preserve formatting
            if old_name in data_str:
                data_str = data_str.replace(old_name, new_name)
                # Write the updated data back to the JSON file
                with open(json_path, 'w') as file:
                    file.write(data_str)
                print(f"Updated {json_file} to replace {old_name} with {new_name}")

# Main script logic
def main():
    for file_name in os.listdir(images_dir):
        if file_name.endswith('.png'):
            png_path = os.path.join(images_dir, file_name)
            if not has_alpha(png_path):
                # Convert to JPG
                jpg_path = convert_to_jpg(png_path)
                print(f"Converted {png_path} to {jpg_path}")
                
                # Remove the original PNG file
                os.remove(png_path)
                print(f"Removed {png_path}")
                
                # Update JSON references
                old_name = os.path.basename(png_path)
                new_name = os.path.basename(jpg_path)
                update_json_references(old_name, new_name)

if __name__ == '__main__':
    main()