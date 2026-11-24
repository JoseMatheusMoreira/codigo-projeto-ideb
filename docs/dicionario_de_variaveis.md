# Dicionário de variáveis

O dicionário detalhado das colunas finais está em `docs/dicionario_variaveis_completo.csv`.
Este arquivo mantém o histórico das fontes e das regras gerais; a tabela CSV
contém uma linha por coluna efetivamente disponível na base final.

## Fontes

| Fonte | Arquivo utilizado | Ano/período | Data de download | Observações |
|---|---|---:|---|---|
| IDEB/INEP | `data/raw/ideb_anos_iniciais_municipios_2025.xlsx` | 2023/2025 | 2026-11-15 | Aba `IDEB_AI_MUNICÍPIOS`; cabeçalho na linha 10 do Excel |
| Censo Escolar/INEP | `data/raw` fornecido pelo usuário; microdados de educação básica | 2024 | Diretório local fornecido pelo usuário | Agregação para município |
| Indicadores Educacionais/INEP | não integrado | 2024 | — | Extensão futura |
| IBGE | SIDRA 5938 e 9514 | 2022/2023 | API pública do SIDRA | PIB e população |

## Variáveis da base final

| Nome da coluna | Fonte | Ano | Descrição | Tipo | Unidade | Bloco | Pode ser entrada? | Tratamento | Observações |
|---|---|---:|---|---|---|---|---|---|---|
| `CO_MUNICIPIO` | IBGE/INEP | — | Identificador do município | Numérico | código IBGE | Chave | Não | Converter para string de 7 dígitos | Conferir zeros à esquerda |
| `REDE` | IDEB/INEP | — | Rede de ensino | Categórica | texto | Filtro | Não | Filtrar `Municipal` | Não usar linhas `Pública` como substitutas |
| `VL_OBSERVADO_2025` | IDEB/INEP | 2025 | IDEB observado dos anos iniciais | Numérico/texto | escala IDEB | Alvo | Não | Converter `-` para ausente; não imputar | Excluir linhas sem alvo |
| `VL_OBSERVADO_2023` | IDEB/INEP | 2023 | IDEB histórico observado dos anos iniciais | Numérico/texto | escala IDEB | C | Sim | Converter `-` para ausente | Permitido por ser anterior ao alvo |

## Blocos de ablação

- **A — Contexto:** variáveis socioeconômicas e demográficas.
- **B — Contexto + Educação:** A mais infraestrutura e indicadores educacionais de 2024.
- **C — Contexto + Educação + Histórico:** B mais `ideb_2023`.

Antes do treinamento, substituir essa descrição pelos nomes exatos das colunas em cada bloco.

## Checklist de validação temporal

- [ ] Cada coluna tem fonte e ano registrados.
- [ ] Nenhuma entrada usa Saeb 2025, aprovação 2025 ou outra informação posterior a 2024.
- [ ] O IDEB 2025 aparece apenas como alvo.
- [ ] Foi verificado se algum indicador educacional já incorpora o alvo ou dados de 2025.
- [ ] As transformações e imputações serão aprendidas apenas no treino.

## Verificação já realizada para o arquivo do IDEB

- Aba identificada: `IDEB_AI_MUNICÍPIOS`.
- Total de linhas de dados: 14.533.
- Linhas da rede `Municipal`: 5.450.
- Municípios únicos na rede municipal: 5.450.
- IDEB 2023 disponível na rede municipal: 5.241.
- IDEB 2025 disponível na rede municipal: 5.320.
- Para a base supervisionada com os dois IDEBs, a interseção calculada é de 5.196 municípios; há 45 municípios apenas com IDEB 2023 e 124 apenas com IDEB 2025.
