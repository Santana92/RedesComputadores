# Comunicação de Dados na Camada Física usando Som 🔊💻

[![Licença MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Status dos Testes](https://img.shields.io/badge/Testes%20Automatizados-30%20Aprovados%20(100%25)-success.svg)](#9-testes-e-validação)

Trabalho prático da disciplina de **Redes de Computadores** focado no desenvolvimento, análise e validação experimental da **Camada Física** e subcamada de enlace lógico utilizando o **ar atmosférico e ondas acústicas** como meio de transmissão não guiado.

---

## 📹 Vídeo de Demonstração

- **Vídeo de Demonstração (Apresentação Individual):** `[INSERIR LINK DO VÍDEO NO YOUTUBE - 3 A 7 MINUTOS]`
- **Thumbnail / Prévia:**  
  *(Espaço reservado para inserção da imagem de prévia da gravação individual)*

---

## 1. Introdução e Objetivo da Atividade

O objetivo fundamental deste trabalho é projetar e implementar um sistema completo de comunicação digital na **Camada Física** (Camada 1 do Modelo OSI), operando através de ondas sonoras mecânicas propagadas pelo ar entre alto-falantes e microfones.

O software foi concebido como um **modem acústico único**, capaz de atuar em ambos os papéis da comunicação:
- **Transmissor (TX):** Transforma mensagens digitais em sinais acústicos audíveis emitidos pelo alto-falante ou orienta a emissão física manual.
- **Receptor (RX):** Captura ondas sonoras pelo microfone, processa o sinal analógico, recupera a sequência binária e reconstrói a mensagem original com verificação de integridade.

O sistema implementa dois métodos acústicos independentes, cada um utilizando uma característica distinta do sinal físico:
1. **Método 1 — Quantidade de Impactos:** A informação binária está na **quantidade** de pulsos acústicos (0 = 1 impacto isolado `•`, 1 = 2 impactos consecutivos rápidos `••`). O Método 1 suporta duas modalidades de transmissão:
   - **Transmissão Automática:** O próprio computador sintetiza os impactos acústicos e os emite pelo alto-falante.
   - **Transmissão Manual:** O usuário produz os impactos fisicamente (palmas, batidas na mesa, estalos de dedos, cliques de caneta) diante do microfone, sem qualquer emissão de áudio pelo computador.
   Ambas as modalidades utilizam enquadramento em blocos de 9 bits (8 dados + 1 paridade par) e verificação de erro por **Paridade Par**.
2. **Método 2 — Duração do Impacto:** A informação binária está na **duração temporal** de um único impacto acústico (0 = impacto curto de 50 ms, 1 = impacto longo de 160 ms), com sincronização por preâmbulo (10101010) e detecção de erro robusta por **CRC-8** (polinômio ATM `0x07`).

---

## 2. Fundamentação Teórica

### 2.1. O Modelo ISO/OSI e o Escopo do Projeto

O modelo de referência ISO/OSI estrutura a arquitetura de redes em sete camadas conceituais. Este projeto concentra-se rigorosamente nas duas primeiras camadas da pilha:

| # | Camada | Função Conceitual | Implementação Concreta neste Projeto |
| :---: | :--- | :--- | :--- |
| **7** | **Aplicação** | Ponto de contato com o usuário. | Interface gráfica (Tkinter) e modo terminal interativo (CLI). |
| **6** | **Apresentação** | Codificação e formatação de texto. | Conversão de caracteres em bytes ASCII / UTF-8. |
| **5** | **Sessão** | Controle de diálogo e abertura/fechamento. | Controle explícito de início e término de escuta/transmissão. |
| **4** | **Transporte** | Confiabilidade ponta a ponta e controle de fluxo. | *(Não implementado — comunicação direta datagrama).* |
| **3** | **Rede** | Roteamento e endereçamento lógico global. | *(Não implementado — enlace direto ponto a ponto).* |
| **2** | **Enlace de Dados** | **Enquadramento (*framing*), alinhamento e detecção de erros.** | **Quadros de 9 bits com Paridade Par (Método 1) e Pacotes delimitados com CRC-8 (Método 2).** |
| **1** | **Física** | **Transmissão e recepção de bits brutos no meio físico.** | **Transdutores acústicos (Alto-falante D/A e Microfone A/D) via Quantidade de Impactos ou Duração do Impacto.** |

### 2.2. Aprofundamento na Camada Física
A Camada Física é a camada mais baixa da arquitetura e tem a responsabilidade de transmitir a sequência bruta de bits através do meio de transmissão:
- **Meio Físico Utilizado:** O ar atmosférico em temperatura e pressão ambiente, que atua como meio contínuo elástico não guiado.
- **Sinal Físico:** Ondas mecânicas longitudinais de pressão (compressão e rarefação periódica das moléculas do ar).
- **Transdutor Emissor (Conversor D/A Acústico):** O alto-falante, que recebe tensões elétricas geradas pela placa de som e move mecanicamente seu diafragma para criar a onda sonora.
- **Transdutor Receptor (Conversor A/D Acústico):** O microfone, cuja membrana vibra sob a pressão acústica incidente no ar e gera um sinal elétrico analógico amostrado digitalmente pela placa de som.

### 2.3. Sinais Analógicos e Digitais
- **Sinal Digital:** Sequência discreta de símbolos binários ($0$ e $1$) manipulada pela CPU e pela memória.
- **Sinal Analógico:** Onda contínua de pressão sonora $p(t)$ medida em Pascals ($\text{Pa}$) propagando-se no ar.
- **Fluxo do Sinal:**
  $$\text{Bits Digitais } (0, 1) \xrightarrow{\text{Modulação / Síntese}} s(t) \text{ [Analógico]} \xrightarrow{\text{Alto-falante} \to \text{Ar} \to \text{Microfone}} r(t) \xrightarrow{\text{Envelope / Detecção}} \text{Bits Recuperados } (0, 1)$$

### 2.4. Taxa de Amostragem (*Sampling Rate*)
Conforme o **Teorema de Amostragem de Nyquist-Shannon**, para reproduzir e capturar um sinal com fidelidade sem falseamento espectral (*aliasing*), a taxa de amostragem $F_s$ deve ser maior que o dobro da frequência máxima presente no sinal ($F_s > 2 f_{\max}$):
- O sistema adota $F_s = 44.100\text{ Hz}$ com amostras em ponto flutuante de 32 bits (`np.float32`).
- Com os pulsos acústicos centrados em $900\text{ Hz}$, a taxa de amostragem de $44.100\text{ Hz}$ fornece uma sobreamostragem de quase $50\times$, garantindo excelente resolução temporal para a medição da duração e dos intervalos entre impactos.

### 2.5. Ruído e Atenuação no Meio Acústico
O canal acústico não guiado apresenta perturbações que não ocorrem em cabos metálicos ou fibra óptica:
1. **Atenuação por Divergência Geométrica:** A energia da onda esférica dissipa com o quadrado da distância ($I \propto 1/r^2$).
2. **Reverberação e Ecos de Multipropagação:** Ondas refletidas em mesas, paredes e telas chegam ao microfone com pequenos atrasos, prolongando a cauda do som.
3. **Ruído Aditivo de Fundo:** Ar-condicionado, ventoinhas de computador e conversas no ambiente introduzem energia contínua.

### 2.6. Fundamentos Teóricos da Detecção de Erros
- **Bit de Paridade Simples (Método 1):**
  Soma em módulo 2 dos 8 bits de dados:
  $$b_{\text{paridade}} = \left(\sum_{i=1}^8 b_i\right) \bmod 2$$
  *Propriedade:* Detecta confiavelmente qualquer número ímpar de bits invertidos (1, 3, 5 ou 7). Se dois bits forem invertidos simultaneamente, a paridade permanece a mesma e o erro não é detectado.
- **Código de Redundância Cíclica - CRC-8 (Método 2):**
  Trata a sequência binária como coeficientes de um polinômio $M(x)$ em $\text{GF}(2)$. Divide polinomialmente pelo polinômio gerador padrão ATM/SMBus $G(x) = x^8 + x^2 + x + 1$ (`0x07`).
  *Propriedade:* Detecta 100% dos erros simples de bit, 100% dos erros duplos, 100% de qualquer quantidade ímpar de erros e 100% das rajadas de erro de até 8 bits.

---

## 3. Arquitetura do Sistema

O sistema foi estruturado modularmente em Python, com separação estrita entre a conversão de dados, detecção de erros, controladores da camada física e interface com o usuário:

```text
Atividade1/
│
├── main.py                         # Ponto de entrada raiz (executa GUI ou CLI)
├── requirements.txt                # Dependências (numpy, sounddevice)
├── LICENSE                         # Licença MIT Open Source
├── README.md                       # Documentação técnica completa
│
├── src/
│   ├── __init__.py
│   ├── conversao.py                # Conversão: Texto <-> Bytes <-> Bits e formatação
│   ├── deteccao_erros.py           # Paridade Par (quadros 9 bits) e CRC-8 (polinômio 0x07)
│   ├── interface.py                # Interface gráfica completa em Tkinter nativo
│   ├── main.py                     # Controlador CLI e despachante da interface
│   │
│   ├── metodo1_batidas/            # Camada Física: Método 1 (Quantidade de Impactos)
│   │   ├── __init__.py
│   │   ├── transmissor.py          # Síntese dos impactos (1 impacto = 0, 2 impactos = 1)
│   │   └── receptor.py             # Escuta contínua, máquina de estados e limiar adaptativo
│   │
│   └── metodo2_duracao/            # Camada Física: Método 2 (Duração do Impacto)
│       ├── __init__.py
│       ├── transmissor.py          # Síntese por duração (curto = 50ms, longo = 160ms)
│       └── receptor.py             # Envelope de energia, medição de duração e CRC-8
│
└── tests/                          # Suíte de 25 testes automatizados (unittest)
    ├── __init__.py
    ├── test_metodo1.py             # Testes do Método 1 (paridade, síntese, ruído)
    ├── test_metodo2.py             # Testes do Método 2 (CRC-8, durações, preâmbulo, ruído)
    └── test_requisitos_completos.py# Mapeamento formal dos 9 requisitos de avaliação
```

### 3.1. Papel Transmissor (TX)
Coleta a mensagem de texto, converte em bytes e bits, adiciona os mecanismos de verificação de erro (paridade ou CRC-8), sintetiza a forma de onda de áudio e reproduz nos alto-falantes.

### 3.2. Papel Receptor (RX)
Captura o áudio analógico pelo microfone, processa o sinal para detectar os impactos, extrai os bits conforme o método selecionado, valida os mecanismos de verificação e reconstrói o texto original.

### 3.3. Caminho Físico Real (Regra Fundamental)
O software **não compartilha variáveis internas, memória ou arquivos entre transmissor e receptor**. Toda a comunicação demonstrada percorre exclusivamente o meio físico:
$$\textbf{Transmissor} \longrightarrow \textbf{Alto-falante} \xrightarrow[\text{Ondas Mecânicas}]{\textbf{Ar / Ambiente}} \textbf{Microfone} \longrightarrow \textbf{Receptor} \longrightarrow \textbf{Mensagem}$$

---

## 4. Método 1 — Quantidade de Impactos

No Método 1, a informação binária é representada diretamente pela **quantidade de impactos acústicos** emitidos dentro de uma janela de tempo. O método oferece duas formas reais de transmissão:
1. **Transmissão Automática:** O próprio computador sintetiza os impactos acústicos e os reproduz pelo alto-falante.
2. **Transmissão Manual:** O usuário produz os impactos fisicamente (palmas, batidas na mesa, estalos de dedos ou clique de caneta) diante do microfone, e o computador apenas escuta e decodifica.

### 4.1. Codificação dos Bits
- **Bit 0:** Representado por **1 impacto acústico isolado** (`•`).
- **Bit 1:** Representado por **2 impactos acústicos consecutivos rápidos** (`••`), com intervalo entre $85\text{ ms}$ e $350\text{ ms}$.

### 4.2. Estrutura do Quadro de 9 Bits e Paridade Par
Tanto na transmissão automática quanto na transmissão manual, cada caractere é transmitido em um quadro rígido de 9 bits:
$$\underbrace{b_1 \quad b_2 \quad b_3 \quad b_4 \quad b_5 \quad b_6 \quad b_7 \quad b_8}_{8\text{ bits de dados (caractere ASCII)}} \quad \underbrace{b_9}_{\text{Bit de Paridade Par}}$$

- **Regra de Cálculo da Paridade:**
  - Se a quantidade de bits `1` nos 8 bits de dados for **PAR**: $b_9 = 0$.
  - Se a quantidade de bits `1` nos 8 bits de dados for **ÍMPAR**: $b_9 = 1$.
- **Exemplo de Codificação para o caractere 'A':**
  - `'A'` (ASCII `65` = `01000001`): possui 2 uns (par) $\implies b_9 = 0$.
  - Quadro de 9 bits: `010000010`.
  - Sequência física correspondente: `[0: •] [1: ••] [0: •] [0: •] [0: •] [0: •] [0: •] [1: ••] [P=0: •]`.
- **Exemplo de Codificação para a mensagem "OI":**
  - `'O'` (ASCII `79` = `01001111`): possui 5 uns (ímpar) $\implies b_9 = 1$. Quadro: `010011111`.
  - `'I'` (ASCII `73` = `01001001`): possui 3 uns (ímpar) $\implies b_9 = 1$. Quadro: `010010011`.
  - **Sequência completa transmitida (18 bits):** `010011111010010011`.

### 4.3. As Duas Modalidades de Transmissão

#### A) Transmissão Automática
- O usuário informa a mensagem na interface ou terminal.
- O computador converte a mensagem em bits e adiciona o bit de paridade par para cada byte.
- O software sintetiza os pulsos de áudio (frequência central de $900\text{ Hz}$, decaimento exponencial com $\tau = 7\text{ ms}$, janela nominal de bit de $0.70\text{ s}$).
- O alto-falante reproduz o som, que se propaga pelo ar até o microfone do receptor.

#### B) Transmissão Manual
- O usuário seleciona **Transmissão Manual** na interface ou opção 2 no terminal.
- O computador **NÃO** gera impactos pelo alto-falante.
- O usuário inicia a escuta (`🎙️ INICIAR TRANSMISSÃO MANUAL`).
- O usuário produz os impactos fisicamente:
  - Uma batida na mesa ou palma isolada $\to$ o receptor registra **Bit 0** (`•`).
  - Duas batidas rápidas na mesa ou estalos consecutivos $\to$ o receptor registra **Bit 1** (`••`).
- O usuário aguarda um intervalo de aproximadamente $0.5\text{ s}$ entre cada bit para permitir que a janela temporal feche.
- A transmissão manual é livre: o usuário pode enviar quantos bits desejar.
- A cada 9 bits acumulados, o receptor monta o byte de dados, verifica a paridade par e exibe o caractere decodificado.
- Ao clicar em `⏹️ FINALIZAR TRANSMISSÃO MANUAL`, o receptor consolida os dados e apresenta o diagnóstico final.

### 4.4. Receptor e Detector em Tempo Real
O receptor emprega a classe `DetectorBatidasTempoReal` (`src/metodo1_batidas/receptor.py`), que funciona de forma agnóstica à origem do som (alto-falante ou impactos manuais):
1. Captura contínua do microfone em blocos de 512 amostras a $44.100\text{ Hz}$ (~$11.6\text{ ms}$ por callback).
2. Remove o nível DC do sinal e mede a amplitude de pico instantânea.
3. Máquina de estados:
   - **`IDLE`:** Aguarda o sinal superar o limiar configurado (ajustável de 0.02 a 0.35 ou via calibração adaptativa). Ao detectar o primeiro impacto, registra o instante e transiciona para `WAITING_SECOND_TAP`.
   - **`WAITING_SECOND_TAP`:** Monitora o intervalo decorrido $\Delta t$:
     - Se ocorrer um segundo impacto com $\Delta t \ge 85\text{ ms}$ (debounce para rejeição de eco) e $\Delta t \le 360\text{ ms}$: emite **Bit 1** (`••`), aplica período refratário e retorna a `IDLE`.
     - Se $\Delta t > 360\text{ ms}$ sem um segundo impacto: confirma que foi um impacto isolado, emite **Bit 0** (`•`) e retorna a `IDLE`.
4. Os bits emitidos são enfileirados em quadros de 9 bits, que passam pela validação da paridade par.

---

## 5. Método 2 — Duração do Impacto

No Método 2, a informação binária é representada pela **duração temporal de um único impacto acústico**. O transmissor gera impactos de diferentes extensões no tempo, e o receptor mede a duração do pulso captado pelo microfone.

### 5.1. Codificação dos Bits
- **Bit 0:** Representado por um **impacto acústico curto** ($50\text{ ms}$).
- **Bit 1:** Representado por um **impacto acústico longo** ($160\text{ ms}$).

### 5.2. Parâmetros Centralizados do Método 2
Localizados em [`src/metodo2_duracao/transmissor.py`](src/metodo2_duracao/transmissor.py):

| Parâmetro | Constante | Valor | Finalidade |
| :--- | :--- | :---: | :--- |
| **Duração do Impacto Curto** | `DURACAO_IMPACTO_CURTO` | **$50\text{ ms}$** ($0.050\text{ s}$) | Representa o dígito binário 0. |
| **Duração do Impacto Longo** | `DURACAO_IMPACTO_LONGO` | **$160\text{ ms}$** ($0.160\text{ s}$) | Representa o dígito binário 1. |
| **Limiar de Decisão** | `LIMIAR_DURACAO` | **$105\text{ ms}$** ($0.105\text{ s}$) | Ponto de corte: duração $< 105\text{ ms} \to 0$; $\ge 105\text{ ms} \to 1$. |
| **Intervalo entre Impactos** | `INTERVALO_ENTRE_IMPACTOS` | **$150\text{ ms}$** ($0.150\text{ s}$) | Silêncio para cessar a energia do som anterior e evitar fusão de símbolos. |
| **Frequência do Pulso** | `FREQ_IMPACTO` | **$900.0\text{ Hz}$** | Frequência audível de excelente resposta em alto-falantes e microfones. |
| **Preâmbulo de Sincronismo**| `PADRAO_PREAMBULO` | `[1, 0, 1, 0, 1, 0, 1, 0]` | Padrão binário conhecido de 8 bits enviado antes do pacote. |
| **Silêncio de Guarda** | `SILENCIO_GUARDA` | **$200\text{ ms}$** ($0.200\text{ s}$) | Intervalo de silêncio no início e fim para estabilizar a captura. |

### 5.3. Estrutura do Pacote e CRC-8
O Método 2 organiza os dados em pacotes com controle de integridade:
$$\text{Pacote} = [\underbrace{\text{Comprimento } N}_{1\text{ byte}}] + [\underbrace{\text{Carga Útil (Payload)}}_{N\text{ bytes}}] + [\underbrace{\text{CRC-8}}_{1\text{ byte}}]$$

- **Polinômio Gerador:** $G(x) = x^8 + x^2 + x + 1$ (`0x07` — padrão ATM/SMBus).
- **Exemplo para a mensagem "OI":**
  - Comprimento: $N = 2$ (`0x02`).
  - Dados: `'O'` (`0x4F`), `'I'` (`0x49`).
  - CRC-8 calculado sobre `[0x02, 0x4F, 0x49]` resulta em `0xB6`.
  - Pacote: `[0x02, 0x4F, 0x49, 0xB6]` ($4\text{ bytes} = 32\text{ bits}$).
  - Adicionando o preâmbulo (`8 bits`), o áudio total contém $40\text{ bits}$.

### 5.4. Transmissão
1. O texto digitado é convertido em bytes.
2. O pacote com cabeçalho de comprimento e CRC-8 é montado.
3. Os bits são convertidos em impactos acústicos:
   - Para bit `0`: emite pulso de $50\text{ ms}$.
   - Para bit `1`: emite pulso de $160\text{ ms}$.
   - Entre cada impacto: insere silêncio de $150\text{ ms}$.
4. O sinal completo é reproduzido pelo alto-falante.

### 5.5. Recepção e Medição de Duração
1. **Captura do Sinal:** O receptor grava o áudio do microfone pelo tempo configurado (ex.: $10\text{ s}$ a $12\text{ s}$).
2. **Envelope de Energia:** Remove o offset DC, retifica a onda e aplica média móvel suave ($12\text{ ms}$) para extrair o contorno de energia do sinal.
3. **Limiar Adaptativo de Amplitude:** Mede o ruído de fundo da sala e define um limiar dinâmico que ignora o ruído de fundo e detecta a presença de som.
4. **Segmentação e Debounce:** Identifica o início e o fim de cada impacto contíguo, unificando pequenas falhas ($< 35\text{ ms}$) causadas por reflexões da sala e descartando estalos insignificantes ($< 20\text{ ms}$).
5. **Medição e Classificação:**
   $$\text{duração} = \frac{\text{amostra}_{\text{fim}} - \text{amostra}_{\text{início}}}{F_s}$$
   - Se $\text{duração} < 105\text{ ms} \implies$ **Bit 0 (Curto)**.
   - Se $\text{duração} \ge 105\text{ ms} \implies$ **Bit 1 (Longo)**.
6. **Sincronização:** Localiza o preâmbulo `10101010` na sequência de bits e extrai os bits subsequentes do pacote.
7. **Verificação de Integridade:** Lê o byte de comprimento, extrai o CRC-8 recebido, recalcula o CRC-8 e compara. Se idênticos, confirma **`SUCESSO — dados íntegros`** e reconstrói a mensagem.

---

## 6. Comparação dos Métodos

| Característica | Método 1 — Quantidade de Impactos | Método 2 — Duração do Impacto |
| :--- | :--- | :--- |
| **Característica Utilizada** | **Quantidade** de impactos acústicos por janela. | **Duração temporal** de cada impacto acústico individual. |
| **Formas de Transmissão** | **Automática** (alto-falante) e **Manual** (palmas, batidas na mesa, estalos, caneta). | **Automática** (alto-falante emitindo pulsos de 50 ms e 160 ms). |
| **Representação do Bit 0** | 1 impacto sonoro isolado (`•`). | Impacto acústico curto ($50\text{ ms}$). |
| **Representação do Bit 1** | 2 impactos sonoros consecutivos rápidos (`••`, $85\text{ ms}$ a $350\text{ ms}$ entre eles). | Impacto acústico longo ($160\text{ ms}$). |
| **Verificação de Erro** | **Bit de Paridade Par** (1 bit por caractere em quadros de 9 bits). | **CRC-8** com polinômio `0x07` (1 byte por pacote). |
| **Estrutura de Enlace** | Quadros rígidos de **9 bits** (8 dados + 1 paridade). | Pacote delimitado: `[1B Tamanho] + [N Bytes] + [1B CRC-8]`. |
| **Sincronização** | Cadência temporal por janela de bit ($\sim 0.70\text{ s}$). | **Preâmbulo de 8 bits** (`10101010`). |
| **Taxa Teórica Aproximada** | $\approx \mathbf{1.43\text{ bps}}$ ($1 / 0.70\text{ s}$). | $\approx \mathbf{3.92\text{ bps}}$ ($1 / 0.255\text{ s}$ médio). |
| **Tempo para "OI"** | $\sim 13\text{ segundos}$ (18 bits). | $\sim 10\text{ segundos}$ (40 bits com preâmbulo). |
| **Principal Desafio Físico** | Separar corretamente dois impactos rápidos sem fundi-los por reverberação. | Medir com precisão a duração do som sem que a cauda de eco da sala confunda o limiar. |

---

## 7. Taxa de Transmissão

### 7.1. Taxa Teórica
- **Método 1:**
  $$R_{\text{teor, M1}} = \frac{1}{T_{\text{bit}}} = \frac{1}{0.70\text{ s}} \approx 1.43\text{ bps}$$
- **Método 2:**
  $$T_{\text{símbolo, médio}} = \frac{T_{\text{curto}} + T_{\text{longo}}}{2} + T_{\text{intervalo}} = \frac{0.050 + 0.160}{2} + 0.150 = 0.255\text{ s}$$
  $$R_{\text{teor, M2}} = \frac{1}{0.255\text{ s}} \approx 3.92\text{ bps}$$

### 7.2. Taxa Prática
A taxa prática considera a transmissão real de ponta a ponta, incluindo cabeçalhos, preâmbulos e silêncios de guarda:
- Para a mensagem `"OI"` (16 bits de dados):
  - No Método 1: 18 bits em $\approx 13\text{ segundos} \implies \approx 1.23\text{ bps}$ práticos.
  - No Método 2: 40 bits de áudio em $\approx 10.6\text{ segundos} \implies \approx 1.51\text{ bps}$ de dados úteis líquidos.

---

## 8. Detecção e Teste de Erro

Para fins didáticos e demonstração em vídeo, o software inclui a capacidade de injetar propositalmente um erro de bit (inversão determinística de 0 para 1 ou de 1 para 0) antes da emissão:

1. **Método 1 (Paridade):**
   - Transmissor inverte 1 bit do quadro (ou o operador realiza uma batida a mais/a menos no modo manual).
   - Receptor recalcula a paridade par: a contagem de uns passa de par para ímpar (ou vice-versa).
   - O receptor detecta a divergência e exibe em vermelho: **`✗ FALHA DE TRANSMISSÃO — Paridade Inválida no Quadro X`**.
2. **Método 2 (CRC-8):**
   - Transmissor inverte 1 bit do pacote binário.
   - Receptor recalcula a divisão polinomial: o resto obtido difere do byte de CRC-8 recebido.
   - O receptor acusa imediatamente: **`✗ FALHA DE TRANSMISSÃO — dados corrompidos`**.

---

## 9. Testes e Validação

### 9.1. Suíte de Testes Automatizados (30 Aprovados — 100%)
Executados via `python -m unittest discover tests -v`:

1. `test_01_calculo_paridade_casos_oficiais`: Validação matemática da paridade par com os exemplos da especificação.
2. `test_02_validacao_quadro_correto_e_corrompido`: Aprovação de quadros corretos e reprovação de corrompidos.
3. `test_03_injecao_proposital_erro_em_dados`: Inversão de bit acusando falha de paridade.
4. `test_04_transmissao_acustica_sem_ruido`: Síntese e decodificação do Método 1 sem ruído.
5. `test_05_transmissao_acustica_com_ruido_ambiente`: Tolerância do Método 1 a ruído aditivo.
6. `test_06_fluxo_completo_mensagem_curta`: Validação de quadros de 9 bits para "OI".
7. `test_07_transmissao_automatica_acustica_oi`: Síntese de 18 bits, detecção e validação de paridade de "OI".
8. `test_08_entrada_manual_um_impacto_vira_zero`: Validação de 1 impacto físico isolado decodificando como bit 0 (`•`).
9. `test_09_entrada_manual_dois_impactos_rapidos_vira_um`: Validação de 2 impactos rápidos consecutivos decodificando como bit 1 (`••`).
10. `test_10_entrada_manual_sequencia_fisica_caractere_a`: Simulação de batidas físicas manuais completas para o caractere `'A'` com paridade par.
11. `test_11_entrada_manual_deteccao_erro_paridade`: Detecção de erro em caso de batida manual incorreta violando a paridade par.
12. `test_12_detector_tempo_real_estrutura_e_callbacks`: Validação estrutural do detector contínuo do microfone.
13. `test_01_crc8_vetor_padrao_internacional`: Verificação do CRC-8 com o vetor internacional `'123456789'` $\to$ `0xF4`.
14. `test_02_pacote_metodo2_integro_e_corrompido`: Montagem e desmontagem de pacotes íntegros e corrompidos.
15. `test_03_injecao_proposital_de_erro_crc8`: Inversão de bit acusando falha no CRC-8.
16. `test_04_classificacao_impacto_curto_e_longo`: Medição de pulsos individuais de 50 ms (0) e 160 ms (1).
17. `test_05_transmissao_acustica_duracao_sem_ruido`: Modulação por duração e decodificação sem ruído.
18. `test_06_transmissao_acustica_duracao_com_ruido`: Modulação por duração com ruído gaussiano aditivo.
19. `test_07_calculo_taxa_bps`: Verificação analítica das taxas teórica e prática.
20. `test_08_demodulacao_autonoma_sem_tamanho_previo`: Recepção cega com preâmbulo e silêncio antes/depois.
21. `test_09_mensagem_maior`: Transmissão completa da mensagem "REDE" no Método 2.
22. `test_req_01_transmissao_sem_ruido`: Validação formal do Requisito 1.
23. `test_req_02_transmissao_com_ruido`: Validação formal do Requisito 2.
24. `test_req_03_mensagem_curta`: Validação formal do Requisito 3 (mensagem curta `'A'`).
25. `test_req_04_mensagem_maior`: Validação formal do Requisito 4 (mensagem maior).
26. `test_req_05_erro_proposital_em_um_bit`: Validação formal do Requisito 5 (injeção de erro).
27. `test_req_06_quadro_correto`: Validação formal do Requisito 6 (quadro íntegro aprovado).
28. `test_req_07_quadro_corrompido`: Validação formal do Requisito 7 (quadro corrompido reprovado).
29. `test_req_08_calculo_de_paridade`: Validação formal do Requisito 8 (regra de paridade).
30. `test_req_09_deteccao_erro_metodo2_crc8`: Validação formal do Requisito 9 (algoritmo CRC-8).

---

## 10. Autoria Individual

Projeto desenvolvido individualmente por **Lucas Santana da Silva** (R.A.: 2208504), aluno do curso de Bacharelado em Ciência da Computação, na disciplina de Redes de Computadores.

---

## 11. Declaração do Uso de Inteligência Artificial

Em conformidade com a ética acadêmica e os princípios de transparência científica:

Ferramentas de **Inteligência Artificial Generativa** foram utilizadas exclusivamente como instrumento de apoio durante o desenvolvimento do trabalho, atuando em:
- Auxílio na identificação e correção de bugs no processamento de sinal;
- Sugestões para simplificação da camada física acústica e estruturação dos módulos;
- Explicação e detalhamento de conceitos teóricos de redes e sinais;
- Revisão da documentação técnica e organização dos materiais explicativos.

O autor **Lucas Santana da Silva** é integralmente responsável pelo projeto final, pela implementação, pelos testes realizados, pela compreensão aprofundada de cada parte do código e pela gravação da apresentação em vídeo.

---

## 12. Como Executar

### Pré-requisitos
- Python 3.10 ou superior.
- Placa de som com microfone e alto-falante configurados.

### Clonagem
```bash
git clone https://github.com/Santana92/RedesComputadores
```

### Instalação
```bash
cd Atividade1
pip install -r requirements.txt
```

### Executar a Interface Gráfica
```bash
python main.py
```

### Executar no Terminal (CLI)
```bash
python main.py --cli
```

### Executar os Testes Automatizados
```bash
python -m unittest discover tests -v
```

---

## 13. Guia do Teste Físico (Bancada)

Para realizar a demonstração física real:
1. **Configuração dos Dispositivos:** Garanta que o áudio do computador transmissor seja emitido pelo **alto-falante** (e não por fones de ouvido isolados), e que o computador receptor esteja utilizando o **microfone** para captar o som do ar ambiente.

2. **Método 1 — Transmissão Automática (Alto-falante):**
   - No Receptor: clique em `🎙️ INICIAR ESCUTA DO MICROFONE`.
   - No Transmissor: selecione `Transmissão Automática`, digite `OI` e clique em `🔊 TRANSMITIR BATIDAS PELO ALTO-FALANTE`.
   - O receptor detectará os impactos emitidos pelos alto-falantes, validará a paridade dos quadros e exibirá `OI`.

3. **Método 1 — Transmissão Manual (Palmas / Batidas na Mesa):**
   - No painel do Método 1: selecione `Transmissão Manual`.
   - Clique em `🎙️ INICIAR TRANSMISSÃO MANUAL`. O microfone começa a escutar e o computador **NÃO** emite som.
   - Diante do microfone, produza os impactos físicos:
     - 1 batida na mesa ou palma $\to$ o receptor exibe `• -> Bit 0`.
     - 2 batidas rápidas na mesa ou estalos $\to$ o receptor exibe `•• -> Bit 1`.
   - Aguarde cerca de $0.5\text{ s}$ entre cada bit.
   - Para transmitir o caractere `'A'` (ASCII 65 = `01000001`, paridade par = `0`), siga a sequência:
     `•` (0), `••` (1), `•` (0), `•` (0), `•` (0), `•` (0), `•` (0), `••` (1), `•` (Paridade 0).
   - O receptor valida a paridade par e exibe o caractere `'A'` imediatamente.
   - Clique em `⏹️ FINALIZAR TRANSMISSÃO MANUAL`.

4. **Método 2 — Duração do Impacto (Alto-falante):**
   - No Receptor: ajuste o tempo de escuta para $12\text{ s}$ e clique em `🎙️ CAPTAR ÁUDIO PELO MICROFONE`.
   - No Transmissor: digite `OI` e clique em `🔊 TRANSMITIR VIA DURAÇÃO (ALTO-FALANTE)`.
   - O receptor medirá a duração de cada impacto ($50\text{ ms}$ vs $160\text{ ms}$), detectará o preâmbulo `10101010`, conferirá o CRC-8 e reconstruirá `OI`.

5. **Demonstração de Erro:**
   - No Método 1: marque `Injetar Erro` (inverte 1 bit) e transmita $\to$ o receptor acusará `✗ FALHA DE TRANSMISSÃO — Paridade Inválida`.
   - No Método 2: marque `Injetar Erro` (inverte bit no CRC) e transmita $\to$ o receptor acusará `✗ FALHA DE TRANSMISSÃO — CRC-8 Divergente`.

---

## Licença

Distribuído sob a licença **MIT Open Source** (consulte [LICENSE](LICENSE)).
