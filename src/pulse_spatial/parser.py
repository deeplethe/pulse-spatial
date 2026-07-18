"""Dependency-free lexer and recursive-descent parser for PULSE-S."""

from __future__ import annotations

from dataclasses import dataclass

from .language import (
    Assignment,
    Assumption,
    ConstraintDecl,
    CrsDecl,
    Duration,
    EntityDecl,
    GeometryLiteral,
    InstanceDecl,
    ModelDocument,
    ObservationDecl,
    ProcessDecl,
    PropertyDecl,
    Question,
    Reference,
    RegionDecl,
    ScenarioDecl,
    SpatialQuestion,
    StateDecl,
    Value,
    ValueQuestion,
)


class PulseSyntaxError(ValueError):
    """Raised when PULSE-S source text is not syntactically valid."""


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    value: str
    line: int
    column: int


def _tokenize(source: str, source_name: str) -> tuple[_Token, ...]:
    tokens: list[_Token] = []
    index = 0
    line = 1
    column = 1

    def advance() -> str:
        nonlocal index, line, column
        character = source[index]
        index += 1
        if character == "\n":
            line += 1
            column = 1
        else:
            column += 1
        return character

    def fail(
        message: str,
        at_line: int | None = None,
        at_column: int | None = None,
    ) -> None:
        error_line = line if at_line is None else at_line
        error_column = column if at_column is None else at_column
        raise PulseSyntaxError(
            f"{source_name}:{error_line}:{error_column}: {message}"
        )

    while index < len(source):
        character = source[index]
        if character.isspace():
            advance()
            continue
        if character == "#" or source.startswith("//", index):
            while index < len(source) and source[index] != "\n":
                advance()
            continue

        token_line, token_column = line, column
        if character == '"':
            advance()
            value: list[str] = []
            while index < len(source) and source[index] != '"':
                current = advance()
                if current == "\n":
                    fail("unterminated string", token_line, token_column)
                if current != "\\":
                    value.append(current)
                    continue
                if index >= len(source):
                    fail("unterminated string escape", token_line, token_column)
                escaped = advance()
                escapes = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}
                if escaped not in escapes:
                    fail(f"unsupported string escape \\{escaped}")
                value.append(escapes[escaped])
            if index >= len(source):
                fail("unterminated string", token_line, token_column)
            advance()
            tokens.append(_Token("STRING", "".join(value), token_line, token_column))
            continue

        if character.isalpha():
            value = [advance()]
            while index < len(source):
                current = source[index]
                if not (current.isalnum() or current in "_-"):
                    break
                value.append(advance())
            tokens.append(_Token("IDENT", "".join(value), token_line, token_column))
            continue

        number_start = character.isdigit() or (
            character == "-"
            and index + 1 < len(source)
            and source[index + 1].isdigit()
        )
        if number_start:
            value = []
            if source[index] == "-":
                value.append(advance())
            while index < len(source) and source[index].isdigit():
                value.append(advance())
            if index < len(source) and source[index] == ".":
                value.append(advance())
                if index >= len(source) or not source[index].isdigit():
                    fail("expected a digit after the decimal point")
                while index < len(source) and source[index].isdigit():
                    value.append(advance())
            tokens.append(_Token("NUMBER", "".join(value), token_line, token_column))
            continue

        symbol = next(
            (candidate for candidate in ("->", "==") if source.startswith(candidate, index)),
            None,
        )
        if symbol is not None:
            advance()
            advance()
            tokens.append(_Token("SYMBOL", symbol, token_line, token_column))
            continue
        if character in "{}[](),:.=":
            tokens.append(_Token("SYMBOL", advance(), token_line, token_column))
            continue
        fail(f"unexpected character {character!r}")

    tokens.append(_Token("EOF", "<eof>", line, column))
    return tuple(tokens)


class _Parser:
    def __init__(self, source: str, source_name: str) -> None:
        self.source_name = source_name
        self.tokens = _tokenize(source, source_name)
        self.index = 0

    @property
    def current(self) -> _Token:
        return self.tokens[self.index]

    def fail(self, message: str, token: _Token | None = None) -> None:
        found = self.current if token is None else token
        raise PulseSyntaxError(
            f"{self.source_name}:{found.line}:{found.column}: {message}; "
            f"found {found.value!r}"
        )

    def accept(self, value: str) -> bool:
        if self.current.value != value:
            return False
        self.index += 1
        return True

    def expect(self, value: str) -> _Token:
        if self.current.value != value:
            self.fail(f"expected {value!r}")
        token = self.current
        self.index += 1
        return token

    def expect_kind(self, kind: str, description: str) -> _Token:
        if self.current.kind != kind:
            self.fail(f"expected {description}")
        token = self.current
        self.index += 1
        return token

    def identifier(self) -> str:
        return self.expect_kind("IDENT", "an identifier").value

    def string(self) -> str:
        return self.expect_kind("STRING", "a string").value

    def number(self) -> int | float:
        value = self.expect_kind("NUMBER", "a number").value
        return float(value) if "." in value else int(value)

    def reference(self) -> Reference:
        owner = self.identifier()
        self.expect(".")
        return Reference(owner, self.identifier())

    def duration(self) -> Duration:
        value = float(self.number())
        unit = self.identifier()
        if unit not in {"ms", "s", "min", "h", "day"}:
            self.fail("expected a duration unit", self.tokens[self.index - 1])
        return Duration(value, unit)

    def geometry(self) -> GeometryLiteral:
        kind = self.identifier()
        if kind == "point":
            self.expect("(")
            x = float(self.number())
            self.expect(",")
            y = float(self.number())
            self.expect(")")
            return GeometryLiteral("Point", ((x, y),))
        if kind != "polygon":
            self.fail("expected point or polygon", self.tokens[self.index - 1])
        coordinates: list[tuple[float, float]] = []
        self.expect("[")
        while True:
            self.expect("[")
            x = float(self.number())
            self.expect(",")
            y = float(self.number())
            self.expect("]")
            coordinates.append((x, y))
            if not self.accept(","):
                break
        self.expect("]")
        return GeometryLiteral("Polygon", tuple(coordinates))

    def value(self) -> Value:
        if self.current.value in {"point", "polygon"}:
            return self.geometry()
        if self.current.kind == "NUMBER":
            return self.number()
        if self.current.kind == "STRING":
            return self.string()
        value = self.identifier()
        if value == "true":
            return True
        if value == "false":
            return False
        return value

    def crs(self) -> CrsDecl:
        name = self.identifier()
        self.expect("=")
        return CrsDecl(name, self.string())

    def region(self) -> RegionDecl:
        name = self.identifier()
        self.expect("crs")
        crs = self.identifier()
        self.expect("=")
        return RegionDecl(name, crs, self.geometry())

    def entity(self) -> EntityDecl:
        name = self.identifier()
        properties: list[PropertyDecl] = []
        states: list[StateDecl] = []
        self.expect("{")
        while not self.accept("}"):
            member_kind = self.identifier()
            if member_kind == "property":
                member_name = self.identifier()
                self.expect(":")
                type_name = self.identifier()
                crs = None
                unit = None
                if self.accept("crs"):
                    crs = self.identifier()
                if self.accept("unit"):
                    unit = self.string()
                properties.append(PropertyDecl(member_name, type_name, unit, crs))
                continue
            if member_kind != "state":
                self.fail("expected property or state", self.tokens[self.index - 1])
            member_name = self.identifier()
            self.expect("oneof")
            self.expect("[")
            values = [self.identifier()]
            while self.accept(","):
                values.append(self.identifier())
            self.expect("]")
            states.append(StateDecl(member_name, tuple(values)))
        return EntityDecl(name, tuple(properties), tuple(states))

    def instance(self) -> InstanceDecl:
        name = self.identifier()
        self.expect(":")
        entity = self.identifier()
        assignments: list[Assignment] = []
        self.expect("{")
        while not self.accept("}"):
            member = self.identifier()
            self.expect("=")
            assignments.append(Assignment(member, self.value()))
        return InstanceDecl(name, entity, tuple(assignments))

    def observation(self) -> ObservationDecl:
        reference = self.reference()
        self.expect("=")
        value = self.geometry()
        self.expect("{")
        self.expect("at")
        observed_at = self.string()
        self.expect("source")
        source = self.identifier()
        confidence = None
        accuracy = None
        accuracy_unit = None
        if self.accept("confidence"):
            confidence = float(self.number())
        if self.accept("accuracy"):
            accuracy = float(self.number())
            accuracy_unit = self.identifier()
            if accuracy_unit not in {"m", "km"}:
                self.fail("expected an accuracy unit", self.tokens[self.index - 1])
        self.expect("}")
        return ObservationDecl(
            reference,
            value,
            observed_at,
            source,
            confidence,
            accuracy,
            accuracy_unit,
        )

    def constraint(self) -> ConstraintDecl:
        name = self.identifier()
        self.expect("{")
        self.expect("must")
        predicate = self.identifier()
        self.expect("(")
        reference = self.reference()
        self.expect(",")
        region = self.identifier()
        self.expect(")")
        while_reference = None
        while_value = None
        if self.accept("while"):
            while_reference = self.reference()
            self.expect("==")
            while_value = self.identifier()
        self.expect("}")
        return ConstraintDecl(
            name, predicate, reference, region, while_reference, while_value
        )

    def process(self) -> ProcessDecl:
        name = self.identifier()
        self.expect("(")
        parameter = self.identifier()
        self.expect(":")
        entity = self.identifier()
        self.expect(")")
        self.expect("{")
        self.expect("when")
        event = self.identifier()
        self.expect("(")
        guard_reference = self.reference()
        self.expect(",")
        region = self.identifier()
        self.expect(")")
        duration = self.duration() if self.accept("for") else None
        self.expect("changes")
        transition_reference = self.reference()
        self.expect(":")
        from_state = self.identifier()
        self.expect("->")
        to_state = self.identifier()
        self.expect("}")
        return ProcessDecl(
            name,
            parameter,
            entity,
            event,
            guard_reference,
            region,
            duration,
            transition_reference,
            from_state,
            to_state,
        )

    def question(self) -> Question:
        if self.current.value in {"inside", "coveredBy"}:
            predicate = self.identifier()
            self.expect("(")
            reference = self.reference()
            self.expect(",")
            region = self.identifier()
            self.expect(")")
            return SpatialQuestion(predicate, reference, region)
        return ValueQuestion(self.reference())

    def scenario(self) -> ScenarioDecl:
        name = self.identifier()
        assumptions: list[Assumption] = []
        questions: list[Question] = []
        run_for = None
        self.expect("{")
        while not self.accept("}"):
            clause = self.identifier()
            if clause == "assume":
                reference = self.reference()
                self.expect("==")
                assumptions.append(Assumption(reference, self.value()))
            elif clause == "run":
                if run_for is not None:
                    self.fail("scenario can contain only one run clause")
                run_for = self.duration()
            elif clause == "ask":
                questions.append(self.question())
            else:
                self.fail("expected assume, run, ask, or }", self.tokens[self.index - 1])
        return ScenarioDecl(name, tuple(assumptions), run_for, tuple(questions))

    def model(self) -> ModelDocument:
        self.expect("model")
        name = self.identifier()
        self.expect("version")
        version = self.string()

        declarations: dict[str, list[object]] = {
            "crs": [],
            "region": [],
            "entity": [],
            "instance": [],
            "observe": [],
            "constraint": [],
            "process": [],
            "scenario": [],
        }
        parsers = {
            "crs": self.crs,
            "region": self.region,
            "entity": self.entity,
            "instance": self.instance,
            "observe": self.observation,
            "constraint": self.constraint,
            "process": self.process,
            "scenario": self.scenario,
        }
        while self.current.kind != "EOF":
            declaration = self.identifier()
            parser = parsers.get(declaration)
            if parser is None:
                self.fail("expected a declaration keyword", self.tokens[self.index - 1])
            declarations[declaration].append(parser())

        return ModelDocument(
            name,
            version,
            tuple(declarations["crs"]),  # type: ignore[arg-type]
            tuple(declarations["region"]),  # type: ignore[arg-type]
            tuple(declarations["entity"]),  # type: ignore[arg-type]
            tuple(declarations["instance"]),  # type: ignore[arg-type]
            tuple(declarations["observe"]),  # type: ignore[arg-type]
            tuple(declarations["constraint"]),  # type: ignore[arg-type]
            tuple(declarations["process"]),  # type: ignore[arg-type]
            tuple(declarations["scenario"]),  # type: ignore[arg-type]
        )


def parse_pulse(source: str, source_name: str = "<string>") -> ModelDocument:
    """Parse PULSE-S text into an immutable, unresolved document model."""

    return _Parser(source, source_name).model()
