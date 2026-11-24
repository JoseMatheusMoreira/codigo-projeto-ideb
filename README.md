# Previsão do IDEB 2025

Projeto de Reconhecimento de Padrões para investigar se o IDEB 2025 dos anos
iniciais das redes municipais pode ser previsto com informações disponíveis até
2024.

## O que entra no modelo

- IDEB municipal de 2023, como informação histórica;
- Censo Escolar 2024, agregado para o município;
- PIB municipal de 2023 e população do Censo 2022, obtidos do IBGE.

O alvo é `VL_OBSERVADO_2025`. O código do município identifica a observação,
mas não é usado como variável preditora.

## Organização

- `data/raw/`: arquivos originais, mantidos localmente e fora do Git;
- `data/processed/`: bases geradas pelo processamento;
- `notebooks/`: execução documentada das etapas principais;
- `src/`: funções e scripts de preparação, análise e modelagem;
- `docs/`: dicionário de variáveis e decisões metodológicas;
- `results/`: tabelas e gráficos gerados localmente.

Os materiais da apresentação ficam em uma pasta separada do repositório de
código.

## Notebooks

1. `01_preparacao_ideb_municipal.ipynb`;
2. `02_selecao_colunas_censo_escolar.ipynb`;
3. `03_filtro_linhas_censo_escolar.ipynb`;
4. `04_diagnostico_nulos_censo.ipynb`;
5. `05_analise_zeros_doc_turmas.ipynb`;
6. `06_tratamento_banda_larga.ipynb`;
7. `07_agregacao_censo_municipio.ipynb`.

Os notebooks devem ser executados nessa ordem. A análise exploratória e a
modelagem podem ser executadas pelos scripts correspondentes em `src/`.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Os microdados brutos não são distribuídos neste repositório. Para reproduzir o
pipeline, coloque os arquivos nas localizações descritas em
`docs/decisoes_metodologicas.md` e ajuste os caminhos de entrada nos scripts,
se necessário.

## Resultado preliminar

A base municipal final possui 5.196 municípios e 35 colunas. Na primeira rodada,
a Ridge usando IDEB 2023 e variáveis do Censo Escolar obteve MAE de 0,360, RMSE
de 0,488 e R² de 0,688 no conjunto de teste.
