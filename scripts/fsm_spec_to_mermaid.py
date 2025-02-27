#!/usr/bin/env python3

from pathlib import Path
from auto_dev.fsm.fsm import FsmSpec


if __name__ == "__main__":
    repo_root = Path(__file__).parent 
    path = repo_root / "specs" / "fsms"
    assert path.exists()
    outpath = repo_root / "specs" / "fsms" / "mermaid"
    outpath.mkdir(exist_ok=True)

    for file in path.glob("*.yaml"):
        outfile = outpath / (file.stem + ".mmd")
        try:
            fsm_spec = FsmSpec.from_path(file)
            mermaid = fsm_spec.to_mermaid()
            outfile.write_text(mermaid.strip())
        except Exception as e:
            print(f"\n[ERROR] {file.stem}\n{'-' * (len(file.stem) + 8)}")
            print(f"{e}\n")
