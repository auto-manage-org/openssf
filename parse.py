import sys
from ruamel.yaml import YAML
import io

# --- Main Script Logic ---

# 1. Check if enough arguments were provided (script, file, and at least one key)
if len(sys.argv) < 3:
    print("Usage: python your_script_name.py <path_to_yml_file> <key1> [key2] ...", file=sys.stderr)
    sys.exit(1)

# 2. Assign arguments to variables
file_path = sys.argv[1]
keys_to_find = sys.argv[2:]  # Get all arguments from the third one onwards

# Instantiate the YAML parser
yaml = YAML(typ='safe')

try:
    with open(file_path, 'r') as file:
        lines = file.readlines()
        clean_lines = [line for line in lines if not line.strip().startswith('{{{')]
        cleaned_content = "".join(clean_lines)
        data = yaml.load(cleaned_content)

        found_value = None
        # --- MODIFIED: Loop through the keys provided as arguments ---
        for key in keys_to_find:
            if key in data:
                found_value = data.get(key)
                break  # Stop searching once a key is found

        if found_value is not None:
            # If the value is a dictionary or list, dump it back to a YAML string
            if isinstance(found_value, (dict, list)):
                string_stream = io.StringIO()
                yaml.dump(found_value, string_stream)
                print(string_stream.getvalue().strip())
            else:
                # Print the simple string value directly
                print(found_value)
            sys.exit(0)  # Success
        else:
            print(f"Error: None of the specified keys {keys_to_find} were found in '{file_path}'.", file=sys.stderr)
            sys.exit(1)  # Failure

except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error parsing YAML file: {e}", file=sys.stderr)
    sys.exit(1)