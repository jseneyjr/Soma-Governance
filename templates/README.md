# Soma Templates

Templates are domain-specific cell packs that Genesis can use to seed initial cells in a new project. 

## How they work
During Genesis Stage 5, the system detects the project domain and copies matching templates to `.soma/cells/`. 
Templates are created with `expiry_sessions: 5` so they self-prune quickly if they are irrelevant to the specific project.
They are marked with `created: "template"` to distinguish them from discovered cells.

## Domain Detection
Genesis detects the project domain via:
- `requirements.txt` / `setup.py` (with torch/tensorflow) -> `rl-training` or `data-pipeline`
- `package.json` -> `web-backend`
- `Dockerfile` / `*.tf` -> `infrastructure`

## Creating Custom Template Packs
To create a custom pack, add a new directory here and populate it with `.md` files following the standard cell format.
