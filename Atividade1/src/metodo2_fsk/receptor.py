# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Receptor do Método 2: Demodulação Acústica FSK (Frequency-Shift Keying).

Captura o sinal de áudio, sincroniza o início da transmissão usando
o tom piloto de preâmbulo e demodula cada janela temporal em bits 0 ou 1
através de análise espectral por correlação ortogonal (DFT).
"""

from typing import List, Tuple, Optional
import numpy as np
import sounddevice as sd

from .transmissor import (
    FREQ_BIT_0,
    FREQ_BIT_1,
    FREQ_PREAMBULO,
    DURACAO_SIMBOLO,
    DURACAO_PREAMBULO,
)


def calcular_energia_frequencia(
    janela: np.ndarray,
    frequencia: float,
    sample_rate: int = 44100
) -> float:
    """
    Calcula a densidade de energia do sinal em uma frequência específica.
    Equivale à Transformada Discreta de Fourier (DFT) calculada no ponto exato,
    atuando como um filtro casado (filtro de correlação senoidal e cossenoidal).
    """
    # Aqui calculamos a DFT pontual projetando o sinal em seno e cosseno para medir a energia
    n = np.arange(len(janela), dtype=np.float32)
    omega = 2.0 * np.pi * frequencia / sample_rate
    
    parte_real = np.sum(janela * np.cos(omega * n))
    parte_imag = np.sum(janela * np.sin(omega * n))
    
    energia = float(parte_real**2 + parte_imag**2) / len(janela)
    return energia


def demodular_janela_fsk(
    janela: np.ndarray,
    sample_rate: int = 44100
) -> Tuple[int, float, float]:
    """
    Decodifica uma janela de símbolo único (25 ms) em bit 0 ou bit 1.
    
    Retorna:
    - bit_decodificado: 0 ou 1
    - energia_f0: energia medida em 1200 Hz
    - energia_f1: energia medida em 2200 Hz
    """
    # Medimos a energia nas duas portadoras: se 2200 Hz for mais forte, é bit 1; senão, é bit 0.
    e0 = calcular_energia_frequencia(janela, FREQ_BIT_0, sample_rate)
    e1 = calcular_energia_frequencia(janela, FREQ_BIT_1, sample_rate)
    
    bit = 1 if (e1 > e0) else 0
    return bit, e0, e1


def detectar_preambulo(
    sinal: np.ndarray,
    sample_rate: int = 44100
) -> Optional[int]:
    """
    Localiza o preâmbulo (tom de 1700 Hz) utilizando Filtro Casado (Matched Filter)
    via correlação cruzada. O pico do envelope da correlação determina
    com extrema precisão o término do tom piloto e o início dos símbolos de dados.
    """
    amostras_pre = int(sample_rate * DURACAO_PREAMBULO)
    if len(sinal) < amostras_pre:
        return None

    # Normalizamos o sinal capturado para que o nível de volume não distorça a correlação
    sinal_cent = sinal - np.mean(sinal)
    pico_sinal = float(np.max(np.abs(sinal_cent)))
    if pico_sinal < 0.005:
        return None
    sinal_norm = (sinal_cent / pico_sinal).astype(np.float32)

    t_pre = np.arange(amostras_pre, dtype=np.float32) / sample_rate
    padrao_pre = np.sin(2.0 * np.pi * FREQ_PREAMBULO * t_pre).astype(np.float32)

    # Aqui aplicamos o Filtro Casado (correlação cruzada) com o padrão do tom piloto de 1700 Hz
    corr = np.correlate(sinal_norm, padrao_pre, mode="valid")
    amostras_ciclo = max(1, int(sample_rate / FREQ_PREAMBULO))
    filtro_suav = np.ones(amostras_ciclo, dtype=np.float32) / amostras_ciclo
    corr_envelope = np.convolve(np.abs(corr), filtro_suav, mode="same")

    pico_max = float(np.max(corr_envelope))
    media_fundo = float(np.mean(corr_envelope))

    # Rejeitamos ruído puro da sala exigindo que o pico seja pelo menos 2.8x maior que a média de fundo
    ratio = (pico_max / media_fundo) if media_fundo > 0 else 0.0
    if pico_max < 150.0 or ratio < 2.8:
        return None

    indice_pico = int(np.argmax(corr_envelope))
    # O início dos dados ocorre logo após o preâmbulo
    inicio_dados = indice_pico + amostras_pre
    return inicio_dados


def demodular_bits_fsk(
    sinal: np.ndarray,
    quantidade_bits: Optional[int] = None,
    sample_rate: int = 44100,
    duracao_simbolo: float = DURACAO_SIMBOLO
) -> Tuple[List[int], int]:
    """
    Demodula a sequência de bits do áudio FSK completo.
    
    Retorna:
    - bits: lista dos bits decodificados (0s e 1s).
    - inicio_amostra: amostra onde os dados iniciaram.
    """
    amostras_por_simbolo = int(sample_rate * duracao_simbolo)
    
    # Sincronização ótima via filtro casado
    inicio = detectar_preambulo(sinal, sample_rate=sample_rate)
    if inicio is None:
        # Fallback de envelope em caso de sinal direto sem piloto
        envelope = np.abs(sinal - np.mean(sinal))
        picos = np.where(envelope > 0.08)[0]
        inicio = int(picos[0]) if len(picos) > 0 else 0
        
    bits = []
    total_amostras = len(sinal)
    amostra_atual = inicio
    
    limite = quantidade_bits
    # Nessa parte iteramos de 25 em 25 ms decodificando cada símbolo de bit
    while amostra_atual + amostras_por_simbolo <= total_amostras:
        if limite is not None and len(bits) >= limite:
            break
            
        janela = sinal[amostra_atual : amostra_atual + amostras_por_simbolo]
        bit, _, _ = demodular_janela_fsk(janela, sample_rate=sample_rate)
        bits.append(bit)
        amostra_atual += amostras_por_simbolo
        
        # Se quantidade_bits não foi informada, descobrimos dinamicamente pelo Byte 0 (comprimento)
        # e encerramos a leitura para não demodular o silêncio gravado no fim do áudio
        if limite is None and len(bits) == 8:
            tam_declarado = 0
            for shift, b in enumerate(bits[:8]):
                tam_declarado = (tam_declarado << 1) | (b & 1)
            if 0 < tam_declarado <= 250:
                limite = (1 + tam_declarado + 1) * 8
        
    return bits, inicio


def decodificar_audio_fsk(
    sinal: np.ndarray,
    quantidade_bits: Optional[int] = None,
    sample_rate: int = 44100
) -> List[int]:
    """Atalho de alto nível para decodificar bits a partir de um sinal de áudio."""
    bits, _ = demodular_bits_fsk(sinal, quantidade_bits=quantidade_bits, sample_rate=sample_rate)
    return bits


def gravar_audio_microfone_fsk(
    duracao_segundos: float,
    sample_rate: int = 44100
) -> np.ndarray:
    """Grava áudio do microfone para o receptor FSK."""
    print(f"[*] Escutando canal FSK ({duracao_segundos:.1f}s)...")
    gravacao = sd.rec(int(duracao_segundos * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
    sd.wait()
    print("[*] Áudio captado.")
    return gravacao.flatten()
