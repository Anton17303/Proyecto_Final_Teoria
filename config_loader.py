from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:  # pragma: no cover - ruta habitual
    import yaml
except ModuleNotFoundError:  # pragma: no cover - respaldo offline
    from . import simple_yaml as yaml


@dataclass(frozen=True)
class Transition:
    """Representa una transición de la MT."""

    initial_state: str
    read_symbol: str
    next_state: str
    write_symbol: str
    movement: str
    initial_memory: Optional[str] = None
    next_memory: Optional[str] = None


@dataclass(frozen=True)
class MachineSpecification:
    """Estructura de datos inmutable con la especificación completa."""

    states: List[str]
    initial_state: str
    final_states: List[str]
    input_alphabet: List[str]
    tape_alphabet: List[str]
    blank_symbol: str
    transitions: List[Transition]
    simulation_strings: List[str]
    memory_alphabet: Optional[List[str]] = None
    initial_memory: Optional[str] = None

    def transition_map(self) -> Dict[str, Transition]:
        """Devuelve un diccionario indexado por (estado, símbolo, memoria)."""

        mapping: Dict[str, Transition] = {}
        for transition in self.transitions:
            key = _transition_key(
                transition.initial_state,
                transition.read_symbol,
                transition.initial_memory,
            )
            mapping[key] = transition
        return mapping


def _transition_key(state: str, symbol: str, memory: Optional[str]) -> str:
    return f"{state}|{symbol}|{memory or '*'}"


def _normalize_config(data: Dict) -> Dict:
    """Acepta configuraciones con o sin el nodo 'machine'."""

    if "machine" in data and isinstance(data["machine"], dict):
        return data["machine"]
    return data


def load_specification(path: str | Path) -> MachineSpecification:
    """Carga y valida el archivo YAML que describe la MT."""

    with Path(path).open("r", encoding="utf-8") as handle:
        raw_data = yaml.safe_load(handle)

    if not isinstance(raw_data, dict):
        raise ValueError("El archivo YAML debe describir un objeto mapeo.")

    config = _normalize_config(raw_data)

    def require(key: str) -> Dict:
        if key not in config or not isinstance(config[key], dict):
            raise ValueError(f"El bloque '{key}' es obligatorio y debe ser un objeto.")
        return config[key]

    q_states = require("q_states")
    q_list = list(q_states.get("q_list", []))
    if not q_list:
        raise ValueError("Debe existir al menos un estado en 'q_list'.")
    initial_state = q_states.get("initial")
    if initial_state not in q_list:
        raise ValueError("El estado inicial debe pertenecer a 'q_list'.")
    final_states = q_states.get("final", [])
    if isinstance(final_states, str):
        final_states = [final_states]
    for final_state in final_states:
        if final_state not in q_list:
            raise ValueError(f"El estado final '{final_state}' no pertenece a 'q_list'.")

    alphabet_block = require("alphabet")
    input_alphabet = list(alphabet_block.get("input", []))
    if not input_alphabet:
        raise ValueError("'alphabet.input' debe contener símbolos para la cinta de entrada.")

    tape_alphabet = list(alphabet_block.get("tape", []))
    if not tape_alphabet:
        raise ValueError("'alphabet.tape' debe contener los símbolos disponibles en la cinta.")

    blank_symbol = config.get("blank") or alphabet_block.get("blank")
    if blank_symbol is None:
        raise ValueError("Debe definirse un símbolo en blanco mediante 'blank'.")
    if blank_symbol not in tape_alphabet:
        raise ValueError("El símbolo en blanco debe pertenecer al alfabeto de la cinta.")

    memory_block = config.get("memory") or {}
    memory_alphabet = memory_block.get("alphabet")
    initial_memory = memory_block.get("initial")

    if memory_alphabet is not None:
        memory_alphabet = list(memory_alphabet)
        if initial_memory is None:
            raise ValueError("Cuando se define 'memory.alphabet' debe indicarse 'memory.initial'.")
        if initial_memory not in memory_alphabet:
            raise ValueError("El valor inicial de memoria debe pertenecer a 'memory.alphabet'.")

    transition_block = config.get("delta")
    if not isinstance(transition_block, Iterable):
        raise ValueError("El bloque 'delta' debe ser una lista de transiciones.")

    transitions = []
    valid_movements = {"L", "R", "S"}
    for index, raw_transition in enumerate(transition_block):
        params = raw_transition.get("params") if isinstance(raw_transition, dict) else None
        output = raw_transition.get("output") if isinstance(raw_transition, dict) else None
        if not isinstance(params, dict) or not isinstance(output, dict):
            raise ValueError("Cada transición debe incluir los nodos 'params' y 'output'.")

        initial_state_transition = params.get("initial_state")
        read_symbol = params.get("tape_input")
        initial_memory_value = params.get("mem_cache_value")

        if initial_state_transition not in q_list:
            raise ValueError(f"Estado no válido en transición #{index}: {initial_state_transition!r}.")
        if read_symbol not in tape_alphabet:
            raise ValueError(f"Símbolo no válido en transición #{index}: {read_symbol!r}.")
        if initial_memory_value is not None and memory_alphabet is not None:
            if initial_memory_value not in memory_alphabet:
                raise ValueError(
                    f"Valor de memoria inválido en transición #{index}: {initial_memory_value!r}."
                )

        next_state = output.get("final_state")
        write_symbol = output.get("tape_output")
        movement = output.get("tape_displacement")
        next_memory_value = output.get("mem_cache_value")

        if next_state not in q_list:
            raise ValueError(f"Estado destino no válido en transición #{index}: {next_state!r}.")
        if write_symbol not in tape_alphabet:
            raise ValueError(f"Símbolo de escritura no válido en transición #{index}: {write_symbol!r}.")
        if movement not in valid_movements:
            raise ValueError(
                f"Movimiento inválido en transición #{index}: {movement!r}. Valores permitidos: {valid_movements}."
            )
        if next_memory_value is not None and memory_alphabet is not None:
            if next_memory_value not in memory_alphabet:
                raise ValueError(
                    f"Valor de memoria resultante inválido en transición #{index}: {next_memory_value!r}."
                )

        transitions.append(
            Transition(
                initial_state=initial_state_transition,
                read_symbol=read_symbol,
                next_state=next_state,
                write_symbol=write_symbol,
                movement=movement,
                initial_memory=initial_memory_value,
                next_memory=next_memory_value,
            )
        )

    simulation_strings = raw_data.get("simulation_strings") or config.get("simulation_strings") or []
    if isinstance(simulation_strings, str):
        simulation_strings = [simulation_strings]
    simulation_strings = [str(value) for value in simulation_strings]

    return MachineSpecification(
        states=q_list,
        initial_state=initial_state,
        final_states=final_states,
        input_alphabet=input_alphabet,
        tape_alphabet=tape_alphabet,
        blank_symbol=blank_symbol,
        transitions=transitions,
        simulation_strings=simulation_strings,
        memory_alphabet=memory_alphabet,
        initial_memory=initial_memory,
    )