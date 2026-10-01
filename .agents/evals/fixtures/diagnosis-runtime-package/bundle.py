import shutil


def package(source, destination):
    """Assemble a runnable release from the compiler's output."""
    (destination / "bin").mkdir(parents=True)
    shutil.copy2(source / "bin" / "runner", destination / "bin" / "runner")
