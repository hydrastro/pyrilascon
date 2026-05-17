# Project checkpoint bundle

The project checkpoint bundle is the archiveable handoff artifact for the current
stream-native ASCON development stage.

Generate it with:

```sh
make project-checkpoint-bundle
```

The default output is:

```text
build/project_checkpoint_bundle/
build/project_checkpoint_bundle.zip
```

The bundle contains:

- `checkpoint.json` and `checkpoint.md`: bundle metadata and report summary;
- `project_status.json` and `project_status.md`: the implementation/verification
  status snapshot;
- `board_manifest.json`: the Tang Nano 9K NEORV32 stream memory-map contract;
- `files/`: copied evidence paths, including RTL, firmware, tests, board
  manifests, and documentation referenced by the status report.

This target is intended for project reports, supervisor handoff, and release
checkpoints. It does not synthesize hardware or program a board. The next hard
engineering gate remains the real Tang Nano/NEORV32 build plus strict UART
benchmark capture.

You can validate an existing bundle directly with:

```sh
PYTHONPATH=. python tools/generate_project_checkpoint_bundle.py --check
```
