# Dados

Os arquivos brutos não são versionados por causa do tamanho e das regras de
distribuição das fontes.

Coloque localmente:

- o Excel municipal do IDEB em `data/raw/ideb_anos_iniciais_municipios_2025.xlsx`;
- o microdado principal do Censo Escolar 2024 no caminho configurado em
  `src/filtrar_censo_escolar.py`;
- os arquivos processados serão gravados em `data/processed/`.

A base municipal final usada nos testes locais é gerada pelo pipeline e não deve
ser editada manualmente.
