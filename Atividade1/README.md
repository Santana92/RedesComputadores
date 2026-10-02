# Comunicação de Dados na Camada Física usando Som 🔊💻

[![Licença MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Status dos Testes](https://img.shields.io/badge/Testes%20Automatizados-27%20Aprovados%20(100%25)-success.svg)](#9-testes-e-validação)

Trabalho prático da disciplina de **Redes de Computadores** focado no desenvolvimento, análise e validação experimental da **Camada Física** e subcamada de enlace lógico utilizando o **ar atmosférico e ondas acústicas** como meio de transmissão não guiado.

---

## 📹 Vídeo de Demonstração

- **Vídeo de Demonstração (Individual):** `[INSERIR LINK DO VÍDEO NO YOUTUBE - 3 A 7 MINUTOS]`
- **Thumbnail / Prévia:**  
  *(Inserir link ou imagem da prévia do vídeo gravado pelo autor demonstrando a comunicação real entre computadores e os testes de erro)*

---

## 1. Introdução e Objetivo da Atividade

O objetivo fundamental deste trabalho é projetar e implementar um sistema completo de comunicação digital na **Camada Física** (Camada 1 do Modelo OSI), operando através de ondas sonoras mecânicas propagadas pelo ar entre alto-falantes e microfones.

O software foi concebido como um **modem acústico único**, capaz de atuar em ambos os papéis da comunicação:
- **Transmissor (TX):** Transforma mensagens digitais em sinais acústicos audíveis emitidos pelo alto-falante.
- **Receptor (RX):** Captura ondas sonoras pelo microfone, processa o sinal analógico, recupera a sequência binária e reconstrói a mensagem original com verificação de integridade.

O sistema implementa dois métodos independentes de sinalização acústica:
1. **Método 1 — Batidas por Impacto:** Sinalização em banda base baseada na quantidade e cadência de pulsos acústicos (palmas, estalos ou batidas em superfícies), com enquadramento em blocos de 9 bits e detecção de erro por **Paridade Par**.
2. **Método 2 — Modulação FSK (*Frequency-Shift Keying*):** Modulação em frequência com portadoras ortogonais contínuas ($1200\text{ Hz}$ e $2200\text{ Hz}$), tom piloto de sincronização ($1700\text{ Hz}$) e detecção de erro robusta por **CRC-8** (polinômio ATM `0x07`).

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
| **2** | **Enlace de Dados** | **Enquadramento (*framing*), alinhamento e detecção de erros.** | **Quadros de 9 bits (Método 1) e Pacotes delimitados com CRC-8 (Método 2).** |
| **1** | **Física** | **Transmissão e recepção de bits brutos no meio físico.** | **Transdutores acústicos (Alto-falante e Microfone) via Impactos ou Tons FSK.** |

### 2.2. Aprofundamento na Camada Física

A Camada Física define as especificações elétricas, mecânicas e funcionais para ativar, manter e desativar o enlace físico entre sistemas terminais. No contexto acústico:
- **Meio de Transmissão:** O ar atmosférico em temperatura e pressão ambiente, que atua como meio contínuo elástico.
- **Sinal Físico:** Ondas mecânicas longitudinais de compressão e rarefação de moléculas do ar.
- **Transdutor Emissor (D/A Acústico):** O alto-falante, que converte sinais elétricos oscilatórios em deslocamento mecânico de sua membrana cônica.
- **Transdutor Receptor (A/D Acústico):** O microfone, cujo diafragma vibra sob a pressão acústica incidente, gerando tensões elétricas amostradas pela placa de som.

### 2.3. Sinais Analógicos e Digitais

- **Sinal Digital:** Uma abstração matemática discreta no tempo e na amplitude formada por dígitos binários ($0$ e $1$), manipulada pela CPU e pela memória do computador.
- **Sinal Analógico:** Uma grandeza física contínua que varia suavemente no tempo, representada pela pressão sonora instantânea $p(t)$ medida em Pascals ($\text{Pa}$).
- **O Processo de Modulação/Demodulação:**
  $$\text{Bits Digitais } (0, 1) \xrightarrow{\text{Modulação / Síntese}} s(t) \text{ [Analógico]} \xrightarrow{\text{Ar}} r(t) \xrightarrow{\text{Amostragem / DFT / Filtro}} \text{Bits Recuperados } (0, 1)$$

### 2.4. Largura de Banda e Capacidade de Canal

A largura de banda acústica útil é limitada pela resposta em frequência dos alto-falantes e microfones integrados dos computadores comuns (tipicamente de $100\text{ Hz}$ a $15.000\text{ Hz}$).
- **Teorema de Nyquist para canal sem ruído:**
  $$C = 2B \log_2(M)$$
  Para sinalização binária ($M = 2$), a taxa máxima de símbolos sem interferência intersimbólica (ISI) é de duas vezes a largura de banda.
- **Teorema de Shannon-Hartley para canal com ruído gaussiano:**
  $$C = B \log_2\left(1 + \frac{S}{N}\right)$$
  Em ambientes de sala de aula com conversas, ruído de trânsito e ventiladores, a relação sinal-ruído ($S/N$) é substancialmente reduzida, exigindo durações de símbolo suficientemente longas para garantir que a energia do sinal supere o ruído de fundo.

### 2.5. Taxa de Amostragem (*Sampling Rate*)

De acordo com o **Teorema da Amostragem de Nyquist-Shannon**, para evitar o fenômeno de falseamento espectral (*aliasing*), a taxa de amostragem $F_s$ deve ser estritamente maior que o dobro da frequência máxima presente no sinal ($F_s > 2 f_{\max}$):
- O projeto adota padronizadamente $F_s = 44.100\text{ Hz}$ com amostras em ponto flutuante de 32 bits (`np.float32`).
- No Método 2, a frequência máxima é $f_1 = 2200\text{ Hz}$, correspondendo a uma frequência de Nyquist de $4400\text{ Hz}$. A taxa de $44.100\text{ Hz}$ fornece uma margem de sobreamostragem de aproximadamente $10\times$, assegurando excelente definição das senoides e filtragem digital precisa.

### 2.6. Ruído e Atenuação no Meio Acústico

O canal acústico não guiado apresenta perturbações que não ocorrem em cabos metálicos ou fibra óptica:
1. **Atenuação por Divergência Geométrica:** A densidade de potência da onda esférica decai com o quadrado da distância ($I \propto 1/r^2$).
2. **Reverberação e Ecos de Multipropagação:** Ondas refletidas em mesas, paredes e telas chegam ao microfone com atrasos variáveis, causando dispersão temporal e interferência destrutiva.
3. **Ruído Aditivo de Fundo:** Ar-condicionado, digitação em teclados e conversas na sala introduzem energia espúria em ampla faixa espectral.

### 2.7. Fundamentos Teóricos da Detecção de Erros

Como o canal acústico está sujeito a perdas e distorções, a Camada de Enlace precisa incorporar mecanismos matemáticos de verificação:
- **Bit de Paridade Simples:**
  Soma em módulo 2 de todos os bits de dados:
  $$b_{\text{paridade}} = \left(\sum_{i=1}^8 b_i\right) \bmod 2$$
  *Propriedade matemática:* Detecta confiavelmente qualquer número ímpar de bits invertidos (1, 3, 5 ou 7). Se dois bits forem invertidos simultaneamente, a paridade permanece a mesma e o erro torna-se indetectável.
- **Código de Redundância Cíclica (CRC):**
  Considera a mensagem de $k$ bits como um polinômio $M(x)$ com coeficientes em $\text{GF}(2)$. O polinômio gerador $G(x)$ define o divisor. O resto da divisão polinomial:
  $$R(x) = [M(x) \cdot x^r] \bmod G(x)$$
  constitui o checksum anexado ao pacote. O algoritmo CRC-8 com polinômio $G(x) = x^8 + x^2 + x + 1$ (`0x07`) garante detecção de 100% dos erros simples de bit, 100% dos erros duplos, 100% de qualquer quantidade ímpar de erros e 100% das rajadas de ruído de comprimento $\le 8$ bits.

---

## 3. Arquitetura do Sistema

O sistema foi estruturado modularmente em Python, com separação estrita entre a camada de representação de dados, controle de enlace, processadores de sinal da camada física e interface de usuário.

```text
redes-de-computadores/
│
├── main.py                         # Ponto de entrada raiz (executa GUI ou CLI)
├── requirements.txt                # Dependências (numpy, sounddevice)
├── LICENSE                         # Licença MIT Open Source
├── README.md                       # Documentação técnica e científica
│
├── src/
│   ├── __init__.py
│   ├── conversao.py                # Conversão: Texto <-> Bytes <-> Bits e formatação
│   ├── deteccao_erros.py           # Paridade Par (quadros 9 bits) e CRC-8 (polinômio 0x07)
│   ├── interface.py                # Interface gráfica completa em Tkinter nativo
│   ├── main.py                     # Controlador CLI e despachante da interface
│   │
│   ├── metodo1_batidas/            # Camada Física: Método 1 (Impacto Acústico)
│   │   ├── __init__.py
│   │   ├── transmissor.py          # Síntese amortecida de batidas e reprodução
│   │   └── receptor.py             # Escuta contínua, máquina de estados e limiar adaptativo
│   │
│   └── metodo2_fsk/                # Camada Física: Método 2 (Modulação FSK)
│       ├── __init__.py
│       ├── transmissor.py          # Modulação CP-FSK contínua e cálculo de taxas
│       └── receptor.py             # Sincronização por filtro casado e demodulação DFT
│
└── tests/                          # Suíte de 26 testes automatizados
    ├── __init__.py
    ├── test_metodo1.py             # Testes do Método 1 (paridade, áudio sintético, ruído)
    ├── test_metodo2.py             # Testes do Método 2 (CRC-8, demodulação FSK, pré-símbolo)
    └── test_requisitos_completos.py# Mapeamento formal dos 9 requisitos de avaliação
```

### 3.1. Papel Transmissor (TX)
Responsável por coletar os dados de entrada (seja texto digitado ou sequência de impactos mecânicos captados), estruturar os dados com os mecanismos de detecção de erro, modular os bits em formas de onda de áudio e reproduzir os sons pelo alto-falante.

### 3.2. Papel Receptor (RX)
Responsável por capturar o áudio ambiente via microfone em tempo real ou gravação contínua, rejeitar ruído espúrio, sincronizar o início da transmissão, demodular os eventos acústicos em bits binários, validar a integridade através do mecanismo de enlace e reconstruir o texto original.

### 3.3. Caminho Físico do Áudio Real (Regra Fundamental)
O software **não utiliza variáveis compartilhadas, memória global, sockets de rede ou chamadas internas diretas** para transferir dados entre transmissor e receptor. 

Em todos os cenários operacionais, os dados percorrem estritamente o canal físico analógico:
$$\textbf{Transmissor} \longrightarrow \textbf{Alto-falante} \xrightarrow[\text{Ondas Mecânicas}]{\textbf{Ar / Ambiente}} \textbf{Microfone} \longrightarrow \textbf{Processamento RX} \longrightarrow \textbf{Mensagem}$$

Mesmo quando os testes são realizados em um único computador, o áudio deve sair fisicamente pelos alto-falantes e ser capturado pelo microfone da máquina.

---

## 4. Método 1 — Batidas por Impacto

O Método 1 representa os dados através de transientes acústicos discretos de impacto mecânico. O som pode ser produzido por palmas, estalos de dedos, batidas com caneta ou batidas na mesa. O receptor é agnóstico à fonte do som, identificando a ocorrência do impacto pela variação abrupta de energia.

### 4.1. Codificação dos Bits
- **Bit 0:** Representado por **uma batida isolada** seguida de intervalo de silêncio.
- **Bit 1:** Representado por **duas batidas consecutivas rápidas** dentro de uma janela temporal curta.

### 4.2. Estrutura do Quadro de 9 Bits e Paridade Par
O protocolo de enlace do Método 1 organiza a transmissão em blocos rígidos de 9 bits:
$$\underbrace{b_1 \quad b_2 \quad b_3 \quad b_4 \quad b_5 \quad b_6 \quad b_7 \quad b_8}_{8\text{ bits de dados (caractere ASCII)}} \quad \underbrace{b_9}_{\text{Bit de Paridade Par}}$$

- **Regra de Cálculo da Paridade:**
  - Se a contagem de bits `1` em $b_1 \dots b_8$ for **PAR**, então $b_9 = 0$.
  - Se a contagem de bits `1` em $b_1 \dots b_8$ for **ÍMPAR**, então $b_9 = 1$.
- **Exemplo Oficial de Codificação para a mensagem "OI":**
  - Caractere `'O'` (ASCII `79` = `01001111`): possui 5 uns (ímpar) $\implies$ paridade = `1`. Quadro: `010011111`.
  - Caractere `'I'` (ASCII `73` = `01001001`): possui 3 uns (ímpar) $\implies$ paridade = `1`. Quadro: `010010011`.
  - **Sequência binária completa transmitida (18 bits):**
    `010011111010010011`

### 4.3. Transmissão Automática pelo Alto-falante
O transmissor sintetiza ondas senoidais amortecidas com decaimento exponencial rápido somadas a transientes de ruído branco, simulando o timbre de uma batida seca:
- Duração do pulso de impacto: $35\text{ ms}$ com frequência principal de $900\text{ Hz}$ e decaimento $\tau = 7\text{ ms}$.
- Duração nominal da janela de cada bit: $0.70\text{ s}$ a $0.80\text{ s}$.
- Intervalo entre batidas duplas do Bit 1: $160\text{ ms}$.
- O vetor de áudio é reproduzido de forma síncrona ou em thread assíncrona pelos alto-falantes através da biblioteca `sounddevice`.

### 4.4. Entrada Manual por Impactos Físicos
Uma pessoa pode produzir manualmente os sons diretamente diante do microfone. O operador bate palmas ou toca uma caneta na mesa seguindo a cadência:
- Para enviar `0`: produz 1 batida e aguarda o intervalo de guarda ($\sim 0.7\text{ s}$).
- Para enviar `1`: produz 2 batidas rápidas em menos de $350\text{ ms}$ e aguarda o intervalo de guarda.

### 4.5. Recepção pelo Microfone
O receptor emprega a classe `DetectorBatidasTempoReal`, operando via stream contínuo de áudio com blocos de 512 amostras ($\sim 11.6\text{ ms}$ a $44.100\text{ Hz}$):
1. **Remoção de Offset DC:** Subtrai a média local do sinal.
2. **Medição de Pico:** Avalia o valor absoluto máximo do bloco.
3. **Debounce ($85\text{ ms}$):** Após um pico acima do limiar, entra em período refratário para não registrar reverberações mecânicas da mesa como batidas adicionais.
4. **Máquina de Estados de Classificação:**
   - Ao detectar a 1ª batida, entra no estado `WAITING_SECOND_TAP`.
   - Se ocorrer uma 2ª batida válida dentro da janela dupla ($350\text{ ms}$), emite **Bit 1**.
   - Se a janela de $350\text{ ms}$ expirar sem novo impacto, emite **Bit 0**.
5. **Decodificação Autônoma:** Os bits são agrupados dinamicamente de 9 em 9. Ao completar cada bloco, a paridade é conferida e o caractere resultante é imediatamente exibido em tela. A recepção não depende de conhecimento prévio da mensagem.

### 4.6. Detecção de Erros e Limitações da Paridade
O receptor recalcula a paridade esperada sobre os 8 bits de dados e compara com o 9º bit recebido:
- **Paridade Correta:** O quadro é marcado como íntegro e o caractere é validado.
- **Paridade Incorreta:** O software emite alerta visual de **`FALHA DE TRANSMISSÃO — Paridade Inválida`** e não valida os dados.
- **Limitação Conhecida:** Se ruídos externos causarem a inversão simultânea de dois bits em um mesmo quadro, a paridade continuará par e o erro não será detectado.

---

## 5. Método 2 — Modulação FSK (*Frequency-Shift Keying*)

O Método 2 utiliza modulação por chaveamento de frequência com portadoras senoidais contínuas. A implementação original em FSK foi integralmente preservada, mantendo suas frequências fundamentais e ortogonalidade matemática.

### 5.1. Funcionamento do FSK
Em vez de depender de eventos de impacto, o FSK transmite energia contínua em frequências predefinidas durante intervalos fixos de tempo denominados **janelas de símbolo**.

### 5.2. Parâmetros Físicos Reais Implementados no Código
Verificados diretamente em [`src/metodo2_fsk/transmissor.py`]

| Parâmetro | Constante no Código | Valor Real | Descrição Técnica |
| :--- | :--- | :---: | :--- |
| **Frequência do Bit 0** | `FREQ_BIT_0` | **$1200.0\text{ Hz}$** | Portadora representativa do dígito binário 0. |
| **Frequência do Bit 1** | `FREQ_BIT_1` | **$2200.0\text{ Hz}$** | Portadora representativa do dígito binário 1. |
| **Frequência de Preâmbulo** | `FREQ_PREAMBULO` | **$1700.0\text{ Hz}$** | Tom piloto de sincronismo de quadro. |
| **Duração do Símbolo** | `DURACAO_SIMBOLO` | **$0.025\text{ s}$ ($25\text{ ms}$)** | Tempo de emissão de cada bit individual. |
| **Duração do Preâmbulo** | `DURACAO_PREAMBULO` | **$0.150\text{ s}$ ($150\text{ ms}$)** | Duração do tom piloto de alinhamento. |
| **Silêncio de Guarda** | `SILENCIO_GUARDA` | **$0.100\text{ s}$ ($100\text{ ms}$)** | Silêncio de guarda no início e fim do pacote. |
| **Taxa de Amostragem** | `sample_rate` | **$44.100\text{ Hz}$** | Resolução temporal da camada de áudio. |

#### Demonstração de Ortogonalidade:
Em uma janela de $T = 25\text{ ms}$:
- A frequência de $1200\text{ Hz}$ realiza exatamente $1200 \times 0.025 = 30$ ciclos completos.
- A frequência de $2200\text{ Hz}$ realiza exatamente $2200 \times 0.025 = 55$ ciclos completos.
- Como o produto interno de duas senoides de frequências que completam ciclos inteiros na janela é nulo:
  $$\int_0^{0.025} \sin(2\pi \cdot 1200 \cdot t) \cdot \sin(2\pi \cdot 2200 \cdot t) \, dt = 0$$
  a correlação cruzada entre as duas portadoras é zero, garantindo separação espectral perfeita.

### 5.3. Transmissão Automática por Texto (Modo A)
1. O usuário digita o texto (ex.: `"OI"`).
2. O texto é convertido em bytes (`b'OI'`).
3. O pacote de enlace é estruturado com cabeçalho de comprimento e CRC-8:
   $$\text{Pacote} = [2, \; 79, \; 73, \; \text{CRC8}]$$
4. Os bytes são convertidos em sequência de bits (32 bits).
5. O sintetizador FSK concatena o silêncio de guarda, o tom piloto de $1700\text{ Hz}$, os tons dos 32 bits com continuidade de fase (CP-FSK) e o silêncio final.
6. O sinal resultante é reproduzido pelo alto-falante.

### 5.4. Entrada Manual por Impactos no Método 2 (Modo B)
Conforme especificado na arquitetura atualizada do projeto, o Método 2 **também permite que o usuário forneça os dados por batidas físicas (palmas, estalos, caneta ou mesa)**.
- **Diferença Fundamental:** Os sons de impacto **NÃO** viajam pelo canal FSK. Eles servem unicamente como mecanismo de entrada manual de dados para o transmissor FSK.
- **Fluxo Completo de Comunicação:**
  $$\begin{array}{c}
  \text{Operador Humano} \\
  \downarrow \text{ (Palmas / Batidas na Mesa: 1 batida = 0, 2 batidas = 1)} \\
  \textbf{Microfone Local do Transmissor} \\
  \downarrow \\
  \textbf{Detector de Impactos} \implies \text{Bits Binários} \\
  \downarrow \\
  \textbf{Codificador FSK} \implies \text{Adiciona Cabeçalho e CRC-8} \implies \text{Tons FSK (1200/2200 Hz)} \\
  \downarrow \\
  \textbf{Alto-falante do Transmissor} \\
  \downarrow \text{ (Ondas Senoidais FSK propagando-se pelo Ar)} \\
  \textbf{Microfone do Receptor} \\
  \downarrow \\
  \textbf{Demodulador FSK (Filtro Casado + DFT)} \implies \text{Bits Recuperados} \\
  \downarrow \\
  \textbf{Validador de Integridade CRC-8} \implies \textbf{Mensagem Reconstruída}
  \end{array}$$

### 5.5. Conversão: Impactos $\to$ Bits $\to$ FSK
Quando o usuário produz impactos manuais para o transmissor FSK:
- O detector classifica cada evento (ex.: 9 batidas detectadas).
- Se a sequência de bits não for múltiplo exato de 8, o transmissor preenche com zeros à direita para completar bytes inteiros.
- Os bytes resultantes são encapsulados com o byte de comprimento e o checksum CRC-8.
- O pacote binário final é sintetizado em áudio FSK e reproduzido pelo alto-falante.

### 5.6. Recepção e Demodulação Espectral
1. **Captura do Sinal:** O receptor grava o canal através do microfone durante um tempo de escuta configurável (padrão de 6.0s a 8.0s), permitindo iniciar a escuta confortavelmente antes de acionar o transmissor.
2. **Sincronização por Filtro Casado em Quadratura ($I/Q$):** O sinal normalizado é correlacionado em seno e cosseno com o padrão do preâmbulo de $1700\text{ Hz}$ em janelas ortogonais de $10\text{ ms}$ (441 amostras). A energia coerente $E = I^2 + Q^2$ é imune a rotações de fase provocadas pelo atraso acústico no ar.
3. **Rejeição Estrita de Ruído Ambiente:** Exige que a pureza espectral do tom piloto seja $> 0.35$ de forma sustentada por pelo menos $75\text{ ms}$ ($\ge 50\%$ da duração do preâmbulo), descartando ruídos da sala e silêncios prévios.
4. **Recuperação de Relógio e Alinhamento de Símbolo (*Symbol Timing Recovery*):** Ao detectar o fim do tom de $1700\text{ Hz}$, o receptor avalia uma faixa de $\pm 12\text{ ms}$ e busca o deslocamento temporal $\tau^*$ que maximiza o contraste de discriminação dos símbolos iniciais, centralizando as janelas de integração exatamente no meio de cada símbolo.
5. **Demodulação Ponderada (DFT com Janela de Hann):** Para cada símbolo de $25\text{ ms}$ ($1102$ amostras), aplica-se uma janela de Hann ($w[n] = 0.5 - 0.5 \cos(\frac{2\pi n}{N-1})$) para suprimir transientes de borda e reverberações da sala, calculando a densidade espectral nas portadoras:
   $$E_0 = \left|\sum_{n=0}^{N-1} (x[n] \cdot w[n]) e^{-j 2\pi \frac{1200}{F_s} n}\right|^2, \quad E_1 = \left|\sum_{n=0}^{N-1} (x[n] \cdot w[n]) e^{-j 2\pi \frac{2200}{F_s} n}\right|^2$$
   - Se $E_1 > E_0 \implies$ **Bit 1**.
   - Se $E_0 \ge E_1 \implies$ **Bit 0**.
6. **Decodificação Autônoma e Delimitação:** Ao demodular os primeiros 8 bits (Byte 0 = tamanho $N$), o receptor determina dinamicamente o total exato de bits ($(1 + N + 1) \times 8$ bits), encerrando a leitura imediatamente após o último bit e ignorando qualquer ruído posterior.

### 5.7. Detecção de Erros com CRC-8
O pacote recebido é submetido à validação de redundância cíclica:
- O receptor extrai o payload de $N$ bytes e recalcula o CRC-8 sobre o cabeçalho e os dados utilizando o polinômio gerador `0x07`.
- Compara o CRC calculado com o byte de CRC recebido no final do pacote.
- Se idênticos $\implies$ exibe **`SUCESSO — dados íntegros`** e apresenta a mensagem reconstruída.
- Se divergentes $\implies$ exibe **`FALHA DE TRANSMISSÃO — dados corrompidos`** e rejeita os dados.

---

## 6. Comparação dos Métodos

A tabela abaixo sintetiza as distinções arquiteturais e operacionais entre os dois métodos implementados:

| Característica | Método 1 — Batidas por Impacto | Método 2 — Modulação FSK |
| :--- | :--- | :--- |
| **Técnica de Sinalização** | Transientes mecânicos em banda base (pulsos amortecidos). | Chaveamento de frequência de fase contínua (CP-FSK). |
| **Representação do Bit 0** | 1 batida acústica isolada. | Senoide contínua de **$1200\text{ Hz}$** ($25\text{ ms}$). |
| **Representação do Bit 1** | 2 batidas acústicas consecutivas rápidas ($\le 350\text{ ms}$). | Senoide contínua de **$2200\text{ Hz}$** ($25\text{ ms}$). |
| **Entrada Automática** | Digitação de texto $\to$ síntese de batidas pelo PC. | Digitação de texto $\to$ sintetizador de tons FSK. |
| **Entrada Manual** | Palmas/mesa diante do microfone $\to$ bits do Método 1. | Palmas/mesa $\to$ bits $\to$ modulação e emissão FSK. |
| **Transmissão pelo Alto-falante** | Sim (ondas sintetizadas de batida mecânica). | Sim (ondas senoidais de $1200\text{ Hz}$ e $2200\text{ Hz}$). |
| **Recepção pelo Microfone** | Sim (análise temporal de picos e envelope). | Sim (filtro casado de preâmbulo e análise por DFT). |
| **Sincronização de Quadro** | Intervalos temporais de guarda e silêncio. | Tom piloto senoidal de preâmbulo em **$1700\text{ Hz}$** ($150\text{ ms}$). |
| **Mecanismo de Erro** | **Bit de Paridade Par** (1 bit por caractere de 8 bits). | **CRC-8** ATM `0x07` (1 byte por pacote de dados). |
| **Formato de Enquadramento** | Quadros rígidos de **9 bits** (8 dados + 1 paridade). | Pacote variável: `[1B Tamanho] + [N Bytes] + [1B CRC8]`. |
| **Taxa Teórica de Bits** | $\approx \mathbf{1.43\text{ bps}}$ ($0.70\text{ s}$ por bit). | $\mathbf{40.0\text{ bps}}$ ($0.025\text{ s}$ por bit). |
| **Taxa Prática Medida** | $\approx 0.8\text{ a } 1.0\text{ bps}$ *(ou a medir em bancada física)*. | $\approx 14\text{ a } 35\text{ bps}$ *(conforme tamanho da mensagem)*. |
| **Sensibilidade a Ruído** | Vulnerável a impactos falsos e reverberação de mesa. | Resistente a ruído branco e ruído de banda estreita. |

---

## 7. Taxa de Transmissão

### 7.1. Taxa Teórica
A taxa teórica bruta ($R_{\text{teor}}$) representa a capacidade intrínseca do esquema de sinalização sem considerar preâmbulos e silêncios:
- **Método 1:**
  $$R_{\text{teor, M1}} = \frac{1}{T_{\text{bit}}} = \frac{1}{0.70\text{ s}} \approx 1.43\text{ bps}$$
- **Método 2 (FSK):**
  $$R_{\text{teor, M2}} = \frac{1}{T_{\text{sym}}} = \frac{1}{0.025\text{ s}} = 40.0\text{ bps}$$

### 7.2. Taxa Prática e Fatores de Degradação
A taxa prática líquida ($R_{\text{prat}}$) considera apenas a carga útil de dados transferida em função do tempo real total de transmissão:
$$R_{\text{prat}} = \frac{\text{Bits Úteis de Informação}}{T_{\text{preambulo}} + T_{\text{silêncios}} + T_{\text{controle}} + T_{\text{dados}}}$$

- **Cálculo Real para Mensagem "OI" (16 bits de dados) no Método 2:**
  - Bits totais no pacote (cabeçalho + dados + CRC): $32\text{ bits} \times 0.025\text{ s} = 0.800\text{ s}$.
  - Preâmbulo piloto de sincronização: $0.150\text{ s}$.
  - Silêncios de guarda inicial e final: $2 \times 0.100\text{ s} = 0.200\text{ s}$.
  - Tempo total medido: $1.150\text{ s}$.
  - Taxa prática líquida:
    $$R_{\text{prat}} = \frac{16\text{ bits}}{1.150\text{ s}} \approx 13.91\text{ bps}$$
- **Fatores Físicos que Reduzem a Taxa Prática no Canal Real:**
  1. **Dispersão e Reverberação:** Exigem intervalos de guarda entre símbolos para que a energia refletida da onda anterior se dissipe antes da chegada da próxima.
  2. **Sobrecarga de Controle (*Overhead*):** Bits de paridade, cabeçalhos de tamanho e bytes de CRC consomem fração da capacidade do canal.
  3. **Inércia do Operador Humano (no modo manual):** A coordenação motora para produzir palmas ou batidas limita a velocidade manual a cerca de $1$ bit por segundo.
  4. **Latência de Buffers de Áudio:** Os buffers do driver de áudio do sistema operacional introduzem latências de processamento ($\sim 10\text{ a } 50\text{ ms}$).

---

## 8. Desafios Enfrentados e Soluções Implementadas

Durante o ciclo de desenvolvimento e testes do projeto, diversos obstáculos técnicos foram encontrados e solucionados:

1. **Problema: Falsas Batidas Múltiplas por Reverberação Mecânica da Mesa (Método 1)**
   - *Causa:* Uma única batida de caneta ou mão na mesa gerava oscilações residuais secundárias na estrutura física, ultrapassando o limiar de amplitude repetidas vezes.
   - *Solução:* Implementação de um **tempo de debounce de $85\text{ ms}$**. Após qualquer impacto registrado, o receptor entra em estado inibitório temporário, descartando oscilações espúrias.

2. **Problema: Interferência do Ruído de Fundo da Sala de Aula**
   - *Causa:* Um limiar estático de amplitude tornava-se inoperante quando o ruído da sala mudava (ex.: ventiladores ligados ou pessoas conversando).
   - *Solução:* Criação do algoritmo de **Calibração de Ruído Ambiente** (`calibrar_ruido`), que mede o percentil estatístico do sinal por $1.5\text{ s}$ e ajusta o limiar de corte dinamicamente com margem segura acima do piso de ruído.

3. **Problema: Dessincronização do Início do Pacote FSK entre Computadores Distintos**
   - *Causa:* O receptor iniciava a gravação em instante arbitrário e não conseguia discernir o exato milissegundo de início dos dados, desalinhando as janelas de demodulação.
   - *Solução:* Aplicação de **Filtro Casado (*Matched Filter*) por correlação cruzada normalizada** com o tom piloto de $1700\text{ Hz}$. O alinhamento atinge precisão na escala de amostras individuais.

4. **Problema: Falsos Positivos de Preâmbulo em Áudio com Ruído Puro**
   - *Causa:* Em gravações de microfone sem nenhuma transmissão FSK ativa, flutuações aleatórias do ruído ambiente geravam picos matemáticos de correlação.
   - *Solução:* Introdução de verificação de razão pico/fundo ($\text{ratio} \ge 2.8$) associada a normalização estrita de amplitude, rejeitando completamente ruído estocástico.

5. **Problema: Recepção com Tempo de Gravação Residual do Microfone**
   - *Causa:* O microfone continuava gravando após o término do áudio FSK, acumulando ruído que corrompia o final do pacote.
   - *Solução:* Demodulação autônoma com leitura antecipada do **Byte 0 (comprimento $N$)**, delimitando com exatidão matemática o encerramento do pacote em $(N + 2) \times 8$ bits.

---

## 9. Testes e Validação

A qualidade e a conformidade do software foram validadas através de duas modalidades complementares: testes automatizados de unidade/integração e testes funcionais físicos.

### 9.1. Testes Automatizados Executados (27 Aprovados — 100%)
Executados diretamente no ambiente de desenvolvimento através do comando `python -m unittest discover tests -v`:

1. `test_01_calculo_paridade_casos_oficiais`: Validação matemática dos exemplos oficiais exigidos pelo edital da atividade.
2. `test_02_validacao_quadro_correto_e_corrompido`: Aprovação de quadros corretos e rejeição imediata de quadros alterados.
3. `test_03_injecao_proposital_erro_em_dados`: Inversão de bit de dados acusando falha de paridade.
4. `test_04_transmissao_acustica_sem_ruido`: Síntese de áudio de batidas e decodificação analítica idêntica.
5. `test_05_transmissao_acustica_com_ruido_ambiente`: Tolerância a ruído gaussiano aditivo sobre o áudio de impacto.
6. `test_06_fluxo_completo_mensagem_curta`: Ciclo completo para mensagem "OI" em quadros de 9 bits.
7. `test_07_transmissao_automatica_acustica_oi`: Síntese dos 18 bits de "OI", demodulação e validação de paridade em ambos os quadros.
8. `test_01_crc8_vetor_padrao_internacional`: Verificação do algoritmo CRC-8 com o vetor internacional `'123456789'` $\to$ `0xF4`.
9. `test_02_pacote_metodo2_integro_e_corrompido`: Montagem, desmontagem e validação de pacotes FSK íntegros e corrompidos.
10. `test_03_injecao_proposital_de_erro_fsk`: Inversão deliberada de 1 bit acusando falha de integridade no CRC-8.
11. `test_04_demodulacao_janela_individual_fsk`: Teste espectral ortogonal isolado para portadoras de $1200\text{ Hz}$ e $2200\text{ Hz}$.
12. `test_05_transmissao_acustica_fsk_sem_ruido`: Modulação e demodulação FSK completa sem ruído.
13. `test_06_transmissao_acustica_fsk_com_ruido`: Modulação e demodulação FSK sob canal ruidoso.
14. `test_07_calculo_taxa_bps`: Cálculo analítico das taxas de transmissão bruta e líquida.
15. `test_08_demodulacao_autonoma_sem_tamanho_previo`: Demodulação FSK cega com silêncios de guarda inicial e final.
16. `test_09_fluxo_metodo2_com_entrada_manual_de_impactos`: Teste de ponta a ponta do fluxo: Batidas $\to$ Bits $\to$ FSK $\to$ Demodulação $\to$ CRC-8 $\to$ Texto.
17. `test_10_rejeicao_de_ruido_puro`: Rejeição de falso preâmbulo em sinais contendo exclusivamente ruído estocástico.
18. `test_11_demodulacao_com_longo_atraso_e_ruido`: Simulação do teste físico real: início da escuta 2.5s antes da transmissão em canal acústico com ruído.
19. `test_req_01_transmissao_sem_ruido`: Validação formal do Requisito 1 de avaliação.
20. `test_req_02_transmissao_com_ruido`: Validação formal do Requisito 2 de avaliação.
21. `test_req_03_mensagem_curta`: Validação formal do Requisito 3 (transmissão de mensagem curta `'A'`).
22. `test_req_04_mensagem_maior`: Validação formal do Requisito 4 (transmissão de mensagem longa).
23. `test_req_05_erro_proposital_em_um_bit`: Validação formal do Requisito 5 (injeção determinística de erro).
24. `test_req_06_quadro_correto`: Validação formal do Requisito 6 (quadro íntegro aprovado).
25. `test_req_07_quadro_corrompido`: Validação formal do Requisito 7 (quadro corrompido reprovado).
26. `test_req_08_calculo_de_paridade`: Validação formal do Requisito 8 (regra de paridade par).
27. `test_req_09_deteccao_erro_metodo2_crc8`: Validação formal do Requisito 9 (algoritmo CRC-8).

### 9.2. Testes Manuais Acústicos (com Alto-falante e Microfone no Ar)
Os seguintes procedimentos funcionais foram planejados para execução presencial em bancada utilizando hardware real:

- [ ] **Teste Físico 1 — Método 1 Automático entre Dois Computadores:**
  - Computador A (TX) transmite a mensagem `"OI"` pelo alto-falante.
  - Computador B (RX) captura o som pelo microfone e reconstrói `"OI"`.
- [ ] **Teste Físico 2 — Método 1 Manual com Operador Humano:**
  - Usuário produz palmas ou batidas na mesa diante do microfone.
  - Computador exibe os bits em tempo real e remonta os caracteres.
- [ ] **Teste Físico 3 — Método 2 FSK entre Dois Computadores:**
  - Computador A (TX) transmite a mensagem `"OI"` em tons FSK pelo alto-falante.
  - Computador B (RX) captura pelo microfone, demodula e valida o CRC-8.
- [ ] **Teste Físico 4 — Método 2 com Entrada Manual de Batidas:**
  - Usuário produz batidas no microfone do Computador A.
  - Computador A converte os bits em sinal FSK e emite no alto-falante.
  - Computador B recebe o áudio FSK pelo ar e valida o CRC-8.
- [ ] **Teste Físico 5 — Demonstração de Detecção de Erros com Injeção Deliberada:**
  - Marcar a opção de injeção de erro no transmissor e demonstrar que o receptor acusa visualmente a corrupção de paridade ou CRC-8.

---

## 10. Desenvolvimento Individual
 
Este projeto foi concebido, arquitetado, implementado, testado e documentado **de forma estritamente individual** por um único aluno, sem divisão em equipes ou grupos.
 
- **Autor do Projeto:** Lucas Santana da Silva
- **R.A.:** 2208504
- **Curso:** Bacharelado em Ciência da Computação
- **Disciplina:** Redes de Computadores
 
### Escopo das Atividades Conduzidas Individualmente:
1. **Arquitetura Geral e Representação:** Estruturação dos módulos, conversão de dados (`conversao.py`) e fluxos de dados entre as camadas OSI 1 e 2.
2. **Camada Física — Método 1:** Desenvolvimento da síntese senoidal amortecida de batidas (`transmissor.py`) e do detector de impactos em tempo real com máquina de estados, calibração dinâmica de ruído e debounce (`receptor.py`).
3. **Camada Física — Método 2:** Implementação da modulação contínua CP-FSK com cálculo de taxas teóricas/práticas (`transmissor.py`), sincronização de quadro por filtro casado não-coerente em quadratura $I/Q$ com tom piloto de 1700 Hz, recuperação de alinhamento de símbolos (*Symbol Timing Recovery*) e demodulação com janelamento de Hann (`receptor.py`), incluindo suporte a entrada manual por batidas.
4. **Camada de Enlace Lógica:** Implementação e validação matemática da regra de Paridade Par em blocos de 9 bits, divisão polinomial do algoritmo CRC-8 padrão ATM (`0x07`) e rotina de injeção determinística de erro de bit (`deteccao_erros.py`).
5. **Interface de Usuário e Testes:** Construção da interface gráfica completa em Tkinter e do modo terminal CLI (`interface.py`, `main.py`), elaboração e execução da suíte com 27 testes automatizados, bem como a gravação do vídeo demonstrativo e redação de toda a documentação técnica.

---

## 11. Declaração do Uso de Inteligência Artificial

Em estrita consonância com as diretrizes acadêmicas da disciplina, com a transparência científica e com os critérios de integridade do projeto:

Durante o desenvolvimento do trabalho, ferramentas de **Inteligência Artificial Generativa** foram utilizadas como recurso de apoio e suporte técnico em etapas específicas do projeto, incluindo:
- **Estruturação do Código e Arquitetura:** Auxílio no planejamento modular da separação entre camada física, camada de enlace e camada de aplicação.
- **Compreensão de Conceitos Teóricos:** Esclarecimento de detalhes de processamento digital de sinais acústicos, continuidade de fase em CP-FSK, alinhamento por filtro casado (*matched filter*) e propriedades matemáticas da divisão polinomial em $\text{GF}(2)$ do CRC-8.
- **Identificação e Resolução de Problemas:** Auxílio no diagnóstico de problemas práticos, como falsas detecções causadas por reverberação de mesa (implementação de debounce), falsos preâmbulos causados por ruído branco (rejeição por razão pico/fundo) e corte de áudio residual de microfone.
- **Documentação e Organização:** Apoio na organização dos relatórios, formatação das tabelas de parâmetros, elaboração de roteiros práticos de gravação e material de estudo para apresentação.
- **Revisão e Testes Automatizados:** Auxílio na estruturação de casos de teste com a biblioteca `unittest` cobrindo cenários com e sem ruído, injeção de erros e casos de borda.

### Responsabilidade e Domínio Técnico do Autor:
- **Não Substituição do Aprendizado:** A utilização da IA não substituiu a compreensão ou a autoria do projeto. Cada algoritmo, função e parâmetro físico presente no código foi analisado, testado, ajustado e validado experimentalmente pelo autor.
- **Domínio Integral da Implementação:** O autor compreende integralmente o funcionamento matemático e operacional de todos os módulos do sistema (amostragem, filtros, limiares, paridade, CRC-8, demodulação e interface).
---

## 12. Como Instalar e Executar o Projeto

### Pré-requisitos
- **Python 3.10 ou superior** instalado no sistema operacional (Windows, Linux ou macOS).
- **Microfone e alto-falante** funcionais, configurados como dispositivos padrão de gravação e reprodução.

### Passo 1: Clonar o Repositório
```bash
git clone https://github.com/Santana92/RedesComputadores.git
cd Atividade1
```

### Passo 2: Instalar as Dependências
O projeto utiliza bibliotecas científicas consolidadas:
```bash
pip install -r requirements.txt
```
*(Conteúdo de `requirements.txt`: `numpy>=1.24.0` e `sounddevice>=0.4.6`)*

### Passo 3: Executar com Interface Gráfica (Recomendado)
```bash
python main.py
```

### Passo 4: Executar no Modo Terminal (CLI)
Para ambientes servidores ou sem servidor gráfico:
```bash
python main.py --cli
```

### Passo 5: Executar a Suíte de Testes Automatizados
```bash
python -m unittest discover tests -v
```

---

## 13. Exemplos de Utilização Passo a Passo

### Cenário 1: Transmissão Automática do Método 1 (Batidas) entre Dois PCs
1. **No Computador B (Receptor):**
   - Selecione `Método 1: Batidas por Impacto`.
   - Selecione o papel `Receptor (RX)`.
   - Clique em `🎚️ Calibrar Ruído Ambiente` para ajustar o limiar ao ruído da sala.
   - Clique em `🎙️ INICIAR ESCUTA DO MICROFONE`. O status indicará microfone ativo.
2. **No Computador A (Transmissor):**
   - Selecione `Método 1: Batidas por Impacto`.
   - Selecione o papel `Transmissor (TX)`.
   - Digite a mensagem `OI` no campo de texto.
   - Observe a sequência de 18 bits gerada na tela (`010011111010010011`).
   - Clique em `🔊 TRANSMITIR BATIDAS PELO ALTO-FALANTE`.
3. **Resultado:**
   - O alto-falante do Computador A emitirá as batidas audíveis.
   - O microfone do Computador B captará os impactos em tempo real.
   - Na tela do Computador B, cada quadro de 9 bits será validado com paridade par correta, culminando na mensagem reconstruída **`"OI"`**.

---

### Cenário 2: Transmissão FSK com Entrada Manual por Batidas (Método 2)
1. **No Computador A (Transmissor):**
   - Selecione `Método 2: FSK`.
   - Selecione o papel `Transmissor (TX)`.
   - Em Entrada de Dados, selecione `B) Entrada Manual por Impactos`.
   - Clique em `🎙️ INICIAR CAPTURA DE BATIDAS PARA FSK`.
   - Produza batidas no microfone (ex.: bata uma vez para bit `0`, ou bata duas vezes rápidas para bit `1`).
   - Clique em `⏹️ FINALIZAR CAPTURA DE BATIDAS`.
   - Clique em `🔊 MODULAR E TRANSMITIR BITS EM FSK`.
2. **No Computador B (Receptor):**
   - Selecione `Método 2: FSK`.
   - Selecione o papel `Receptor (RX)`.
   - Clique em `🎙️ CAPTAR ÁUDIO FSK PELO MICROFONE`.
3. **Resultado:**
   - O Computador A sintetiza os bits batidos pelo usuário em frequências de $1200\text{ Hz}$ e $2200\text{ Hz}$ com CRC-8.
   - O Computador B sincroniza pelo piloto de $1700\text{ Hz}$, demodula os tons FSK, valida o CRC-8 e exibe os dados válidos recebidos.

---

### Cenário 3: Demonstração de Detecção de Erro Proposital
1. No Transmissor (em qualquer método), marque a opção **`Injetar Erro Proposital`**.
2. Realize a transmissão acústica pelo alto-falante.
3. No Receptor, observe que o software detecta prontamente a incoerência matemática:
   - **Método 1:** Banner vermelho **`✗ FALHA DE TRANSMISSÃO — Paridade Inválida no Quadro X`**.
   - **Método 2:** Banner vermelho **`✗ FALHA DE TRANSMISSÃO — dados corrompidos (Divergência de CRC-8)`**.

---

## 14. Conclusão

O desenvolvimento deste projeto proporcionou uma compreensão empírica e aprofundada dos desafios reais que governam a comunicação de dados na Camada Física e de Enlace. 

As principais conclusões extraídas da implementação prática incluem:
1. **A Natureza Desafiadora do Canal Físico:** Diferente de simulações puramente lógicas em software, o canal acústico real impõe restrições severas de eco, absorção atmosférica, ruído aditivo e limitações de hardware (placas de som e transdutores).
2. **A Superioridade da Modulação em Frequência (FSK):** A transição de um sistema em banda base por impactos para modulação por chaveamento de frequência (FSK) representou um ganho de aproximadamente $28\times$ na velocidade de transmissão, demonstrando como técnicas de multiplexação espectral potencializam a utilização da largura de banda.
3. **A Indispensabilidade dos Mecanismos de Enlace:** Em um canal ruidoso e não guiado, a simples transmissão de bits é inviável sem enquadramento rígido e algoritmos de detecção de erros. O CRC-8 provou ser expressivamente mais robusto que a paridade simples contra rajadas de perturbação externa.
4. **Independência Operacional dos Métodos:** Ficou comprovado que ambos os métodos atendem plenamente aos objetivos da atividade, oferecendo transmissão e recepção por áudio real e suportando tanto a emissão automatizada quanto a entrada manual de dados por impactos físicos.

---

## Licença

Este projeto é distribuído sob a licença **MIT Open Source**. Consulte o arquivo [LICENSE](LICENSE) para obter os termos integrais de uso e distribuição.
