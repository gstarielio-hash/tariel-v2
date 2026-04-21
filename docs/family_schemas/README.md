# Family Schemas

Diretorio canonico para os JSONs de familia do produto Tariel.

Regras:

- um arquivo por familia;
- nome do arquivo igual ao `family_key`;
- JSON declarativo da familia, nao de tenant e nao de caso real;
- sem branding de empresa;
- sem status operacional;
- usado como base para publicacao no catalogo oficial do Admin-CEO.

Artefatos complementares por familia:

- `<family_key>.laudo_output_seed.json`: contrato-base do `laudo_output` da familia;
- `<family_key>.laudo_output_exemplo.json`: exemplo preenchido para validacao humana e render;
- `<family_key>.template_master_seed.json`: seed inicial de `template_master` em `editor_rico`.

Regra pratica:

- o `family_schema` define a familia;
- o `laudo_output` materializa o caso revisado;
- o `template_master` transforma esse `laudo_output` em documento humano e PDF.
