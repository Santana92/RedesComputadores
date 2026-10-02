# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Transmissor do Método 2: Modulação Acústica FSK (Frequency-Shift Keying).

Converte bits em tons de áudio audíveis em frequências distintas:
- Bit 0: 1200 Hz
- Bit 1: 2200 Hz
- Preâmbulo de sincronismo: 1700 Hz
"""

from typing import List, Dict, Any
import numpy as np
import sounddevice as sd

# ==============================================================================
# PARÂMETROS DA CAMADA FÍSICA FSK
# ==============================================================================
# Definimos 1200 Hz para o bit 0 e 2200 Hz para o bit 1:
# Ambas são ortogonais em 25 ms (completam 30 e 55 ciclos exatos) e fáceis de reproduzir.
FREQ_BIT_0: float = 1200.0       # Frequência representativa do bit 0 (Hz)
FREQ_BIT_1: float = 2200.0       # Frequência representativa do bit 1 (Hz)

# Tom piloto de 1700 Hz: fica exatamente no meio das duas frequências para sincronização
FREQ_PREAMBULO: float = 1700.0   # Tom piloto de preâmbulo e sincronismo (Hz)

# Foi escolhida a duração de 25 ms por símbolo para garantir uma taxa teórica de 40 bps
DURACAO_SIMBOLO: float = 0.025    # Duração de cada bit (25 ms = 40 bps de taxa bruta)
DURACAO_PREAMBULO: float = 0.15   # Preâmbulo de 150 ms para sincronização de quadro
SILENCIO_GUARDA: float = 0.10     # Silêncio de guarda no início e término


def sintetizar_bits_fsk(
    bits: List[int],
    sample_rate: int = 44100,
    duracao_simbolo: float = DURACAO_SIMBOLO,
    incluir_preambulo: bool = True
) -> np.ndarray:
    """
    Gera o vetor de áudio modulado em FSK contínua (Continuous-Phase FSK).
    A fase contínua evita transientes abruptos de clique entre símbolos,
    concentrando a energia puramente nas frequências portadoras.
    """
    amostras_por_simbolo = int(sample_rate * duracao_simbolo)
    partes = []
    # Mantemos a variável fase_atual entre os símbolos para garantir fase contínua (CP-FSK)
    # e evitar estalos indesejados no alto-falante.
    fase_atual = 0.0
    dois_pi = 2.0 * np.pi

    # 1. Silêncio inicial de guarda
    if SILENCIO_GUARDA > 0:
        amostras_silencio = int(sample_rate * SILENCIO_GUARDA)
        partes.append(np.zeros(amostras_silencio, dtype=np.float32))

    # 2. Tom piloto de preâmbulo para sincronização do receptor
    if incluir_preambulo:
        amostras_preambulo = int(sample_rate * DURACAO_PREAMBULO)
        t = np.arange(amostras_preambulo, dtype=np.float32) / sample_rate
        fase = fase_atual + dois_pi * FREQ_PREAMBULO * t
        tom_preambulo = np.sin(fase, dtype=np.float32)
        # Aplica pequena janela de fade in/out no preâmbulo
        fade = np.linspace(0.0, 1.0, min(100, amostras_preambulo // 4), dtype=np.float32)
        tom_preambulo[:len(fade)] *= fade
        tom_preambulo[-len(fade):] *= fade[::-1]
        partes.append(tom_preambulo)
        fase_atual = float(fase[-1] + dois_pi * FREQ_PREAMBULO / sample_rate) % dois_pi

    # 3. Símbolos dos Bits (0 = 1200 Hz, 1 = 2200 Hz)
    dt = 1.0 / sample_rate
    t_simbolo = np.arange(amostras_por_simbolo, dtype=np.float32) * dt

    for bit in bits:
        # Aqui selecionamos a frequência portadora de acordo com o bit
        freq = FREQ_BIT_1 if (bit == 1) else FREQ_BIT_0
        fase = fase_atual + dois_pi * freq * t_simbolo
        onda = np.sin(fase, dtype=np.float32)
        partes.append(onda)
        # Atualiza a fase contínua para o próximo símbolo
        fase_atual = float(fase[-1] + dois_pi * freq * dt) % dois_pi

    # 4. Silêncio final de guarda
    if SILENCIO_GUARDA > 0:
        amostras_silencio = int(sample_rate * SILENCIO_GUARDA)
        partes.append(np.zeros(amostras_silencio, dtype=np.float32))

    audio_completo = np.concatenate(partes)
    # Normalizamos para amplitude máxima de 0.8 para evitar saturação no alto-falante
    pico = np.max(np.abs(audio_completo))
    if pico > 0:
        audio_completo = (audio_completo / pico) * 0.8
    return audio_completo.astype(np.float32)


def transmitir_audio_fsk(audio: np.ndarray, sample_rate: int = 44100) -> None:
    """Reproduz o sinal acústico FSK nos alto-falantes."""
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


def parar_transmissao_fsk() -> None:
    """Interrompe imediatamente a reprodução do sinal FSK."""
    try:
        sd.stop()
    except Exception:
        pass


def calcular_taxa_bps(
    num_bits_dados: int,
    num_bits_totais: int,
    duracao_simbolo: float = DURACAO_SIMBOLO,
    incluir_preambulo: bool = True
) -> Dict[str, Any]:
    """
    Calcula as taxas teórica e prática de transmissão em bits por segundo (bps).
    
    - Taxa Teórica: Capacidade bruta da modulação (1 / duracao_simbolo).
    - Taxa Prática: Dados úteis transferidos pelo tempo real total (incluindo preâmbulo e controle).
    """
    taxa_teorica = 1.0 / duracao_simbolo
    tempo_simbolos = num_bits_totais * duracao_simbolo
    tempo_overhead = (DURACAO_PREAMBULO if incluir_preambulo else 0.0) + (2 * SILENCIO_GUARDA)
    tempo_total = tempo_simbolos + tempo_overhead
    
    taxa_pratica = (num_bits_dados / tempo_total) if tempo_total > 0 else 0.0
    
    return {
        "taxa_teorica_bps": round(taxa_teorica, 2),
        "taxa_pratica_bps": round(taxa_pratica, 2),
        "duracao_total_s": round(tempo_total, 3),
        "bits_dados": num_bits_dados,
        "bits_totais": num_bits_totais,
    }
