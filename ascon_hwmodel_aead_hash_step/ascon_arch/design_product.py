from pathlib import Path
import json

from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import ArchitectureFamily
from ascon_arch.validation import validate_config


def top_module_name(config: ImplementationConfig) -> str:
    return f"ascon_{config.name}_top"


def emit_top_stub(config: ImplementationConfig) -> str:
    module_name = top_module_name(config)
    topology = config.topology
    lines: list[str] = [
        "// Generated architecture skeleton.",
        "// This file is intentionally a structural placeholder, not the final datapath RTL.",
        f"// Config: {config.name}",
        f"// Target: {config.target.value}",
        f"// Family: {topology.family.value}",
        f"// Engine count: {topology.engine_count}",
        f"// Expected parallel operations: {topology.expected_parallel_operations()}",
        "",
        f"module {module_name} #(",
        f"  parameter integer ENGINE_COUNT = {topology.engine_count}",
        ") (",
        "  input  wire clk,",
        "  input  wire rst_n,",
        "  input  wire start_i,",
        "  output wire ready_o,",
        "  output wire done_o",
        ");",
        "",
    ]
    if topology.family == ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS:
        lines.extend(
            [
                "  // ASIC choice: independent encryption and decryption datapaths.",
                "  // TODO: instantiate encrypt datapath and decrypt datapath once their RTL generators exist.",
                "  assign ready_o = 1'b1;",
                "  assign done_o  = start_i;",
            ]
        )
    elif topology.family == ArchitectureFamily.PARALLEL_ENGINES:
        lines.extend(
            [
                "  // FPGA choice: N parallel engines.",
                "  // TODO: generate ENGINE_COUNT engine instances and arbitration/fanout logic.",
                "  assign ready_o = 1'b1;",
                "  assign done_o  = start_i;",
            ]
        )
    else:
        lines.extend(
            [
                "  // Generic architecture family placeholder.",
                "  assign ready_o = 1'b1;",
                "  assign done_o  = start_i;",
            ]
        )
    lines.extend(["", "endmodule"])
    return "\n".join(lines) + "\n"


def write_design_product(config: ImplementationConfig, output_root: str | Path) -> tuple[Path, ...]:
    validate_config(config)
    root = Path(output_root) / config.name
    rtl_dir = root / "rtl"
    metadata_dir = root / "metadata"
    rtl_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    config_path = metadata_dir / "config_resolved.json"
    config_path.write_text(json.dumps(config.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(config_path)

    manifest = {
        "top_module": top_module_name(config),
        "target": config.target.value,
        "family": config.topology.family.value,
        "engine_count": config.topology.engine_count,
        "expected_parallel_operations": config.topology.expected_parallel_operations(),
        "rtl_files": [f"rtl/{top_module_name(config)}.sv"],
    }
    manifest_path = metadata_dir / "module_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(manifest_path)

    rtl_path = rtl_dir / f"{top_module_name(config)}.sv"
    rtl_path.write_text(emit_top_stub(config), encoding="utf-8")
    written.append(rtl_path)

    readme_path = root / "README.md"
    readme_path.write_text(
        "# Generated ASCON design product\n\n"
        f"Name: `{config.name}`\n\n"
        f"Target: `{config.target.value}`\n\n"
        f"Architecture family: `{config.topology.family.value}`\n\n"
        f"Expected parallel operations: `{config.topology.expected_parallel_operations()}`\n\n"
        "This directory is generated from an architecture configuration. "
        "The current RTL file is a structural placeholder for the next implementation phase.\n",
        encoding="utf-8",
    )
    written.append(readme_path)
    return tuple(written)
