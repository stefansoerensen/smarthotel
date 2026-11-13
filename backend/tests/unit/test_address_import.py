"""Parsing bus address lists: own CSV and ETS group address exports."""

from app.services.devices.addresses import parse_address_list


def test_own_csv_with_header() -> None:
    rows, errors = parse_address_list("code;address\n101-VALVE;1/2/3\n101-SETPOINT;1/2/4\n")
    assert [(r.line, r.code, r.address) for r in rows] == [
        (2, "101-VALVE", "1/2/3"),
        (3, "101-SETPOINT", "1/2/4"),
    ]
    assert errors == []


def test_ets_export_quoted_with_names_as_codes() -> None:
    text = '"Group name";"Address";"Central";"Unfiltered";"Description"\n"101-VALVE";"1/2/3";"";"";""\n'
    rows, errors = parse_address_list(text)
    assert [(r.code, r.address) for r in rows] == [("101-VALVE", "1/2/3")]
    assert errors == []


def test_commas_and_blank_lines() -> None:
    rows, _ = parse_address_list("101-LIGHT,1/0/7\n\n102-LIGHT , 1/0/8\n")
    assert [(r.code, r.address) for r in rows] == [("101-LIGHT", "1/0/7"), ("102-LIGHT", "1/0/8")]


def test_malformed_lines_are_reported_with_their_number() -> None:
    rows, errors = parse_address_list("code;address\n101-VALVE\n;1/2/3\n101-X;1/2/3\n")
    assert [r.code for r in rows] == ["101-X"]
    assert [(e.line, e.message) for e in errors] == [
        (2, "Zwei Spalten erwartet: Code und Adresse"),
        (3, "Code fehlt"),
    ]


def test_ets_middle_group_rows_without_sub_address_are_skipped() -> None:
    text = '"Group name";"Address"\n"Heizung";"1/-/-"\n"Zimmer 101";"1/2/-"\n"101-VALVE";"1/2/3"\n'
    rows, errors = parse_address_list(text)
    assert [r.code for r in rows] == ["101-VALVE"]
    assert errors == []
