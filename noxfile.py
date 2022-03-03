from glob import glob

import nox


@nox.session(name="test-examples", venv_backend="none")
def test_examples(session: nox.Session):
    for example in glob("examples/*/noxfile.py"):
        session.run("nox", "-f", example, external=True)
