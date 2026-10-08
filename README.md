# EditHTML — Relatórios editáveis do Navisworks

Converte um **Clash Report HTML** e uma pasta de imagens em um relatório HTML autônomo e editável.

## Instalação

```bash
pip install -r requirements.txt
```

## Executar

```bash
python edit_html.py "ELE X HID (TIPO).html" "ELE X HID (TIPO)_files" -o relatorio_editavel.html
```

Abra o arquivo gerado no navegador. Preencha **Descrição**, **Prioridade**, **Responsável** e **Disciplina** de cada Item 1 e Item 2.

- **Salvar HTML**: baixa uma nova cópia com os valores digitados, que continua editável.
- **Salvar PDF**: abre a caixa de impressão do navegador; selecione **Salvar como PDF**. Os valores atuais aparecem na versão impressa.

**Importante:** o navegador não permite gravar automaticamente sobre o arquivo original. O botão Salvar HTML gera um download. O botão Salvar PDF utiliza a impressão nativa do navegador (não grava diretamente em uma pasta sem interação).

## Configuração

Modifique a variável `CAMPOS_REMOVER` no início de `edit_html.py` para personalizar os nomes dos campos removidos:

```python
CAMPOS_REMOVER = ["Distance", "Clash Point", "Grid Location", "Item Type"]
```

Ou substitua a lista pelo terminal:

```bash
python edit_html.py entrada.html pasta_imagens --remover "Distance" "Grid Location"
```

A busca dos nomes dos campos ignora diferenças de maiúsculas/minúsculas e acentos. As imagens são localizadas pelo nome do arquivo dentro da pasta informada e de suas subpastas e incorporadas ao HTML em Base64.

## Requisitos e limitações

Python 3.10+ e Beautiful Soup 4. Destinado a relatórios HTML do Navisworks com blocos `div.viewpoint` e campos `span.namevaluepair`. Imagens inexistentes serão listadas no terminal. Para exportar em PDF, use um navegador com suporte a impressão.

## Interface gráfica (Windows / macOS / Linux)

Execute após instalar as dependências:

```bash
python interface.py
```

Use os três botões **Selecionar...** para escolher o HTML original, a pasta de imagens e o arquivo HTML de saída. Clique em **Gerar relatório editável**. O PDF é gerado posteriormente no próprio relatório, pelo botão **Salvar PDF** (caixa de impressão do navegador).

A interface utiliza **Tkinter**, normalmente incluído na instalação padrão do Python. Não é necessário instalar pacote de interface via `pip`.

## Campos do cabeçalho

O campo **Tolerance/Tolerância** do cabeçalho de cada relatório é substituído por **Data**, **Arquivo 1**, **Arquivo 2** e **Versão**, cada um com caixa de texto editável de até **20 caracteres**. Os valores são preservados ao usar o botão **Salvar HTML**. O funcionamento também vale para a interface gráfica (`python interface.py`).

## Módulo independente: preenchimento de descrições pela planilha

Execute:

```powershell
git pull
pip install -r requirements.txt
python preencher_descricoes.py
```

Selecione o HTML editável, uma planilha Excel (.xlsx/.xlsm) e onde salvar o HTML preenchido.

A planilha deve ter as colunas **Nome**, **Item**, **Element ID**, **Descrição** e **Quem altera**. Cada interferência ocupa duas linhas com o mesmo Nome, uma para Item 1 e outra para Item 2:

| Nome | Item | Element ID | Descrição | Quem altera |
|---|---|---|---|---|
| Clash1 | 1 | 16997963 | Ajustar tubulação | HID |
| Clash1 | 2 | 2942017 | Ajustar tubulação | HID |

O programa agrupa as duas linhas pelo Nome (separadamente por aba), forma o par de IDs e **procura esse par no HTML**, independentemente da ordem. A planilha pode conter registros de muitos relatórios HTML: os pares que não existem no arquivo selecionado são ignorados. A correspondência usa o **par completo de Element IDs**, não apenas um ID isolado.

**Descrição** preenche **Description** e **Quem altera** preenche **Responsável** (limitado a 3 caracteres no HTML). Caso apenas uma das linhas tenha os textos preenchidos, são utilizados os valores não vazios. Valores vazios não apagam conteúdo do HTML. Valores conflitantes entre as duas linhas, grupos incompletos ou repetição de pares com informações conflitantes não são aplicados automaticamente.

Os cabeçalhos aceitos podem ser ajustados em `COLUNAS` no arquivo `preencher_descricoes.py`. A planilha XLSM é apenas lida; macros não são executadas.
