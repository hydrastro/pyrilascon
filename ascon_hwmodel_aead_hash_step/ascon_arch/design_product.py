from pathlib import Path
import json

from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import ArchitectureFamily, PermutationStyle, ResetStyle
from ascon_arch.permutation_planning import estimate_permutation
from ascon_arch.datapath_planning import estimate_datapath
from ascon_arch.validation import validate_config


def top_module_name(config: ImplementationConfig) -> str:
    return f"ascon_{config.name}_top"


def engine_module_name(config: ImplementationConfig) -> str:
    return f"ascon_{config.name}_engine"


def encrypt_datapath_module_name(config: ImplementationConfig) -> str:
    return f"ascon_{config.name}_encrypt_datapath"


def decrypt_datapath_module_name(config: ImplementationConfig) -> str:
    return f"ascon_{config.name}_decrypt_datapath"


def permutation_module_name(config: ImplementationConfig) -> str:
    return f"ascon_{config.name}_permutation"


def _reset_condition(config: ImplementationConfig) -> str:
    if config.rtl.reset_style == ResetStyle.ASYNC_ACTIVE_LOW:
        return "!rst_n"
    if config.rtl.reset_style == ResetStyle.SYNC_ACTIVE_LOW:
        return "!rst_n"
    return "rst"


def emit_top_stub(config: ImplementationConfig) -> str:
    """Backward-compatible top emitter used by older tests."""
    return emit_top_module(config)


def emit_top_module(config: ImplementationConfig) -> str:
    module_name = top_module_name(config)
    topology = config.topology
    io = config.io
    lines: list[str] = [
        "// Generated ASCON architecture top-level skeleton.",
        "// This is structural RTL scaffolding; datapath internals are generated in later phases.",
        f"// Config: {config.name}",
        f"// Target: {config.target.value}",
        f"// Family: {topology.family.value}",
        f"// Engine count: {topology.engine_count}",
        f"// Expected parallel operations: {topology.expected_parallel_operations()}",
        "",
        f"module {module_name} #(",
        f"  parameter int ENGINE_COUNT = {topology.engine_count},",
        f"  parameter int DATA_BUS_BITS = {io.data_bus_bits}",
        ") (",
        "  input  logic clk,",
        "  input  logic rst_n,",
        "  input  logic start_i,",
        "  input  logic [DATA_BUS_BITS-1:0] data_i,",
        "  output logic [DATA_BUS_BITS-1:0] data_o,",
        "  output logic ready_o,",
        "  output logic done_o",
        ");",
        "",
    ]

    if topology.family == ArchitectureFamily.PARALLEL_ENGINES:
        engine_width = max(1, io.data_bus_bits // topology.engine_count)
        lines.extend(
            [
                f"  localparam int ENGINE_DATA_BITS = {engine_width};",
                "  logic [ENGINE_COUNT-1:0] engine_ready;",
                "  logic [ENGINE_COUNT-1:0] engine_done;",
                "",
                "  genvar engine_index;",
                "  generate",
                "    for (engine_index = 0; engine_index < ENGINE_COUNT; engine_index = engine_index + 1) begin : gen_engine",
                f"      {engine_module_name(config)} #(",
                "        .ENGINE_ID(engine_index),",
                "        .DATA_BUS_BITS(ENGINE_DATA_BITS)",
                "      ) u_engine (",
                "        .clk(clk),",
                "        .rst_n(rst_n),",
                "        .start_i(start_i),",
                "        .data_i(data_i[(engine_index+1)*ENGINE_DATA_BITS-1 -: ENGINE_DATA_BITS]),",
                "        .data_o(data_o[(engine_index+1)*ENGINE_DATA_BITS-1 -: ENGINE_DATA_BITS]),",
                "        .ready_o(engine_ready[engine_index]),",
                "        .done_o(engine_done[engine_index])",
                "      );",
                "    end",
                "  endgenerate",
                "",
                "  assign ready_o = &engine_ready;",
                "  assign done_o  = &engine_done;",
            ]
        )
    else:
        lines.extend(
            [
                f"  {engine_module_name(config)} #(",
                "    .ENGINE_ID(0),",
                "    .DATA_BUS_BITS(DATA_BUS_BITS)",
                "  ) u_engine (",
                "    .clk(clk),",
                "    .rst_n(rst_n),",
                "    .start_i(start_i),",
                "    .data_i(data_i),",
                "    .data_o(data_o),",
                "    .ready_o(ready_o),",
                "    .done_o(done_o)",
                "  );",
            ]
        )
    lines.extend(["", "endmodule", ""])
    return "\n".join(lines)


def emit_engine_module(config: ImplementationConfig) -> str:
    topology = config.topology
    lines: list[str] = [
        "// Generated ASCON engine skeleton.",
        f"// Permutation style: {config.permutation.style.value}",
        f"// S-box style: {config.permutation.sbox_style.value}",
        f"// Datapath profile: {config.datapath.profile.value}",
        f"// Datapath lane width: {config.datapath.lane_width.bits()}",
        f"// Absorb width: {config.datapath.absorb_width.bits()}",
        "",
        f"module {engine_module_name(config)} #(",
        "  parameter int ENGINE_ID = 0,",
        "  parameter int DATA_BUS_BITS = 128",
        ") (",
        "  input  logic clk,",
        "  input  logic rst_n,",
        "  input  logic start_i,",
        "  input  logic [DATA_BUS_BITS-1:0] data_i,",
        "  output logic [DATA_BUS_BITS-1:0] data_o,",
        "  output logic ready_o,",
        "  output logic done_o",
        ");",
        "",
        "  logic enc_ready;",
        "  logic enc_done;",
        "  logic dec_ready;",
        "  logic dec_done;",
        "  logic [DATA_BUS_BITS-1:0] enc_data_o;",
        "  logic [DATA_BUS_BITS-1:0] dec_data_o;",
        "",
    ]
    if topology.family == ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS:
        lines.extend(
            [
                f"  {encrypt_datapath_module_name(config)} #(.DATA_BUS_BITS(DATA_BUS_BITS)) u_encrypt_datapath (",
                "    .clk(clk), .rst_n(rst_n), .start_i(start_i), .data_i(data_i),",
                "    .data_o(enc_data_o), .ready_o(enc_ready), .done_o(enc_done)",
                "  );",
                "",
                f"  {decrypt_datapath_module_name(config)} #(.DATA_BUS_BITS(DATA_BUS_BITS)) u_decrypt_datapath (",
                "    .clk(clk), .rst_n(rst_n), .start_i(start_i), .data_i(data_i),",
                "    .data_o(dec_data_o), .ready_o(dec_ready), .done_o(dec_done)",
                "  );",
                "",
                "  // Current scaffold exposes aggregate progress; mode-level routing is added in the real engine generator.",
                "  assign ready_o = enc_ready & dec_ready;",
                "  assign done_o  = enc_done  & dec_done;",
                "  assign data_o  = enc_data_o ^ dec_data_o;",
            ]
        )
    else:
        lines.extend(
            [
                "  // Single logical datapath placeholder for this architecture family.",
                f"  {permutation_module_name(config)} u_permutation (",
                "    .clk(clk),",
                "    .rst_n(rst_n),",
                "    .start_i(start_i),",
                "    .rounds_i(2'd2),",
                "    .state_i({320{1'b0}}),",
                "    .state_o(),",
                "    .ready_o(),",
                "    .done_o()",
                "  );",
                "",
                "  assign ready_o = 1'b1;",
                "  assign done_o  = start_i;",
                "  assign data_o  = data_i;",
            ]
        )
    lines.extend(["", "endmodule", ""])
    return "\n".join(lines)


def emit_encrypt_datapath_module(config: ImplementationConfig) -> str:
    return _emit_datapath_module(config, encrypt_datapath_module_name(config), "encrypt")


def emit_decrypt_datapath_module(config: ImplementationConfig) -> str:
    return _emit_datapath_module(config, decrypt_datapath_module_name(config), "decrypt")


def _emit_datapath_module(config: ImplementationConfig, module_name: str, direction: str) -> str:
    return "\n".join(
        [
            f"// Generated ASCON {direction} datapath skeleton.",
            f"// Padding: {config.padding.strategy.value}; length handling: {config.padding.length_handling.value}",
            f"// Datapath profile: {config.datapath.profile.value}; lane={config.datapath.lane_width.bits()}b; absorb={config.datapath.absorb_width.bits()}b; io_word={config.datapath.io_word_width.bits()}b",
            f"module {module_name} #(",
            "  parameter int DATA_BUS_BITS = 128",
            ") (",
            "  input  logic clk,",
            "  input  logic rst_n,",
            "  input  logic start_i,",
            "  input  logic [DATA_BUS_BITS-1:0] data_i,",
            "  output logic [DATA_BUS_BITS-1:0] data_o,",
            "  output logic ready_o,",
            "  output logic done_o",
            ");",
            "",
            f"  {permutation_module_name(config)} u_permutation (",
            "    .clk(clk),",
            "    .rst_n(rst_n),",
            "    .start_i(start_i),",
            "    .rounds_i(2'd2),",
            "    .state_i({320{1'b0}}),",
            "    .state_o(),",
            "    .ready_o(),",
            "    .done_o()",
            "  );",
            "",
            "  assign ready_o = 1'b1;",
            "  assign done_o  = start_i;",
            f"  assign data_o  = data_i; // {direction} datapath behavior is implemented in the next RTL phase.",
            "endmodule",
            "",
        ]
    )


def emit_permutation_module(config: ImplementationConfig) -> str:
    permutation = config.permutation
    estimate = estimate_permutation(permutation)
    lines: list[str] = [
        "// Generated ASCON permutation wrapper skeleton.",
        f"// style={permutation.style.value}, sbox={permutation.sbox_style.value}",
        f"// rounds_per_cycle={permutation.rounds_per_cycle}, sbox_columns_per_cycle={permutation.sbox_columns_per_cycle}",
        f"// p8_cycles={estimate.p8_cycles}, p12_cycles={estimate.p12_cycles}, initiation_interval={estimate.initiation_interval}",
        f"// datapath_profile={config.datapath.profile.value}, lane_width={config.datapath.lane_width.bits()}, absorb_width={config.datapath.absorb_width.bits()}",
        f"// area_class={estimate.area_class}, timing_risk={estimate.timing_risk}",
        f"module {permutation_module_name(config)} #(",
        f"  parameter int ROUNDS_PER_CYCLE = {permutation.rounds_per_cycle},",
        f"  parameter int SBOX_COLUMNS_PER_CYCLE = {permutation.sbox_columns_per_cycle},",
        f"  parameter int PIPELINE_STAGES = {permutation.pipeline_stages},",
        f"  parameter int INITIATION_INTERVAL = {estimate.initiation_interval},",
        f"  parameter int P8_CYCLES = {estimate.p8_cycles},",
        f"  parameter int P12_CYCLES = {estimate.p12_cycles}",
        ") (",
        "  input  logic clk,",
        "  input  logic rst_n,",
        "  input  logic start_i,",
        "  input  logic [1:0] rounds_i, // 0:p6, 1:p8, 2:p12",
        "  input  logic [319:0] state_i,",
        "  output logic [319:0] state_o,",
        "  output logic ready_o,",
        "  output logic done_o",
        ");",
        "",
    ]

    if permutation.style == PermutationStyle.ROUND_SERIAL:
        lines.extend([
            "  // One p_C/p_S/p_L round is evaluated per cycle.",
            "  // TODO: add round counter, round-constant schedule, and state register.",
        ])
    elif permutation.style == PermutationStyle.ROUND_UNROLLED:
        lines.extend([
            "  // A combinational step contains ROUNDS_PER_CYCLE consecutive rounds.",
            "  // TODO: generate a step function and iterate ceil(rounds / ROUNDS_PER_CYCLE) cycles.",
        ])
    elif permutation.style in (PermutationStyle.ROUND_PIPELINED, PermutationStyle.FULLY_UNROLLED_PIPELINED):
        lines.extend([
            "  // Round pipeline: independent contexts/messages are needed for full utilization.",
            "  logic [319:0] pipe_state [0:PIPELINE_STAGES];",
            "  // TODO: populate each stage with one fixed-constant Ascon round and context metadata.",
        ])
    elif permutation.style == PermutationStyle.COLUMN_SERIAL:
        lines.extend([
            "  // Column-serial p_S: only SBOX_COLUMNS_PER_CYCLE of the 64 S-box columns are implemented.",
            "  // TODO: add column counter and serialized p_S/p_L scheduling.",
        ])
    elif permutation.style == PermutationStyle.BIT_SERIAL:
        lines.extend([
            "  // Ultra-small serial permutation core.",
            "  // TODO: add bit/column/round counters and heavily reused boolean datapath.",
        ])
    else:
        lines.append("  // TODO: bind selected permutation generator implementation here.")

    lines.extend([
        "",
        "  assign state_o = state_i;",
        "  assign ready_o = 1'b1;",
        "  assign done_o  = start_i;",
        "endmodule",
        "",
    ])
    return "\n".join(lines)


def design_metrics(config: ImplementationConfig) -> dict[str, object]:
    topology = config.topology
    perm_estimate = estimate_permutation(config.permutation)
    datapath_estimate = estimate_datapath(config.datapath)
    return {
        "expected_parallel_operations": topology.expected_parallel_operations(),
        "engine_count": topology.engine_count,
        "total_encrypt_datapaths": topology.total_encrypt_datapaths(),
        "total_decrypt_datapaths": topology.total_decrypt_datapaths(),
        "permutation_style": config.permutation.style.value,
        "sbox_style": config.permutation.sbox_style.value,
        "rounds_per_cycle": config.permutation.rounds_per_cycle,
        "sbox_columns_per_cycle": config.permutation.sbox_columns_per_cycle,
        "pipeline_stages": config.permutation.pipeline_stages,
        "pipeline_initiation_interval": config.permutation.pipeline_initiation_interval,
        "context_interleaving_required": config.permutation.context_interleaving_required,
        "permutation_latency": perm_estimate.to_dict(),
        "context_count": config.context.context_count,
        "interleave_depth": config.context.interleave_depth,
        "data_bus_bits": config.io.data_bus_bits,
        "datapath_profile": config.datapath.profile.value,
        "lane_width_bits": config.datapath.lane_width.bits(),
        "absorb_width_bits": config.datapath.absorb_width.bits(),
        "io_word_width_bits": config.datapath.io_word_width.bits(),
        "serialized_state_update": config.datapath.serialized_state_update,
        "serialized_absorb": config.datapath.serialized_absorb,
        "datapath_estimate": datapath_estimate.to_dict(),
    }


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

    rtl_files: list[tuple[str, str]] = [
        (f"{top_module_name(config)}.sv", emit_top_module(config)),
        (f"{engine_module_name(config)}.sv", emit_engine_module(config)),
        (f"{permutation_module_name(config)}.sv", emit_permutation_module(config)),
    ]
    if config.topology.family == ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS:
        rtl_files.extend(
            [
                (f"{encrypt_datapath_module_name(config)}.sv", emit_encrypt_datapath_module(config)),
                (f"{decrypt_datapath_module_name(config)}.sv", emit_decrypt_datapath_module(config)),
            ]
        )

    for filename, content in rtl_files:
        path = rtl_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)

    manifest = {
        "top_module": top_module_name(config),
        "target": config.target.value,
        "family": config.topology.family.value,
        "engine_count": config.topology.engine_count,
        "expected_parallel_operations": config.topology.expected_parallel_operations(),
        "rtl_files": [f"rtl/{filename}" for filename, _ in rtl_files],
        "metrics": design_metrics(config),
    }
    manifest_path = metadata_dir / "module_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(manifest_path)

    metrics_path = metadata_dir / "expected_metrics.json"
    metrics_path.write_text(json.dumps(design_metrics(config), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(metrics_path)

    readme_path = root / "README.md"
    readme_path.write_text(
        "# Generated ASCON design product\n\n"
        f"Name: `{config.name}`\n\n"
        f"Target: `{config.target.value}`\n\n"
        f"Architecture family: `{config.topology.family.value}`\n\n"
        f"Expected parallel operations: `{config.topology.expected_parallel_operations()}`\n\n"
        f"Permutation: `{config.permutation.style.value}` / S-box `{config.permutation.sbox_style.value}`\n\n"
        "This directory is generated from an architecture configuration. "
        "The current RTL files are structural placeholders that preserve module boundaries for the next implementation phase.\n",
        encoding="utf-8",
    )
    written.append(readme_path)
    return tuple(written)
