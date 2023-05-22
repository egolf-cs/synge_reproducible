import os.path

SCENARIOS_PATH = os.path.dirname(os.path.realpath(__file__))


def switch_strings(string, s1, s2):
    return string.replace(s1, "XXXXX").replace(s2, s1).replace("XXXXX", s2)


def prime_last_label(line):
    messages_and_labels = line.split(' ')
    assert messages_and_labels[-1].endswith("L")
    last_label = messages_and_labels[-1]
    last_label = last_label[:-1] + "'L"
    return ' '.join(messages_and_labels[:-1] + [last_label])


TEMP_FILE_PATH = os.path.join(SCENARIOS_PATH, "figures/temp.html")
