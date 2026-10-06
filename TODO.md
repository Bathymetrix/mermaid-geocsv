# TODO

- [ ] Propose a GeoCSV format amendment reserving case-insensitive `NaN`
  (e.g., `NaN`, `nan`, or `NAN`) and empty fields (e.g., `,,`) for missing data
  in every type, while retaining the existing per-column `field_missing`
  mechanism. This is a MERMAID proposal, not a rule in EarthScope GeoCSV
  v2.0.4.
  - Reserve every case variant of `NaN` exclusively for missing data, across
    all data types, including string fields. It is not a legitimate string
    literal or meaningful data value.
  - Explicitly document the consequence: users who intend `nan` as a meaningful
    word, name, verb, or noun must choose a different value. Existing data using
    it as meaningful text will need a replacement to comply with this rule.
  - Retain explicitly declared `field_missing` values as valid missing markers
    for their respective columns.
- [ ] Add a `write` method for writing MERMAID GeoCSV files. Refactor the
  existing legacy writer in `automaid/scripts/geocsv.py` into this package.
- [ ] Add a `fetch` method that takes an instrument ID (for example, `P0006`),
  builds the EarthScope MDA URL, and retrieves the most recent GeoCSV for that
  instrument. Consider an option to pass the fetched content directly to
  `read`.
- [x] Keep the v2.0.4 known keywords in one editable `_KNOWN_KEYWORDS` lookup
  and preserve their raw declarations in `metadata.comments`.
