from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .config_loader import MachineSpecification, Transition, _transition_key


@dataclass
class InstantaneousDescription:
    """Representa una descripción instantánea (ID) de la MT."""

    step: int
    state: str
    head_position: int
    tape_view: str
    memory: Optional[str]

    def format(self) -> str:
        return (
            f"Paso {self.step:04d}: estado={self.state}, cabeza={self.head_position}, "
            f"memoria={self.memory or '-'}\n  cinta: {self.tape_view}"
        )


@dataclass
class MachineResult:
    """Resultado final de la simulación."""

    accepted: bool
    halted: bool
    reason: str
    steps: int
    ids: List[InstantaneousDescription]


class Tape:
    """Implementación de una cinta infinita hacia ambos lados."""

    def __init__(self, blank_symbol: str, initial_input: str) -> None:
        self.blank_symbol = blank_symbol
        self.cells: Dict[int, str] = {}
        self.min_index = 0
        self.max_index = 0
        for index, symbol in enumerate(initial_input):
            self.cells[index] = symbol
            self.max_index = index
        if not initial_input:
            self.cells[0] = blank_symbol

    def read(self, position: int) -> str:
        return self.cells.get(position, self.blank_symbol)

    def write(self, position: int, symbol: str) -> None:
        self.cells[position] = symbol
        self.min_index = min(self.min_index, position)
        self.max_index = max(self.max_index, position)

    def view(self, head_position: int, radius: int = 20) -> str:
        start = min(self.min_index, head_position - radius)
        end = max(self.max_index, head_position + radius)
        cells = []
        for index in range(start, end + 1):
            symbol = self.read(index)
            if index == head_position:
                cells.append(f"[{symbol}]")
            else:
                cells.append(symbol)
        return "".join(cells)


class TuringMachine:
    """Simulador de Máquinas de Turing deterministas de una cinta."""

    def __init__(self, specification: MachineSpecification) -> None:
        self.spec = specification
        self.transition_map = specification.transition_map()

    def _next_transition(
        self,
        state: str,
        symbol: str,
        memory: Optional[str],
    ) -> Optional[Transition]:
        """Obtiene la transición válida para el trío dado."""

        key = _transition_key(state, symbol, memory)
        transition = self.transition_map.get(key)
        if transition is not None:
            return transition
        return self.transition_map.get(_transition_key(state, symbol, None))

    def run(
        self,
        input_string: str,
        *,
        max_steps: int = 10_000,
        capture_ids: bool = True,
    ) -> MachineResult:
        """Ejecuta la máquina para una cadena de entrada."""

        tape = Tape(self.spec.blank_symbol, input_string)
        state = self.spec.initial_state
        head_position = 0
        memory = self.spec.initial_memory

        ids: List[InstantaneousDescription] = []
        steps = 0

        def capture() -> None:
            if capture_ids:
                ids.append(
                    InstantaneousDescription(
                        step=steps,
                        state=state,
                        head_position=head_position,
                        tape_view=tape.view(head_position),
                        memory=memory,
                    )
                )

        capture()

        while steps < max_steps:
            current_symbol = tape.read(head_position)
            transition = self._next_transition(state, current_symbol, memory)
            if transition is None:
                halted = state in self.spec.final_states
                reason = "Estado final alcanzado" if halted else "No existe transición definida"
                return MachineResult(
                    accepted=halted,
                    halted=True,
                    reason=reason,
                    steps=steps,
                    ids=ids,
                )

            tape.write(head_position, transition.write_symbol)
            if transition.movement == "R":
                head_position += 1
            elif transition.movement == "L":
                head_position -= 1

            state = transition.next_state
            memory = transition.next_memory if transition.next_memory is not None else memory
            steps += 1
            capture()

            if state in self.spec.final_states:
                return MachineResult(
                    accepted=True,
                    halted=True,
                    reason="Estado final alcanzado",
                    steps=steps,
                    ids=ids,
                )

        return MachineResult(
            accepted=False,
            halted=False,
            reason="Se alcanzó el límite máximo de pasos",
            steps=steps,
            ids=ids,
        )

    def simulate_inputs(
        self,
        inputs: Optional[List[str]] = None,
        *,
        max_steps: int = 10_000,
        capture_ids: bool = True,
    ) -> Dict[str, MachineResult]:
        """Ejecuta la MT para cada cadena indicada."""

        inputs = inputs if inputs is not None else self.spec.simulation_strings
        results: Dict[str, MachineResult] = {}
        for input_string in inputs:
            results[input_string] = self.run(
                input_string,
                max_steps=max_steps,
                capture_ids=capture_ids,
            )
        return results