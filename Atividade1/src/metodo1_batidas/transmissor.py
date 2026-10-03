# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Transmissor do Método 1 (Impacto / Batidas).

Responsável por sintetizar e emitir os sinais acústicos correspondentes
aos bits 0 e 1, respeitando a cadência e silêncios do protocolo.
"""

from typing import List
import numpy as np
import sounddevice as sd


def gerar_som_batida(
    sample_rate: int = 44100,
    duracao: float = 0.035,
    freq_principal: float = 900.0,
    fator_amortecimento: float = 0.007
) -> np.ndarray:
    """
    Gera a forma de onda de um impacto acústico percussivo sintetizado
    pelo computador para reprodução no alto-falante.
    
    Usa uma oscilação amortecida com decaimento exponencial rápido.
    """
    total_amostras = int(sample_rate * duracao)
    t = np.linspace(0, duracao, total_amostras, endpoint=False, dtype=np.float32)
    
    # Envelope de decaimento exponencial:
    # Foi escolhida a frequência de 900 Hz com decaimento de 7 ms para que o som soe
    # como um clique acústico seco e nítido, fácil de detectar pelo microfone.
    envelope = np.exp(-t / fator_amortecimento)
    
    # Onda senoidal com decaimento + componente de transiente
    onda = np.sin(2.0 * np.pi * freq_principal * t) * envelope
    ruído = (np.random.rand(total_amostras).astype(np.float32) * 2.0 - 1.0) * (envelope ** 2) * 0.4
    
    batida = onda + ruído
    # Normalização para pico de amplitude ~0.9
    max_amp = np.max(np.abs(batida))
    if max_amp > 0:
        batida = (batida / max_amp) * 0.9
    return batida.astype(np.float32)


def sintetizar_bit_0(
    sample_rate: int = 44100,
    duracao_total: float = 0.8
) -> np.ndarray:
    """
    Sintetiza o Bit 0: Silêncio + 1 Batida + Silêncio.
    """
    # Para o Bit 0, sintetizamos apenas 1 batida única isolada no centro da janela de 0.8s
    batida = gerar_som_batida(sample_rate=sample_rate)
    tamanho_total = int(sample_rate * duracao_total)
    sinal = np.zeros(tamanho_total, dtype=np.float32)
    
    # Posiciona a batida aproximadamente no centro da janela
    posicao_inicio = (tamanho_total - len(batida)) // 2
    sinal[posicao_inicio : posicao_inicio + len(batida)] = batida
    return sinal


def sintetizar_bit_1(
    sample_rate: int = 44100,
    duracao_total: float = 0.8,
    intervalo_entre_batidas: float = 0.16
) -> np.ndarray:
    """
    Sintetiza o Bit 1: Silêncio + 2 Batidas Consecutivas + Silêncio.
    """
    # Para o Bit 1, sintetizamos 2 batidas consecutivas com intervalo de 160 ms.
    # Esse intervalo fica bem dentro da nossa janela dupla de 350 ms do receptor.
    batida = gerar_som_batida(sample_rate=sample_rate)
    tamanho_total = int(sample_rate * duracao_total)
    sinal = np.zeros(tamanho_total, dtype=np.float32)
    
    espacamento_amostras = int(sample_rate * intervalo_entre_batidas)
    duracao_par = len(batida) + espacamento_amostras
    
    posicao_inicio = (tamanho_total - duracao_par) // 2
    # Primeira batida
    sinal[posicao_inicio : posicao_inicio + len(batida)] = batida
    # Segunda batida consecutiva
    pos_2 = posicao_inicio + espacamento_amostras
    sinal[pos_2 : pos_2 + len(batida)] = batida
    return sinal


def sintetizar_bits_metodo1(
    bits: List[int],
    sample_rate: int = 44100,
    tempo_bit: float = 0.8,
    silencio_guarda: float = 0.5
) -> np.ndarray:
    """
    Gera o áudio completo contendo todos os bits codificados,
    com um intervalo de silêncio no início e no final para sincronismo.
    """
    # Adicionamos um silêncio de guarda no início e fim para garantir que o microfone
    # tenha tempo de iniciar a gravação sem cortar a primeira batida.
    partes = []
    
    # Silêncio inicial (guarda de sincronismo)
    if silencio_guarda > 0:
        partes.append(np.zeros(int(sample_rate * silencio_guarda), dtype=np.float32))
    
    for bit in bits:
        if bit == 0:
            partes.append(sintetizar_bit_0(sample_rate=sample_rate, duracao_total=tempo_bit))
        else:
            partes.append(sintetizar_bit_1(sample_rate=sample_rate, duracao_total=tempo_bit))
            
    # Silêncio final
    if silencio_guarda > 0:
        partes.append(np.zeros(int(sample_rate * silencio_guarda), dtype=np.float32))
        
    return np.concatenate(partes)


def transmitir_audio_metodo1(audio: np.ndarray, sample_rate: int = 44100) -> None:
    """
    Reproduz o vetor de áudio nos alto-falantes de forma síncrona.
    """
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


def parar_transmissao_metodo1() -> None:
    """Interrompe imediatamente a reprodução de áudio das batidas."""
    try:
        sd.stop()
    except Exception:
        pass

