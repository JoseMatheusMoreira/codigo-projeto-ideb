# Contexto e decisões metodológicas

## Objetivo

O projeto investiga se informações anteriores ou contemporâneas a 2024 ajudam a
prever o IDEB 2025 dos anos iniciais das redes municipais brasileiras. O IDEB
2025 é usado somente como variável-alvo.

## Fontes

- IDEB 2023 e 2025: arquivo municipal do INEP fornecido para o projeto;
- Censo Escolar 2024: microdados da educação básica do INEP;
- PIB municipal: SIDRA/IBGE, tabela 5938, ano 2023;
- população residente: SIDRA/IBGE, tabela 9514, ano 2022.

## Preparação do IDEB

Foi mantida a rede municipal e a interseção entre os municípios com IDEB 2023 e
2025, resultando em 5.196 municípios. `VL_OBSERVADO_2023` é uma variável
histórica; `VL_OBSERVADO_2025` é o alvo.

## Preparação do Censo Escolar

O arquivo foi validado antes do uso: separador `;`, codificação `latin1`, 426
colunas, 215.545 linhas, ano 2024 e chaves sem duplicidades. Foram selecionadas
colunas de identificação, filtros, infraestrutura, tecnologia, matrículas,
docentes e turmas.

O recorte principal manteve escolas municipais (`TP_DEPENDENCIA=3`), em
funcionamento (`TP_SITUACAO_FUNCIONAMENTO=1`) e com oferta dos anos iniciais
(`IN_FUND_AI=1`). O resultado contém 70.306 escolas e cobre todos os 5.196
municípios do IDEB.

## Valores nulos e zeros

Os nulos de `IN_BANDA_LARGA` ocorreram exclusivamente quando `IN_INTERNET=0`.
Eles foram convertidos para zero por uma regra estrutural de não aplicabilidade,
sem alterar as demais colunas.

Os zeros simultâneos em `QT_DOC_FUND_AI` e `QT_TUR_FUND_AI` foram mantidos. Eles
ocorreram em 12.013 escolas, com forte concentração em escolas rurais. Conforme
a regra de declaração considerada para escolas multisseriadas, esses zeros são
valores válidos usados para evitar duplicação de docentes e turmas entre etapas;
não representam automaticamente ausência de profissionais ou de classes.
Portanto, não foram imputados nem convertidos para nulos. Essas duas variáveis
ficaram fora da primeira agregação municipal para evitar interpretar os zeros
sem aplicar explicitamente a regra de declaração no cálculo municipal.

## Agregação municipal

Os indicadores `IN_*`, originalmente binários, foram resumidos como proporções
de escolas com o recurso. `TP_LOCALIZACAO` virou proporção de escolas rurais.
`CO_ENTIDADE` foi contado como número de escolas. `QT_MAT_FUND_AI` foi resumida
por total, média e mediana.

## IBGE

O PIB per capita foi calculado como PIB de 2023 dividido pela população do
Censo 2022. É uma aproximação, pois os anos de referência são diferentes.

## Modelagem

Os municípios foram separados em 70% treino, 15% validação e 15% teste, com
`random_state=42`. A escolha dos modelos foi feita na validação; o teste foi
preservado para a avaliação final.

Foram comparados baseline da média, Ridge, Random Forest e
HistGradientBoosting. A melhor primeira configuração foi Ridge com IDEB 2023 e
variáveis do Censo Escolar. O resultado no teste foi MAE 0,360, RMSE 0,488 e
R² 0,688.

Os indicadores educacionais adicionais do INEP ficaram fora da primeira versão
porque sua inclusão exigiria confirmar granularidade, chave municipal e regras
de agregação compatíveis.

## Critérios de escolha das variáveis

As variáveis foram selecionadas considerando quatro critérios:

1. disponibilidade até 2024;
2. possibilidade de conversão para uma linha por município;
3. relação plausível com oferta educacional, condições escolares ou contexto
   socioeconômico;
4. capacidade de explicar claramente o significado e o tratamento da variável.

O IDEB 2023 foi escolhido como histórico do próprio município. As variáveis do
Censo foram escolhidas para representar tamanho da rede, matrículas,
localização, infraestrutura física e conectividade. As variáveis do IBGE foram
incluídas para representar contexto econômico e demográfico.

Não foram usadas como preditoras as colunas de identificação, nomes dos
municípios ou o código `CO_MUNICIPIO`. O IDEB 2025 aparece exclusivamente como
alvo.

## Regras de agregação

O Censo Escolar possui uma linha por escola, mas o IDEB usado no projeto possui
uma linha por município. Por isso, as variáveis foram agregadas conforme sua
natureza:

- indicadores `IN_*` binários: média, interpretada como proporção de escolas
  com o recurso;
- localização: proporção de escolas rurais ou em localização diferenciada;
- `CO_ENTIDADE`: contagem de escolas únicas;
- `QT_MAT_FUND_AI`: soma, média e mediana das matrículas;
- docentes e turmas: mantidos fora da primeira agregação municipal enquanto a
  regra de declaração multisseriada não for aplicada de maneira específica.

Não foi aplicada uma média genérica a todas as colunas.

## Controle temporal e leakage

As entradas do modelo possuem as seguintes referências:

- IDEB histórico: 2023;
- Censo Escolar: 2024;
- PIB: 2023;
- população: 2022.

O IDEB 2025 é usado somente como `y`. Também foram preservados conjuntos de
treino, validação e teste separados. Imputação e padronização, quando
necessárias, são aprendidas dentro do pipeline e somente com os dados de
treinamento.

## Resultados preliminares

A base final possui 5.196 municípios. A primeira comparação utilizou baseline
da média, Ridge, Random Forest e HistGradientBoosting. A configuração inicial
com melhor desempenho foi a Ridge usando o IDEB 2023 e as variáveis do Censo,
com MAE de aproximadamente 0,360, RMSE de 0,488 e R² de 0,688 no teste.

Esse resultado é preliminar e não deve ser interpretado como causalidade. Ele
indica apenas o desempenho preditivo observado no protocolo definido.
