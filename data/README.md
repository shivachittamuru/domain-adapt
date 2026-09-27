# Local data

Downloaded datasets and model-run artifacts stay local and are ignored by Git.
The notebooks need only this small financial subset:

```text
data/
  financial.sqlite
  finch_dataset.json
  financial_metadata/database_description/
    account.csv
    card.csv
    client.csv
    disp.csv
    district.csv
    loan.csv
    order.csv
    trans.csv
  runs/
```

The metadata files come from BIRD's
`dev_databases/financial/database_description` directory. Before deleting the
full BIRD download, copy those eight CSVs to the path above and validate their
combined hash:

```text
3f7be83f3f9bdba77d27a66ad38b1a81b3a40361168780f54ceedd985db5fc23
```

Once the copy and hash are verified, these extraction-only paths are not needed
by this project and can be removed locally:

```text
data/bird_dev.zip
data/bird_dev_outer/
data/bird_dev_databases/
```

Keep `financial.sqlite`, `finch_dataset.json`, `financial_metadata/`, and
`runs/`.
