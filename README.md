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
