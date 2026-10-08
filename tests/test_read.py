"""GeoCSV scientific content, framing, and public-result contracts."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from math import isinf
from pathlib import Path

import pandas as pd
import pytest

from mermaid import geocsv


FIXTURES = Path(__file__).parent / "fixtures"
CANONICAL = Path(__file__).parents[1] / "data" / "fixtures" / "P0006" / "P0006.geocsv"


def read_one(path: str | Path) -> pd.DataFrame:
    frames = geocsv.read(path)
    assert len(frames) == 1
    return frames[0]


def test_declared_types_exact_headers_and_same_time_records() -> None:
    frame = read_one(FIXTURES / "typed.geocsv")
    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == [
        "StartTime", "Latitude", "SampleCount", "MethodIdentifier", "odd field-name"
    ]
    assert isinstance(frame.index, pd.RangeIndex)
    assert frame.index.name == "source_record_index"
    assert list(frame.index) == [0, 1]
    assert frame["StartTime"].dtype == object
    assert frame["StartTime"].iloc[0] == pd.Timestamp("2025-01-01T00:00:00.123456789Z")
    assert frame["StartTime"].iloc[1] == pd.Timestamp("2024-12-31T19:00:00.123456789-05:00")
    assert frame["StartTime"].iloc[0].tzinfo is not None
    assert frame["StartTime"].iloc[1].utcoffset() != frame["StartTime"].iloc[0].utcoffset()
    assert frame["Latitude"].dtype == "Float64"
    assert frame["SampleCount"].dtype == "Int64"
    assert isinstance(frame["MethodIdentifier"].dtype, pd.StringDtype)
    assert frame.iloc[0]["SampleCount"] == 9007199254740993
    assert pd.isna(frame.iloc[1]["SampleCount"])
    assert pd.isna(frame.iloc[1]["Latitude"])
    assert frame.iloc[0]["odd field-name"] is pd.NA
    assert frame.iloc[1]["odd field-name"] == 'a "quoted" value'
    time = pd.Timestamp("2025-01-01T00:00:00.123456789Z")
    assert (frame["StartTime"] == time).all()
    matches = frame.loc[frame["StartTime"].eq(time)]
    assert list(matches.index) == [0, 1]
    assert matches["MethodIdentifier"].tolist() == [
        "Measurement:GPS,quoted", "Algorithm(event):test"
    ]


def test_metadata_preserves_comments_declarations_and_immutability() -> None:
    frame = read_one(FIXTURES / "typed.geocsv")
    metadata = frame.attrs["geocsv"]
    assert isinstance(metadata, geocsv.GeoCSVMetadata)
    assert metadata.source_path == (FIXTURES / "typed.geocsv").resolve()
    assert metadata.delimiter == ","
    assert metadata.field_types["SampleCount"] == "integer"
    assert metadata.field_units["Latitude"] == "degrees_north"
    assert metadata.field_long_names["Latitude"] == ""
    assert metadata.field_standard_names["Latitude"] == ""
    assert metadata.field_missing == {}
    notes = [comment for comment in metadata.comments if comment.key == "note"]
    assert [comment.value for comment in notes] == [
        "first: keeps the colon", "second, keeps the comma"
    ]
    assert notes[1].raw == '#note: second, keeps the comma'
    assert notes[1].line_number == 6
    assert metadata.comments[-1].key is None
    history = next(comment for comment in metadata.comments if comment.key == "history")
    assert history.value == "final comment"
    with pytest.raises(FrozenInstanceError):
        metadata.delimiter = "|"
    with pytest.raises(TypeError):
        metadata.field_units["Latitude"] = "meters"
    assert deepcopy(metadata) is metadata
    # pandas selects/copies attrs during ordinary workflows; read-only metadata
    # must not make these documented README examples fail.
    assert frame.copy().attrs["geocsv"] == metadata
    assert frame.iloc[:1].attrs["geocsv"].source_path == metadata.source_path


def test_field_descriptions_are_trimmed_by_column_and_raw_comments_remain(
    tmp_path: Path,
) -> None:
    source = tmp_path / "field_descriptions.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n"
        "#field_type: datetime,float\n"
        '#field_long_name:  "Event, time"  ,  Station latitude  \n'
        '#field_long_name:"Event, time",Station latitude\n'
        "#field_standard_name: time , latitude \n"
        "StartTime,Latitude\n"
        "2025-01-01T00:00:00Z,12.5\n"
        "#field_standard_name:time,latitude\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    metadata = frame.attrs["geocsv"]
    assert metadata.field_long_names == {
        "StartTime": "Event, time", "Latitude": "Station latitude"
    }
    assert metadata.field_standard_names == {
        "StartTime": "time", "Latitude": "latitude"
    }
    descriptions = [
        comment.raw for comment in metadata.comments if comment.key == "field_long_name"
    ]
    assert descriptions == [
        '#field_long_name:  "Event, time"  ,  Station latitude  ',
        '#field_long_name:"Event, time",Station latitude',
    ]
    with pytest.raises(TypeError):
        metadata.field_long_names["Latitude"] = "changed"


@pytest.mark.parametrize(
    "attribute",
    ["field_type", "field_unit", "field_long_name", "field_standard_name", "field_missing"],
)
def test_empty_field_attribute_declaration_does_not_expand(
    tmp_path: Path, attribute: str
) -> None:
    source = tmp_path / "empty_attributes.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#{attribute}:\nA,B\nx,y\n",
        encoding="utf-8",
    )
    with pytest.raises(
        geocsv.GeoCSVError, match=rf"line 2: {attribute} has 1 fields; header has 2"
    ):
        read_one(source)


def test_explicit_empty_field_attribute_entries_match_header_width(tmp_path: Path) -> None:
    source = tmp_path / "empty_attributes.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: ,\n#field_long_name: ,\nA,B\nx,y\n",
        encoding="utf-8",
    )
    metadata = read_one(source).attrs["geocsv"]
    assert metadata.field_types == {"A": "", "B": ""}
    assert metadata.field_long_names == {"A": "", "B": ""}


@pytest.mark.parametrize(
    "delimiter, separator, empty_position",
    [
        (r"\t", "\t", "first"),
        (r"\t", "\t", "last"),
        (r"\s", " ", "first"),
        (r"\s", " ", "last"),
    ],
)
def test_quoted_empty_edge_metadata_entries_with_whitespace_delimiters(
    tmp_path: Path, delimiter: str, separator: str, empty_position: str,
) -> None:
    empty = '""'
    if empty_position == "first":
        field_type = f"{empty}{separator}integer"
        field_unit = f"{empty}{separator}counts"
        long_name = f'{empty}{separator}"Sample count"'
        standard_name = f"{empty}{separator}sample_count"
        field_missing = f"{empty}{separator}missing"
        row = f"station{separator}missing"
    else:
        field_type = f"integer{separator}{empty}"
        field_unit = f"counts{separator}{empty}"
        long_name = f'"Sample count"{separator}{empty}'
        standard_name = f"sample_count{separator}{empty}"
        field_missing = f"-1{separator}{empty}"
        row = f"-1{separator}station"

    source = tmp_path / "quoted_empty_metadata.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#delimiter: {delimiter}\n"
        f"#field_type:{field_type}\n#field_unit:{field_unit}\n"
        f"#field_long_name:{long_name}\n"
        f"#field_standard_name:{standard_name}\n"
        f"#field_missing:{field_missing}\nA{separator}B\n{row}\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    metadata = frame.attrs["geocsv"]
    if empty_position == "first":
        assert frame["A"].dtype == "string"
        assert frame["A"].iloc[0] == "station"
        assert frame["B"].dtype == "Int64"
        assert frame["B"].iloc[0] is pd.NA
        expected_types = {"A": "", "B": "integer"}
        expected_units = {"A": "", "B": "counts"}
        expected_missing = {"A": "", "B": "missing"}
        expected_long_names = {"A": "", "B": "Sample count"}
        expected_standard_names = {"A": "", "B": "sample_count"}
    else:
        assert frame["A"].dtype == "Int64"
        assert frame["A"].iloc[0] is pd.NA
        assert frame["B"].dtype == "string"
        assert frame["B"].iloc[0] == "station"
        expected_types = {"A": "integer", "B": ""}
        expected_units = {"A": "counts", "B": ""}
        expected_missing = {"A": "-1", "B": ""}
        expected_long_names = {"A": "Sample count", "B": ""}
        expected_standard_names = {"A": "sample_count", "B": ""}

    assert metadata.field_types == expected_types
    assert metadata.field_units == expected_units
    assert metadata.field_missing == expected_missing
    assert metadata.field_long_names == expected_long_names
    assert metadata.field_standard_names == expected_standard_names
    assert frame.index.equals(pd.RangeIndex(1, name="source_record_index"))
    assert metadata.source_path == source.resolve()


@pytest.mark.parametrize("delimiter, separator", [(r"\t", "\t"), (r"\s", " ")])
@pytest.mark.parametrize("entry", ["", "integer", "integer "])
def test_unquoted_empty_edge_entries_are_trimmed_as_padding(
    tmp_path: Path, delimiter: str, separator: str, entry: str,
) -> None:
    source = tmp_path / "unquoted_empty_edge.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#delimiter: {delimiter}\n"
        f"#field_type: {entry}\nA{separator}B\nx{separator}1\n",
        encoding="utf-8",
    )
    with pytest.raises(geocsv.GeoCSVError, match="field_type has 1 fields; header has 2"):
        geocsv.read(source)


@pytest.mark.parametrize("quote", ["'", "`"])
def test_single_quotes_and_backticks_do_not_quote_empty_metadata_entries(
    tmp_path: Path, quote: str,
) -> None:
    source = tmp_path / "non_double_quote_metadata.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#delimiter: \\t\n"
        f"#field_type:{quote}{quote}\tinteger\nA\tB\nx\t1\n",
        encoding="utf-8",
    )
    with pytest.raises(geocsv.GeoCSVError, match="unsupported field type"):
        geocsv.read(source)


def test_source_path_resolves_relative_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(FIXTURES)
    frame = read_one("typed.geocsv")
    assert frame.attrs["geocsv"].source_path == (FIXTURES / "typed.geocsv").resolve()


def test_multiline_csv_and_comments_at_record_boundaries() -> None:
    frame = read_one(FIXTURES / "multiline.geocsv")
    assert frame["Description"].tolist() == [
        "first line\n#not_a_comment: inside a cell\nlast line",
        "#a quoted data cell",
    ]
    assert frame["Count"].tolist() == [1, 2]
    comments = frame.attrs["geocsv"].comments
    assert [comment.key for comment in comments] == ["dataset", "field_type", "field_unit", "note"]
    assert comments[-1].line_number == 8


def test_crlf_inside_a_quoted_cell_is_preserved(tmp_path: Path) -> None:
    source = tmp_path / "quoted_crlf.geocsv"
    source.write_bytes(
        b"#dataset: GeoCSV\r\nValue\r\n\"first\r\n#second\"\r\n"
    )
    frame = read_one(source)
    assert frame["Value"].tolist() == ["first\r\n#second"]


@pytest.mark.parametrize(
    "cell, message",
    [
        ('he"llo', "quote in an unquoted CSV field"),
        (' "hello"', "quote in an unquoted CSV field"),
        ('"hello" ', "content after a closing CSV quote"),
        ('"hello"x', "content after a closing CSV quote"),
    ],
)
def test_malformed_csv_quotes_raise_without_repair(
    tmp_path: Path, cell: str, message: str
) -> None:
    source = tmp_path / "malformed_quotes.geocsv"
    source.write_text(f"#dataset: GeoCSV\nValue\n{cell}\n", encoding="utf-8")
    with pytest.raises(geocsv.GeoCSVError, match=f"line 3: {message}"):
        read_one(source)


@pytest.mark.parametrize(
    "content, line_number",
    [
        (b"#dataset: GeoCSV\rValue\nx\n", 1),
        (b"#dataset: GeoCSV\nValue\nx\ry\n", 3),
    ],
)
def test_lone_cr_is_rejected(
    tmp_path: Path, content: bytes, line_number: int
) -> None:
    source = tmp_path / "lone_cr.geocsv"
    source.write_bytes(content)
    with pytest.raises(geocsv.GeoCSVError, match=rf"line {line_number}: lone CR"):
        read_one(source)


@pytest.mark.parametrize(
    "content, line_number",
    [
        (b"#dataset: GeoCSV", 1),
        (b"#dataset: GeoCSV\nValue", 2),
        (b"#dataset: GeoCSV\nValue\nx", 3),
        (b"#dataset: GeoCSV\nValue\nx\n#note: trailing", 4),
    ],
)
def test_every_line_requires_lf_or_crlf_ending(
    tmp_path: Path, content: bytes, line_number: int
) -> None:
    source = tmp_path / "unterminated_line.geocsv"
    source.write_bytes(content)
    with pytest.raises(
        geocsv.GeoCSVError, match=rf"line {line_number}: line must end with LF or CRLF"
    ):
        geocsv.read(source)


@pytest.mark.parametrize("quoted_value", ["#hello", "#dataset: hello"])
def test_single_column_quoted_hash_values_are_data(
    tmp_path: Path, quoted_value: str
) -> None:
    source = tmp_path / "quoted_hash.geocsv"
    source.write_text(
        '#dataset: GeoCSV\n#field_type: string\n'
        '#field_unit: unitless\nLabel\nbefore\n'
        f'"{quoted_value}"\n#note: between records\nafter\n',
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame["Label"].tolist() == ["before", quoted_value, "after"]
    assert isinstance(frame["Label"].dtype, pd.StringDtype)
    assert isinstance(frame.index, pd.RangeIndex)
    assert frame.index.name == "source_record_index"
    assert frame.index.tolist() == [0, 1, 2]
    metadata = frame.attrs["geocsv"]
    assert metadata.source_path == source.resolve()
    assert metadata.field_types == {"Label": "string"}
    assert [comment.key for comment in metadata.comments] == [
        "dataset", "field_type", "field_unit", "note"
    ]
    assert metadata.comments[0].raw == '#dataset: GeoCSV'
    assert metadata.comments[-1].raw == "#note: between records"
    assert metadata.comments[-1].line_number == 7


@pytest.mark.parametrize("column_name", ["#Label", "#dataset: hello"])
def test_quoted_hash_header_and_literal_comment_boundaries(
    tmp_path: Path, column_name: str
) -> None:
    source = tmp_path / "hash_header.geocsv"
    source.write_text(
        '# dataset : GeoCSV\n# field_type : string\n# field_unit : unitless\n'
        '# free text\n# custom : before, with "quotes"\n'
        f'"{column_name}"\nhello\n# custom : before, with "quotes"\n #literal data\nworld\n',
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame.columns.tolist() == [column_name]
    assert frame[column_name].tolist() == ["hello", " #literal data", "world"]
    assert isinstance(frame[column_name].dtype, pd.StringDtype)
    assert frame.index.equals(pd.RangeIndex(3, name="source_record_index"))
    metadata = frame.attrs["geocsv"]
    assert metadata.field_types == {column_name: "string"}
    assert metadata.field_units == {column_name: "unitless"}
    assert [(comment.key, comment.value, comment.line_number)
            for comment in metadata.comments] == [
        ("dataset", "GeoCSV", 1), ("field_type", "string", 2),
        ("field_unit", "unitless", 3), (None, None, 4),
        ("custom", 'before, with "quotes"', 5),
        ("custom", 'before, with "quotes"', 8),
    ]
    assert metadata.comments[4].raw == '# custom : before, with "quotes"'


def test_legacy_quoted_dataset_is_not_a_declaration(tmp_path: Path) -> None:
    source = tmp_path / "legacy.geocsv"
    source.write_text(
        '"#dataset: GeoCSV"\n#field_type: string\n#field_unit: unitless\nLabel\nhello\n',
        encoding="utf-8",
    )
    with pytest.raises(geocsv.GeoCSVError, match="line 1: missing required #dataset"):
        read_one(source)


@pytest.mark.parametrize(
    "dataset_value, preceding_comment, accepted",
    [
        ("GeoCSV", "", True),
        ("geocsv", "", True),
        ("GeoCSV 2.0", "", True),
        ("MERMAID GeoCSV draft", "#title: before marker\n", True),
        ("NOT_A_FORMAT 2.0", "", False),
    ],
)
def test_dataset_value_requires_geocsv_name_only(
    tmp_path: Path, dataset_value: str, preceding_comment: str, accepted: bool
) -> None:
    source = tmp_path / "dataset_identity.geocsv"
    source.write_text(
        f"{preceding_comment}#dataset: {dataset_value}\n"
        "#field_type: string\n#field_unit: unitless\nName\nvalue\n",
        encoding="utf-8",
    )
    if accepted:
        assert read_one(source)["Name"].tolist() == ["value"]
    else:
        with pytest.raises(geocsv.GeoCSVError, match=r"line 1: #dataset value must contain 'GeoCSV'"):
            read_one(source)


def test_read_returns_each_dataset_with_file_wide_record_indices(tmp_path: Path) -> None:
    source = tmp_path / "two_datasets.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#title: first table\n#field_type: string\n"
        "#field_unit: unitless\nName\na\nb\n"
        "#dataset: GeoCSV 2.0\n#title: second table\n"
        "#field_type: integer\n#field_unit: counts\nCount\n7\n8\n",
        encoding="utf-8",
    )
    frames = geocsv.read(source)
    assert len(frames) == 2
    first, second = frames
    assert first.columns.tolist() == ["Name"]
    assert first["Name"].tolist() == ["a", "b"]
    assert first.index.equals(pd.RangeIndex(0, 2, name="source_record_index"))
    assert first.attrs["geocsv"].field_types == {"Name": "string"}
    assert first.attrs["geocsv"].comments[1].value == "first table"
    assert second.columns.tolist() == ["Count"]
    assert second["Count"].tolist() == [7, 8]
    assert second["Count"].dtype == "Int64"
    assert second.index.equals(pd.RangeIndex(2, 4, name="source_record_index"))
    assert second.attrs["geocsv"].field_types == {"Count": "integer"}
    assert second.attrs["geocsv"].comments[1].value == "second table"
    assert first.attrs["geocsv"].source_path == source.resolve()
    assert second.attrs["geocsv"].source_path == source.resolve()


def test_identical_known_declarations_may_repeat_before_and_between_rows(
    tmp_path: Path,
) -> None:
    source = tmp_path / "repeated_declarations.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#title: stable\n#title: stable\n"
        "#field_type: string\n#field_unit: unitless\nName\nfirst\n"
        "#title: stable\n#field_type: string\nsecond\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame["Name"].tolist() == ["first", "second"]
    title_values = [
        comment.value
        for comment in frame.attrs["geocsv"].comments
        if comment.key == "title"
    ]
    assert title_values == ["stable", "stable", "stable"]


@pytest.mark.parametrize("late_declaration", ["#title: changed", "#history: added"])
def test_changed_or_new_known_declaration_requires_dataset_boundary(
    tmp_path: Path, late_declaration: str
) -> None:
    source = tmp_path / "changed_declaration.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#title: original\n#field_type: string\n"
        "#field_unit: unitless\nName\nfirst\n"
        f"{late_declaration}\nsecond\n",
        encoding="utf-8",
    )
    with pytest.raises(geocsv.GeoCSVError, match="new #dataset boundary"):
        geocsv.read(source)


@pytest.mark.parametrize("keyword", ["GeodeticDatum", "Ellipsoid", "note"])
def test_changed_unknown_keyword_requires_dataset_boundary(
    tmp_path: Path, keyword: str
) -> None:
    source = tmp_path / "changed_unknown_keyword.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#{keyword}: first\n#field_type: float\n"
        f"Latitude\n1\n#{keyword}: second\n2\n",
        encoding="utf-8",
    )
    with pytest.raises(
        geocsv.GeoCSVError,
        match=rf"line 6: #{keyword.lower()} changed; a new #dataset boundary is required",
    ) as error:
        geocsv.read(source)
    assert str(source.resolve()) in str(error.value)


def test_unknown_keyword_introduced_after_header_then_changed(tmp_path: Path) -> None:
    source = tmp_path / "late_unknown_keyword.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: string\nLabel\nfirst\n"
        "#note: stable\nsecond\n#note: changed\nthird\n",
        encoding="utf-8",
    )
    with pytest.raises(
        geocsv.GeoCSVError,
        match="line 7: #note changed; a new #dataset boundary is required",
    ):
        geocsv.read(source)


@pytest.mark.parametrize("keyword", ["GeodeticDatum", "Ellipsoid"])
def test_unknown_keyword_can_change_at_dataset_boundary(
    tmp_path: Path, keyword: str
) -> None:
    source = tmp_path / "two_unknown_keywords.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#{keyword}: first\n#field_type: float\n"
        f"Latitude\n1\n#{keyword}: first\n"
        f"#dataset: GeoCSV\n#{keyword}: second\n#field_type: float\n"
        "Latitude\n2\n",
        encoding="utf-8",
    )
    first, second = geocsv.read(source)
    assert first["Latitude"].tolist() == [1.0]
    assert second["Latitude"].tolist() == [2.0]
    assert first["Latitude"].dtype == second["Latitude"].dtype == "Float64"
    assert first.index.equals(pd.RangeIndex(0, 1, name="source_record_index"))
    assert second.index.equals(pd.RangeIndex(1, 2, name="source_record_index"))
    first_metadata = first.attrs["geocsv"]
    second_metadata = second.attrs["geocsv"]
    assert first_metadata.source_path == second_metadata.source_path == source.resolve()
    assert [
        comment.value for comment in first_metadata.comments
        if comment.key == keyword.lower()
    ] == ["first", "first"]
    assert [
        comment.value for comment in second_metadata.comments
        if comment.key == keyword.lower()
    ] == ["second"]


@pytest.mark.parametrize(
    "declarations, header, row, expected_types, expected_units",
    [
        (
            "", "Name,Value", "alpha,10",
            {"Name": "", "Value": ""}, {"Name": "", "Value": ""},
        ),
        (
            "#field_type: datetime,,float\n#field_unit: iso8601,,degrees_north\n",
            "Time,Station,Latitude", "2011-08-18T00:00:00,AB01,-14.2",
            {"Time": "datetime", "Station": "", "Latitude": "float"},
            {"Time": "iso8601", "Station": "", "Latitude": "degrees_north"},
        ),
        (
            "#field_type: \n#field_unit: \n", "Station", "AB01",
            {"Station": ""},
            {"Station": ""},
        ),
    ],
)
def test_optional_field_type_and_unit_declarations(
    tmp_path: Path,
    declarations: str,
    header: str,
    row: str,
    expected_types: dict[str, str],
    expected_units: dict[str, str],
) -> None:
    source = tmp_path / "optional_attributes.geocsv"
    source.write_text(
        f"#dataset: GeoCSV 2.0\n{declarations}{header}\n{row}\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    metadata = frame.attrs["geocsv"]
    assert metadata.field_types == expected_types
    assert metadata.field_units == expected_units
    if "Time" in expected_types:
        assert pd.api.types.is_datetime64_dtype(frame["Time"].dtype)
        assert frame["Time"].dt.tz is None
        assert frame["Time"].iloc[0] == pd.Timestamp("2011-08-18T00:00:00")
        assert frame["Station"].dtype == "string"
        assert frame["Latitude"].dtype == "Float64"
    else:
        for name in expected_types:
            assert frame[name].dtype == "string"


def test_blank_record_is_rejected_for_width_instead_of_skipped(tmp_path: Path) -> None:
    source = tmp_path / "blank_record.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless\n"
        "Label\n\nvalue\n",
        encoding="utf-8",
    )
    with pytest.raises(geocsv.GeoCSVError, match=r"line 5: data row has 0 fields; header has 1"):
        read_one(source)


def test_declared_missing_values_and_alternative_delimiter() -> None:
    frame = read_one(FIXTURES / "missing.geocsv")
    assert frame.iloc[1].isna().all()
    assert frame.iloc[0]["Label"] is pd.NA
    assert frame.attrs["geocsv"].delimiter == "|"
    assert frame.attrs["geocsv"].field_missing["Height"] == "-999"


def test_missing_tokens_and_declared_sentinel_preserve_other_strings(
    tmp_path: Path,
) -> None:
    source = tmp_path / "missing_tokens.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: integer,string,float\n"
        "#field_missing: ,foo,\nCount,Label,Value\n"
        "187,foo,17\n188,NaN,18\n189,,19\n190, nan ,20\n191,NAN,21\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame["Label"].isna().tolist() == [True, True, True, False, True]
    assert frame["Label"].iloc[3] == " nan "
    assert frame["Count"].tolist() == [187, 188, 189, 190, 191]
    assert frame.attrs["geocsv"].field_missing == {
        "Count": "", "Label": "foo", "Value": ""
    }


def test_typed_cells_trim_padding_while_string_cells_keep_it(tmp_path: Path) -> None:
    source = tmp_path / "padded_values.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: integer,float,datetime,string\n"
        "#field_missing: -1,missing,,\nCount,Height,Time,Label\n"
        " 17 , 17.0 , 2025-01-01T00:00:00Z ,  Station A  \n"
        " -1 , missing , 2025-01-02 ,  nan  \n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame["Count"].iloc[0] == 17
    assert frame["Height"].iloc[0] == 17.0
    assert frame["Time"].iloc[0] == pd.Timestamp("2025-01-01T00:00:00Z")
    assert frame["Label"].tolist() == ["  Station A  ", "  nan  "]
    assert frame["Count"].iloc[1] is pd.NA
    assert frame["Height"].iloc[1] is pd.NA


def test_escaped_tab_delimiter_and_utf8() -> None:
    frame = read_one(FIXTURES / "tab.geocsv")
    assert frame.columns.tolist() == ["Unmodified Column", "Height"]
    assert frame.iloc[0]["Unmodified Column"] == "café"
    assert frame.iloc[0]["Height"] == 1.25
    assert frame.attrs["geocsv"].delimiter == "\t"


def test_native_pandas_missing_values_for_every_declared_type() -> None:
    frame = read_one(FIXTURES / "native_missing.geocsv")
    assert frame.iloc[0]["Time"] is pd.NaT
    assert frame.iloc[0]["Height"] is pd.NA
    assert frame.iloc[0]["Count"] is pd.NA
    assert frame.iloc[0]["Label"] is pd.NA
    assert frame.iloc[1]["Label"] == "NA"
    assert frame["Height"].dtype == "Float64"
    assert frame["Count"].dtype == "Int64"
    assert isinstance(frame["Label"].dtype, pd.StringDtype)
    assert str(frame["Time"].dt.tz) == "UTC"


@pytest.mark.parametrize("empty_cell", ["", '""'])
def test_empty_fields_become_typed_missing_values(
    tmp_path: Path, empty_cell: str
) -> None:
    source = tmp_path / "empty_fields.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: string,integer,float,datetime\n"
        "#field_unit: unitless,unitless,unitless,iso8601\n"
        "Label,Count,Height,Time\n"
        f"{empty_cell},{empty_cell},{empty_cell},{empty_cell}\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame.shape == (1, 4)
    assert frame.index.tolist() == [0]
    assert frame.index.name == "source_record_index"
    assert frame["Label"].dtype == "string"
    assert frame["Count"].dtype == "Int64"
    assert frame["Height"].dtype == "Float64"
    assert frame["Time"].dt.tz is None
    assert frame.iloc[0].isna().all()
    assert frame.attrs["geocsv"].source_path == source.resolve()


@pytest.mark.parametrize(
    "values, expected, expected_timezone",
    [
        (["2011-08-18T00:00:00", "2011-08-18"], ["2011-08-18T00:00:00", "2011-08-18T00:00:00"], None),
        (["2011-08-18T00:00:00Z"], ["2011-08-18T00:00:00+00:00"], "UTC"),
        (["2011-08-18 00:00:00Z"], ["2011-08-18T00:00:00+00:00"], "UTC"),
        (["2011-08-18T00:00:00+0000"], ["2011-08-18T00:00:00+00:00"], "UTC"),
        (["2011-08-18T00:00:00-05:00"], ["2011-08-18T00:00:00-05:00"], "UTC-05:00"),
    ],
)
def test_specification_datetime_forms_preserve_timezone(
    tmp_path: Path,
    values: list[str],
    expected: list[str],
    expected_timezone: str | None,
) -> None:
    source = tmp_path / "datetime_forms.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: datetime\n#field_unit: iso8601\nTime\n"
        + "".join(f"{value}\n" for value in values),
        encoding="utf-8",
    )
    frame = read_one(source)
    assert [value.isoformat() for value in frame["Time"]] == expected
    if expected_timezone is None:
        assert frame["Time"].dt.tz is None
    else:
        assert str(frame["Time"].dt.tz) == expected_timezone


def test_mixed_naive_and_zoned_datetimes_keep_each_source_timezone(tmp_path: Path) -> None:
    source = tmp_path / "mixed_datetimes.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: datetime\n#field_unit: iso8601\nTime\n"
        "2011-08-18T00:00:00\n2011-08-18T00:00:00Z\n"
        "2011-08-18T00:00:00-05:00\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame["Time"].dtype == object
    assert frame["Time"].iloc[0] == pd.Timestamp("2011-08-18T00:00:00")
    assert frame["Time"].iloc[0].tzinfo is None
    assert frame["Time"].iloc[1] == pd.Timestamp("2011-08-18T00:00:00Z")
    assert frame["Time"].iloc[1].tzinfo is not None
    assert frame["Time"].iloc[2] == pd.Timestamp("2011-08-18T00:00:00-05:00")


def test_datetime_timezone_converts_aware_values_with_pandas(tmp_path: Path) -> None:
    source = tmp_path / "mixed_offsets.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: datetime\nTime\n"
        "2021-02-12T12:15:46+02:30\n2021-02-12T12:15:46Z\n",
        encoding="utf-8",
    )

    frames = geocsv.read(source, datetime_timezone="America/Los_Angeles")
    assert len(frames) == 1
    frame = frames[0]

    assert str(frame["Time"].dt.tz) == "America/Los_Angeles"
    assert frame["Time"].tolist() == [
        pd.Timestamp("2021-02-12T01:45:46-08:00"),
        pd.Timestamp("2021-02-12T04:15:46-08:00"),
    ]


def test_datetime_timezone_rejects_naive_values(tmp_path: Path) -> None:
    source = tmp_path / "naive_datetime.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: datetime\nTime\n"
        "2021-02-12T12:15:46\n",
        encoding="utf-8",
    )

    with pytest.raises(geocsv.GeoCSVError, match="datetime_timezone requires a timezone"):
        geocsv.read(source, datetime_timezone="UTC")


@pytest.mark.parametrize("field_type", ["string", "integer", "float", "datetime"])
@pytest.mark.parametrize("value", [" ", "   ", '" "'])
def test_whitespace_only_fields_raise_located_error(
    tmp_path: Path, field_type: str, value: str
) -> None:
    source = tmp_path / "whitespace_field.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#field_type: {field_type}\n"
        "#field_unit: unitless\nMeasurement\n"
        f"{value}\n",
        encoding="utf-8",
    )
    with pytest.raises(
        geocsv.GeoCSVError,
        match=r"line 5, field 'Measurement': invalid .*whitespace-only values are not missing",
    ) as exc_info:
        read_one(source)
    assert str(source.resolve()) in str(exc_info.value)


def test_wrong_width_fixture_is_rejected() -> None:
    with pytest.raises(geocsv.GeoCSVError, match="line 5.*3 fields"):
        read_one(FIXTURES / "bad_width.geocsv")


@pytest.mark.parametrize(
    "text, message",
    [
        ("#field_type: string\n#field_unit: unitless\nA\nx\n", "required #dataset"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless\nA,A\nx,y\n", "unique"),
        ("#dataset: GeoCSV\nA,\nx,y\n", "nonempty"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless\nA,B\nx,y\n", "field_type has 1 fields"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless,meters\nA\nx\n", "field_unit has 2 fields"),
        ("#dataset: GeoCSV\n#delimiter: '::'\n#field_type: string\n#field_unit: unitless\nA\nx\n", "delimiter"),
        ("#dataset: GeoCSV\n#field_type: boolean\n#field_unit: unitless\nA\ntrue\n", "unsupported field type"),
        ('#dataset: GeoCSV\n#field_long_name: "unclosed\nA\nx\n', "unterminated field_long_name quote"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless\nA\nx\n#delimiter: |\n", "new #dataset boundary"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_type: float\n#field_unit: unitless\nA\nx\n", "changed"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless\nA\n\"unclosed\n", "invalid CSV"),
        ("", "no header"),
    ],
)
def test_malformed_declarations_fail_clearly(tmp_path: Path, text: str, message: str) -> None:
    source = tmp_path / "invalid.geocsv"
    source.write_text(text, encoding="utf-8")
    with pytest.raises(geocsv.GeoCSVError, match=message):
        read_one(source)


def test_invalid_utf8_reports_source_as_geocsv_error(tmp_path: Path) -> None:
    source = tmp_path / "invalid_encoding.geocsv"
    source.write_bytes(b"#dataset: GeoCSV\nLabel\n\xff\n")
    with pytest.raises(geocsv.GeoCSVError, match="invalid UTF-8 input") as error:
        geocsv.read(source)
    assert str(source.resolve()) in str(error.value)
    assert isinstance(error.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize(
    "field_type, value",
    [
        ("integer", "1.5"), ("integer", "9223372036854775808"),
        ("float", "bad"), ("float", "1e309"), ("float", "1e-400"),
        ("datetime", "2025-02-30T00:00:00Z"),
        ("datetime", "2025/01/01"),
        ("datetime", "2025.01.01"),
        ("datetime", "2025-1-1"),
        ("datetime", "2025-01-01T12:00:00+1"),
        ("datetime", "2025-01-01T12:00:00+013"),
        ("datetime", "2025-01-01T00:00:00.123456789123Z"),
        ("datetime", "2025-01-01 00:00:00.123456789123"),
    ],
)
def test_invalid_values_name_the_source_field_and_line(
    tmp_path: Path, field_type: str, value: str
) -> None:
    source = tmp_path / "invalid_value.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#field_type: {field_type}\n#field_unit: unitless\n"
        f"CustomField\n{value}\n", encoding="utf-8"
    )
    with pytest.raises(geocsv.GeoCSVError, match="line 5, field 'CustomField'"):
        read_one(source)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2025-01-01T1:00:00.123456789012",
        "2025-01-01T12:1:00.123456789012",
        "2025-01-01T12:00:1.123456789012",
        "2025-01-01 1:00:00.123456789012",
    ],
)
def test_nonpadded_times_cannot_bypass_fraction_precision_check(
    tmp_path: Path, timestamp: str,
) -> None:
    source = tmp_path / "excess_precision.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#field_type: datetime\nTime\n{timestamp}\n",
        encoding="utf-8",
    )
    with pytest.raises(
        geocsv.GeoCSVError,
        match=r"line 4, field 'Time': .*more than nine fractional digits",
    ) as error:
        geocsv.read(source)
    assert str(source.resolve()) in str(error.value)


@pytest.mark.parametrize("value", ["NaT", "nat", "NAT"])
@pytest.mark.parametrize("declaration", ["", "#field_missing: ABSENT\n"])
def test_nat_tokens_are_case_insensitive_datetime_missing_values(
    tmp_path: Path, value: str, declaration: str,
) -> None:
    source = tmp_path / "datetime_nat.geocsv"
    source.write_text(
        f"#dataset: GeoCSV\n#field_type: datetime\n{declaration}Time\n{value}\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame.shape == (1, 1)
    assert frame["Time"].iloc[0] is pd.NaT
    assert frame.index.equals(pd.RangeIndex(1, name="source_record_index"))
    assert frame.attrs["geocsv"].source_path == source.resolve()
    expected_sentinels = {"Time": "ABSENT"} if declaration else {}
    assert frame.attrs["geocsv"].field_missing == expected_sentinels


def test_explicit_nat_sentinel_preserves_typed_missing_and_string_values(
    tmp_path: Path,
) -> None:
    source = tmp_path / "declared_nat.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: datetime,string\n#field_missing: NaT,\n"
        "Time,Label\nNaT,NaT\n2025-01-01T00:00:00Z,nat\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert isinstance(frame["Time"].dtype, pd.DatetimeTZDtype)
    assert str(frame["Time"].dt.tz) == "UTC"
    assert frame["Time"].iloc[0] is pd.NaT
    assert frame["Time"].iloc[1] == pd.Timestamp("2025-01-01T00:00:00Z")
    assert frame["Label"].dtype == "string"
    assert frame["Label"].tolist() == ["NaT", "nat"]
    assert frame.index.equals(pd.RangeIndex(2, name="source_record_index"))
    assert frame.attrs["geocsv"].field_missing == {"Time": "NaT", "Label": ""}
    assert frame.attrs["geocsv"].source_path == source.resolve()


def test_header_only_dataset_is_typed(tmp_path: Path) -> None:
    source = tmp_path / "empty.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: datetime,float,integer,string\n"
        "#field_unit: iso8601,meters,unitless,unitless\nTime,Height,Count,Label\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame.empty
    assert frame["Time"].dt.tz is None
    assert frame["Height"].dtype == "Float64"
    assert frame["Count"].dtype == "Int64"


@pytest.mark.parametrize("rows", ["", "nan\nNaT\n"])
@pytest.mark.parametrize("datetime_timezone", [None, "UTC"])
def test_datetime_without_source_timestamps_has_no_timezone(
    tmp_path: Path, rows: str, datetime_timezone: str | None
) -> None:
    source = tmp_path / "missing_datetimes.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: datetime\nTime\n" + rows,
        encoding="utf-8",
    )
    frame = geocsv.read(source, datetime_timezone=datetime_timezone)[0]
    assert pd.api.types.is_datetime64_any_dtype(frame["Time"])
    assert frame["Time"].dt.tz is None
    assert len(frame) == len(rows.splitlines())
    assert frame["Time"].isna().all()


def test_signed_int64_boundaries_are_preserved(tmp_path: Path) -> None:
    source = tmp_path / "integer_boundaries.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: integer\nNumber\n"
        "-9223372036854775808\n9223372036854775807\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame["Number"].dtype == "Int64"
    assert frame["Number"].tolist() == [-(2**63), 2**63 - 1]


def test_explicit_infinity_is_distinct_from_finite_overflow(tmp_path: Path) -> None:
    source = tmp_path / "explicit_infinity.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: float\nValue\ninf\n",
        encoding="utf-8",
    )
    assert isinf(read_one(source)["Value"].iloc[0])


def test_canonical_p0006_content_metadata_and_provenance() -> None:
    frame = read_one(str(CANONICAL))
    assert frame.shape == (20345, 16)
    assert list(frame.columns) == [
        "MethodIdentifier", "StartTime", "Network", "Station", "Location", "Channel",
        "DataQuality", "Latitude", "Longitude", "Elevation", "WaterPressure",
        "InstrumentDescription", "SampleRate", "SampleCount", "TimeDelay", "TimeCorrection",
    ]
    assert isinstance(frame.index, pd.RangeIndex)
    assert frame.index.name == "source_record_index"
    assert frame["Station"].eq("P0006").all()
    assert str(frame["StartTime"].dt.tz) == "UTC"
    assert frame.iloc[0]["StartTime"] == pd.Timestamp("2018-06-27T19:16:42Z")
    assert frame.iloc[0]["Latitude"] == -14.453383
    assert frame.iloc[-1]["StartTime"] == pd.Timestamp("2025-03-12T20:55:57Z")
    assert frame["SampleCount"].dtype == "Int64"
    assert frame["SampleCount"].isna().sum() == 19517
    assert frame["DataQuality"].isna().sum() == 19517
    assert frame.iloc[0]["Location"] is pd.NA
    assert frame["Latitude"].dtype == "Float64"
    metadata = frame.attrs["geocsv"]
    assert metadata.source_path == CANONICAL.resolve()
    assert len(metadata.comments) == 11
    assert all(comment.raw.startswith("#") for comment in metadata.comments)
    assert metadata.delimiter == ","
    description = next(comment for comment in metadata.comments if comment.key == "description")
    assert description.value.endswith("hydrophones, www.EarthScopeOceans.org")
    assert metadata.field_units["WaterPressure"] == "mbar"
    assert metadata.field_types["SampleCount"] == "integer"
    assert any(comment.value == "2026-08-12T20:53:14.396Z" for comment in metadata.comments)
    collision = frame.loc[frame["StartTime"].eq(pd.Timestamp("2019-04-23T19:31:14Z"))]
    assert collision.index.tolist() == [5536, 5537]
    assert collision["MethodIdentifier"].tolist() == [
        "Measurement:Pressure:KELLER_Series_6", "Algorithm(thermocline):automaid:v4.5.9",
    ]
    assert pd.isna(collision.iloc[0]["Latitude"])
    assert collision.iloc[1]["Latitude"] == -14.752247
