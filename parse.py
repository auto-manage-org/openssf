import sys
import yaml

# --- Main Script Logic ---

# Check for a file path argument
if len(sys.argv) < 2:
    # Print error messages to stderr to keep stdout clean
    print("Usage: python your_script_name.py <path_to_yml_file>", file=sys.stderr)
    sys.exit(1) # Exit with an error code

file_path = sys.argv[1]

try:
    with open(file_path, 'r') as file:
        lines = file.readlines()
        clean_lines = [line for line in lines if not line.strip().startswith('{{{')]
        cleaned_content = "".join(clean_lines)
        data = yaml.safe_load(cleaned_content)
        
        description = data.get('description')
        
        if description:
            # --- MODIFIED: Print the raw value to stdout ---
            print(description)
            sys.exit(0) # Exit with a success code
        else:
            print(f"Error: The key 'description' was not found in '{file_path}'.", file=sys.stderr)
            sys.exit(1) # Exit with an error code

except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.", file=sys.stderr)
    sys.exit(1)
except yaml.YAMLError as e:
    print(f"Error parsing YAML file: {e}", file=sys.stderr)
    sys.exit(1)