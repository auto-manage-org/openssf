import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")

def handle_detected_updates(file_path):
    """
    Read the file which has the CAC updated files.
    And return the updated controls, profiles, rules and variables
    """

    controls = []
    profile = {}
    profiles = []
    rules = []
    vars = []
    # Open the file and process it line by line
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if 'controls/' in line:
                controlname = line.split('/')[-1].split('.')[0]
                if "SRG-" not in controlname:
                    if "section" in controlname:
                        controlname = 'cis_ocp_1_4_0'
                    controls.append(controlname)
            elif '.profile' in line:
                profile["profile_name"] = line.split('/')[-1].split('.')[0]
                profile["product"] = line.split('/')[1]
                profiles.append(f'{profile}')
            elif 'rule.yml' in line:
                rulename = line.split('/')[-2]
                rules.append(rulename)
            elif '.var' in line and line.endswith('.var'):
                rulename = line.split('/')[-1].split('.')[0]
                vars.append(rulename)
    return controls, profiles, rules, vars
            

def main(file_path):
    controls, profiles, rules, vars = handle_detected_updates(file_path)
    #for i in [controls, profiles, rules, vars]:
    for i in [controls, profiles, rules, vars]:
        logging.info(" ".join(i))
   

if __name__ == "__main__":
    # Ensure that the script is run with the correct number of arguments
    if len(sys.argv) != 2:
        logging.warning("Usage: \
            python handle_detected_updates.py 'file_path'")
        sys.exit(1)
    try:
        # Extract arguments
        file_path = sys.argv[1]  # First argument is file_path
        # Call the main function
        main(file_path)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)