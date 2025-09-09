from collections import namedtuple

def find_section_lines(file_contents, sec):
    """
    Parses the given file_contents as YAML to find the section with the given identifier.

    Note that this does not call into the yaml library and thus correctly handles Jinja macros at
    the expense of not being a strictly valid yaml parsing.

    Args:
        file_contents (list of str): The contents of the file, split into lines.
        sec (str): The identifier of the section to find.

    Returns:
        list of namedtuple: A list of namedtuples (start, end) representing the lines where the
                            section exists.
    """
    # Hack to find a global key ("section"/sec) in a YAML-like file.
    # All indented lines until the next global key are included in the range.
    # For example:
    #
    # 0: not_it:
    # 1:     - value
    # 2: this_one:
    # 3:      - 2
    # 4:      - 5
    # 5:
    # 6: nor_this:
    #
    # for the section "this_one", the result [(2, 5)] will be returned.
    # Note that multiple sections may exist in a file and each will be
    # identified and returned.
    section = namedtuple('section', ['start', 'end'])

    sec_ranges = []
    sec_id = sec + ":"
    sec_len = len(sec_id)
    end_num = len(file_contents)
    line_num = 0

    while line_num < end_num:
        if len(file_contents[line_num]) >= sec_len:
            if file_contents[line_num][0:sec_len] == sec_id:
                begin = line_num
                line_num += 1
                while line_num < end_num:
                    nonempty_line = file_contents[line_num]
                    if nonempty_line and file_contents[line_num][0] != ' ':
                        break
                    line_num += 1

                end = line_num - 1
                sec_ranges.append(section(begin, end))
        line_num += 1

    return sec_ranges

def get_section_value(yml_file, sections):
    sections_value = {}
    try:
        with open(yml_file, 'r') as f:
            lines = [line.rstrip() for line in f.readlines()]
        for section in sections:
            found_ranges = find_section_lines(lines, section)
            for start, end in found_ranges:
                print(f"\nFound a section from line {start} to {end}:")
                # Slice the list to get the content. Add 1 to `end` because Python slicing is exclusive.
                section_content = lines[start : end + 1]
                sections_value[section] = section_content
        return sections_value
    except FileNotFoundError:
        print(f"ERROR: The file '{yml_file}' was not found.", file=sys.stderr)

sections_value = get_section_value("sysctl_kernel_yama_ptrace_scope_value.var", ["test"])
print(sections_value)


