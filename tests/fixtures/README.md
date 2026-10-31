# Parser and waveform test inputs

[Schema 1.0.0](schema-1.0.0/README.md) contains the active synthetic parser and
association inputs. Real-data schema conversions live under
[`data/fixtures/schema-1.0.0`](../../data/fixtures/schema-1.0.0/README.md).

The top-level `.geocsv` files, `association/synthetic.geocsv` and
`association/indexed.geocsv` are frozen unsupported-schema source evidence.
They are unsupported by the current reader and are not active parsing inputs.
Their original bytes remain unchanged.

The real waveform directories under `association/` remain active:
[P0006 clipped response](association/P0006_20180713_earthscope/README.md) and
[P0045 combined window](association/P0045_20220115/README.md). Their original
manifests retain historical GeoCSV hashes; current tests parse separate schema
fixtures with documented mappings. SAC files are comparison references only.
