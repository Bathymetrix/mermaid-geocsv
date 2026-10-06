"""GeoCSV scientific content, framing, and public-result contracts."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
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


def test_single_dataset_read_still_returns_a_list() -> None:
    frames = geocsv.read(CANONICAL)
    assert isinstance(frames, list)
    assert len(frames) == 1
    assert isinstance(frames[0], pd.DataFrame)


def test_metadata_preserves_comments_declarations_and_immutability() -> None:
    frame = read_one(FIXTURES / "typed.geocsv")
    metadata = frame.attrs["geocsv"]
    assert isinstance(metadata, geocsv.GeoCSVMetadata)
    assert metadata.source_path == (FIXTURES / "typed.geocsv").resolve()
    assert metadata.delimiter == ","
    assert metadata.field_types["SampleCount"] == "integer"
    assert metadata.field_units["Latitude"] == "degrees_north"
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
        f'"{column_name}"\nhello\n# custom : after\n #literal data\nworld\n',
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
        ("custom", 'before, with "quotes"', 5), ("custom", "after", 8),
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
        "#dataset: geocsv future-version\n#title: second table\n"
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
        assert frame["Time"].dtype == "datetime64[us]"
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
    assert str(frame["Time"].dt.tz) == "UTC"
    assert frame.iloc[0].isna().all()
    assert frame.attrs["geocsv"].source_path == source.resolve()


@pytest.mark.parametrize(
    "values, expected, expected_timezone",
    [
        (["2011-08-18T00:00:00", "2011-08-18"], ["2011-08-18T00:00:00", "2011-08-18T00:00:00"], None),
        (["2011-08-18T00:00:00Z"], ["2011-08-18T00:00:00+00:00"], "UTC"),
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


def test_multiple_dataset_fixture_returns_separate_frames() -> None:
    frames = geocsv.read(FIXTURES / "multiple_datasets.geocsv")
    assert len(frames) == 2
    assert frames[0]["Station"].tolist() == ["P0006"]
    assert frames[1]["Station"].tolist() == ["P0007"]
    assert list(frames[0].index) == [0]
    assert list(frames[1].index) == [1]


@pytest.mark.parametrize(
    "text, message",
    [
        ("#field_type: string\n#field_unit: unitless\nA\nx\n", "required #dataset"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless\nA,A\nx,y\n", "unique"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless\nA,B\nx,y\n", "field_type has 1 fields"),
        ("#dataset: GeoCSV\n#field_type: string\n#field_unit: unitless,meters\nA\nx\n", "field_unit has 2 fields"),
        ("#dataset: GeoCSV\n#delimiter: '::'\n#field_type: string\n#field_unit: unitless\nA\nx\n", "delimiter"),
        ("#dataset: GeoCSV\n#field_type: boolean\n#field_unit: unitless\nA\ntrue\n", "unsupported field type"),
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


@pytest.mark.parametrize(
    "field_type, value",
    [
        ("integer", "1.5"), ("integer", "9223372036854775808"),
        ("float", "bad"), ("datetime", "2025-02-30T00:00:00Z"),
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


def test_header_only_dataset_is_typed(tmp_path: Path) -> None:
    source = tmp_path / "empty.geocsv"
    source.write_text(
        "#dataset: GeoCSV\n#field_type: datetime,float,integer,string\n"
        "#field_unit: iso8601,meters,unitless,unitless\nTime,Height,Count,Label\n",
        encoding="utf-8",
    )
    frame = read_one(source)
    assert frame.empty
    assert str(frame["Time"].dt.tz) == "UTC"
    assert frame["Height"].dtype == "Float64"
    assert frame["Count"].dtype == "Int64"


def test_canonical_p0006_content_metadata_and_source_integrity() -> None:
    original_hash = sha256(CANONICAL.read_bytes()).digest()
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
    assert sha256(CANONICAL.read_bytes()).digest() == original_hash
