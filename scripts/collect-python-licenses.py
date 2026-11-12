"""Collect distribution metadata/license texts without importing inference runtimes."""
import importlib.metadata
import json
import sys
from pathlib import Path

output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
inventory=[]
for dist in sorted(importlib.metadata.distributions(),key=lambda d:d.metadata.get('Name','').lower()):
    name=dist.metadata.get('Name','unknown');version=dist.version
    folder=output/(name+'-'+version);folder.mkdir(exist_ok=True)
    metadata=dist.metadata
    (folder/'METADATA.txt').write_text(str(metadata),encoding='utf-8')
    licenses=[]
    for file in dist.files or []:
        lower=str(file).lower()
        if any(part in Path(lower).name for part in ('license','copying','notice')):
            path=Path(dist.locate_file(file))
            if path.is_file():
                target=folder/Path(file).name
                target.write_bytes(path.read_bytes());licenses.append(target.name)
    inventory.append(dict(name=name,version=version,license_expression=metadata.get('License-Expression'),
                          declared_license=metadata.get('License'),home_page=metadata.get('Home-page'),license_files=licenses))
(output/'inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
