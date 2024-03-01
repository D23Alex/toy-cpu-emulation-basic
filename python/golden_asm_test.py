import yaml
import contextlib
import io
import logging
import os
import tempfile

import machine
import pytest
import translator

golden_dir = os.path.join(os.path.dirname(__file__), 'golden')
filenames = [i for i in os.listdir(golden_dir)]


def literal_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')


@pytest.mark.parametrize("filename", filenames)
def test_translator_asm_and_machine(filename, caplog):
    yaml.add_representer(str, literal_presenter)

    caplog.set_level(logging.DEBUG)

    with open(os.path.join('golden', filename)) as f:
        golden = yaml.safe_load(f)

    with tempfile.TemporaryDirectory() as tmpdirname:
        source = os.path.join(tmpdirname, "source.asm")
        input_stream = os.path.join(tmpdirname, "input.txt")
        target = os.path.join(tmpdirname, "target.o")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["in_stdin"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source, target)
            print("============================================================")
            machine.main(target, input_stream)

        with open(target, encoding="utf-8") as file:
            code = file.read()

        if os.getenv('UPDATE_GOLDEN') is not None and os.getenv('UPDATE_GOLDEN') == "true":
            golden["out_code"] = code
            golden["out_stdout"] = stdout.getvalue()
            golden["out_log"] = caplog.text
            with open(os.path.join('golden', filename), 'w') as f:
                yaml.dump(golden, f)
        else:
            assert code == golden["out_code"]
            assert stdout.getvalue() == golden["out_stdout"]
            assert caplog.text == golden["out_log"]
