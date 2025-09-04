import sys
from ruamel.yaml import YAML

# --- Main Script Logic ---

# Check for a file path argument
if len(sys.argv) < 2:
    print("Usage: python your_script_name.py <path_to_yml_file>", file=sys.stderr)
    sys.exit(1)

file_path = sys.argv[1]

# Instantiate the YAML parser
yaml = YAML(typ='safe') # 'safe' is equivalent to yaml.safe_load

try:
    with open(file_path, 'r') as file:
        lines = file.readlines()
        clean_lines = [line for line in lines if not line.strip().startswith('{{{')]
        cleaned_content = "".join(clean_lines)
        
        # Use the .load() method from the ruamel.yaml instance
        data = yaml.load(cleaned_content)
        
        description = data.get('description')
        
        if description:
            # Print the raw value to stdout
            print(description)
            sys.exit(0) # Success
        else:
            print(f"Error: The key 'description' was not found in '{file_path}'.", file=sys.stderr)
            sys.exit(1) # Failure

except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.", file=sys.stderr)
    sys.exit(1)
except Exception as e: # Broader exception for ruamel.yaml parsing errors
    print(f"Error parsing YAML file: {e}", file=sys.stderr)
    sys.exit(1)