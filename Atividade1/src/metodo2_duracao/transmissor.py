# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Transmissor do Método 2: Codificação por Duração do Impacto Acústico.

Neste método, a informação binária é transmitida pela duração de cada impacto:
- Bit 0: Impacto acústico curto (50 ms)
- Bit 1: Impacto acústico longo (160 ms)
- Sincronização: Preâmbulo com padrão alternado conhecido (10101010)

Os impactos são gerados digitalmente pelo computador e reproduzidos
através do alto-falante no meio físico (ar).
"""

from typing import List, Dict, Any
import numpy as np
import sounddevice as sd

# ==============================================================================
# PARÂMETROS CENTRALIZADOS DA CAMADA FÍSICA (MÉTODO 2 - DURAÇÃO)
# ==============================================================================

# Frequência central do pulso acústico gerado pelo alto-falante.
# Escolhemos 900 Hz porque alto-falantes e microfones comuns respondem muito bem nessa faixa,
# e ela fica acima dos ruídos graves da sala (ar-condicionado, ventoinhas).
FREQ_IMPACTO: float = 900.0

# Duração do impacto para cada bit:
# O bit 0 é um impacto curto de 50 ms.
DURACAO_IMPACTO_CURTO: float = 0.050

# O bit 1 é um impacto longo de 160 ms.
# Foi escolhido 160 ms para haver uma diferença nítida e segura em relação aos 50 ms.
DURACAO_IMPACTO_LONGO: float = 0.160

# Limiar de decisão: ponto médio entre impacto curto e longo (105 ms).
# Qualquer impacto com duração menor que esse limiar é classificado como 0; se maior ou igual, é 1.
LIMIAR_DURACAO: float = 0.105

# Intervalo de silêncio entre símbolos consecutivos.
# 150 ms é tempo suficiente para o som anterior cessar e o eco da sala dissipar,
# evitando que dois impactos se fundam em um só.
INTERVALO_ENTRE_IMPACTOS: float = 0.150

# Silêncio de guarda no início e término da transmissão (200 ms).
# Dá tempo para o microfone do receptor iniciar e estabilizar a captura.
SILENCIO_GUARDA: float = 0.200

# Preâmbulo de sincronização: padrão binário conhecido enviado antes do pacote de dados.
# Permite ao receptor localizar exatamente onde começam os dados no áudio captado.
PADRAO_PREAMBULO: List[int] = [1, 0, 1, 0, 1, 0, 1, 0]


def gerar_som_impacto_duracao(
    duracao: float,
    sample_rate: int = 44100,
    freq: float = FREQ_IMPACTO
) -> np.ndarray:
    """
    Gera a forma de onda de um impacto acústico com a duração especificada.
    
    Aplica uma suave janela de subida (fade-in de 5 ms) e descida (fade-out de 10 ms)
    para evitar cliques secos do alto-falante e concentrar o sinal na frequência desejada.
    """
    total_amostras = max(1, int(sample_rate * duracao))
    t = np.arange(total_amostras, dtype=np.float32) / sample_rate
    
    # Onda senoidal na frequência do impacto
    onda = np.sin(2.0 * np.pi * freq * t, dtype=np.float32)
    
    # Envelope trapezoidal para evitar transientes abruptos de borda
    envelope = np.ones(total_amostras, dtype=np.float32)
    n_fade_in = min(int(sample_rate * 0.005), total_amostras // 4)
    n_fade_out = min(int(sample_rate * 0.010), total_amostras // 4)
    
    if n_fade_in > 0:
        envelope[:n_fade_in] = np.linspace(0.0, 1.0, n_fade_in, dtype=np.float32)
    if n_fade_out > 0:
        envelope[-n_fade_out:] = np.linspace(1.0, 0.0, n_fade_out, dtype=np.float32)
        
    som = onda * envelope
    
    # Normalizamos para amplitude de pico segura (~0.85) evitando distorção no alto-falante
    max_amp = float(np.max(np.abs(som)))
    if max_amp > 0:
        som = (som / max_amp) * 0.85
        
    return som.astype(np.float32)


def sintetizar_bits_duracao(
    bits: List[int],
    sample_rate: int = 44100,
    incluir_preambulo: bool = True
) -> np.ndarray:
    """
    Sintetiza a sequência completa de áudio para a lista de bits fornecida.
    
    Estrutura do sinal gerado:
    [Silêncio de Guarda] + [Preâmbulo Opcional] + [Bits com Durações Curtas/Longas] + [Silêncio Final]
    """
    partes = []
    
    # 1. Silêncio inicial de guarda
    if SILENCIO_GUARDA > 0:
        amostras_silencio = int(sample_rate * SILENCIO_GUARDA)
        partes.append(np.zeros(amostras_silencio, dtype=np.float32))
        
    # Sequência de bits a transmitir (preâmbulo + dados)
    bits_para_transmitir = list(PADRAO_PREAMBULO) + list(bits) if incluir_preambulo else list(bits)
    amostras_intervalo = int(sample_rate * INTERVALO_ENTRE_IMPACTOS)
    
    for bit in bits_para_transmitir:
        # Se for 0, o impacto é curto; se for 1, é longo
        dur = DURACAO_IMPACTO_LONGO if (bit == 1) else DURACAO_IMPACTO_CURTO
        pulso = gerar_som_impacto_duracao(dur, sample_rate=sample_rate, freq=FREQ_IMPACTO)
        partes.append(pulso)
        
        # Silêncio entre os impactos para que o receptor consiga separá-los nitidamente
        partes.append(np.zeros(amostras_intervalo, dtype=np.float32))
        
    # 2. Silêncio final de guarda
    if SILENCIO_GUARDA > 0:
        amostras_silencio = int(sample_rate * SILENCIO_GUARDA)
        partes.append(np.zeros(amostras_silencio, dtype=np.float32))
        
    if not partes:
        return np.zeros(0, dtype=np.float32)
        
    return np.concatenate(partes)


def transmitir_audio_duracao(audio: np.ndarray, sample_rate: int = 44100) -> None:
    """Reproduz o sinal acústico gerado nos alto-falantes de forma síncrona."""
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


def parar_transmissao_duracao() -> None:
    """Interrompe imediatamente a reprodução do sinal nos alto-falantes."""
    try:
        sd.stop()
    except Exception:
        pass


def calcular_taxa_bps(
    num_bits_dados: int,
    num_bits_totais: int,
    incluir_preambulo: bool = True
) -> Dict[str, Any]:
    """
    Calcula as taxas teórica e prática de transmissão em bits por segundo (bps).
    
    - Taxa Teórica: Calculada com base na duração média de um símbolo:
      T_medio = (T_curto + T_longo) / 2 + T_intervalo
      Taxa Teórica = 1 / T_medio
    - Taxa Prática: Dados úteis divididos pelo tempo total de áudio (incluindo preâmbulo e guardas).
    """
    tempo_medio_simbolo = ((DURACAO_IMPACTO_CURTO + DURACAO_IMPACTO_LONGO) / 2.0) + INTERVALO_ENTRE_IMPACTOS
    taxa_teorica = (1.0 / tempo_medio_simbolo) if tempo_medio_simbolo > 0 else 0.0
    
    n_preambulo = len(PADRAO_PREAMBULO) if incluir_preambulo else 0
    total_simbolos = num_bits_totais + n_preambulo
    tempo_simbolos = total_simbolos * tempo_medio_simbolo
    tempo_total = tempo_simbolos + (2.0 * SILENCIO_GUARDA)
    
    taxa_pratica = (num_bits_dados / tempo_total) if tempo_total > 0 else 0.0
    
    return {
        "taxa_teorica_bps": round(taxa_teorica, 2),
        "taxa_pratica_bps": round(taxa_pratica, 2),
        "duracao_total_s": round(tempo_total, 3),
        "bits_dados": num_bits_dados,
        "bits_totais": num_bits_totais,
    }
