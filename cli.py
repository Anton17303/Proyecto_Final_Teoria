from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from .config_loader import load_specification
from .machine import TuringMachine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulador de Máquinas de Turing basado en configuraciones YAML",
    )
    parser.add_argument("config", type=Path, help="Ruta al archivo YAML de configuración")
    parser.add_argument(
        "--string",
        "-s",
        dest="strings",
        action="append",
        help="Cadena específica que se desea simular. Puede repetirse",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10_000,
        help="Número máximo de pasos permitidos antes de detener la simulación",
    )
    parser.add_argument(
        "--no-ids",
        dest="capture_ids",
        action="store_false",
        help="Desactiva la impresión de descripciones instantáneas",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Devuelve la salida en formato JSON para facilitar el post-procesamiento",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    spec = load_specification(args.config)
    machine = TuringMachine(spec)
    strings = args.strings if args.strings is not None else spec.simulation_strings
    if not strings:
        parser.error(
            "No se especificaron cadenas para simular. Añada 'simulation_strings' en el YAML o use --string",
        )

    results = machine.simulate_inputs(strings, max_steps=args.max_steps, capture_ids=args.capture_ids)

    if args.json_output:
        payload = {
            input_string: {
                "accepted": result.accepted,
                "halted": result.halted,
                "reason": result.reason,
                "steps": result.steps,
                "ids": [id_.__dict__ for id_ in result.ids] if args.capture_ids else [],
            }
            for input_string, result in results.items()
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    for string, result in results.items():
        header = f"Cadena '{string}'"
        print("=" * len(header))
        print(header)
        print("=" * len(header))
        print(f"Aceptada: {'sí' if result.accepted else 'no'}")
        print(f"Motivo: {result.reason}")
        print(f"Pasos ejecutados: {result.steps}")
        if args.capture_ids:
            print("Descripciones instantáneas:")
            for id_ in result.ids:
                print(id_.format())
        print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())