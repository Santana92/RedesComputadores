# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Receptor do Método 2: Detecção de Impactos e Classificação por Duração.

O receptor capta o sinal do microfone, calcula o envelope de energia do áudio,
localiza os impactos acústicos, mede a duração de cada um e os classifica:
- Impacto curto (< 105 ms)  -> Bit 0
- Impacto longo (>= 105 ms) -> Bit 1

Após converter os impactos em bits, busca o preâmbulo de sincronização (10101010),
extrai o pacote de dados e valida a integridade com CRC-8.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
import numpy as np
import sounddevice as sd

from .transmissor import (
    LIMIAR_DURACAO,
    PADRAO_PREAMBULO,
    DURACAO_IMPACTO_CURTO,
    DURACAO_IMPACTO_LONGO,
)


def calcular_envelope_energia(
    sinal: np.ndarray,
    tamanho_janela_ms: float = 12.0,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Calcula o envelope de amplitude suave do sinal de áudio.
    
    Remove o nível DC, retifica a onda e aplica média móvel para
    suprimir a oscilação rápida da portadora e revelar a forma da duração.
    """
    if len(sinal) == 0:
        return np.zeros(0, dtype=np.float32)
        
    sinal_centralizado = sinal - np.mean(sinal)
    retificado = np.abs(sinal_centralizado)
    
    # Janela de suavização de 12 ms para alisar as senoides sem distorcer o tempo do pulso
    janela_amostras = max(1, int(sample_rate * (tamanho_janela_ms / 1000.0)))
    filtro = np.ones(janela_amostras, dtype=np.float32) / float(janela_amostras)
    
    envelope = np.convolve(retificado, filtro, mode="same")
    return envelope.astype(np.float32)


def detectar_impactos_com_duracao(
    sinal: np.ndarray,
    sample_rate: int = 44100,
    limiar_duracao: float = LIMIAR_DURACAO,
    gap_merge_ms: float = 35.0,
    min_pulse_ms: float = 20.0
) -> Tuple[List[int], List[Dict[str, Any]]]:
    """
    Detecta cada impacto sonoro no sinal, mede sua duração em milissegundos
    e classifica em bit 0 (curto) ou bit 1 (longo).
    
    Retorna:
    - bits: lista de inteiros (0s e 1s)
    - relatorio_impactos: lista de dicionários com detalhes de cada impacto para debug e interface
    """
    if len(sinal) == 0:
        return [], []
        
    envelope = calcular_envelope_energia(sinal, sample_rate=sample_rate)
    pico_maximo = float(np.max(envelope))
    ruido_fundo = float(np.percentile(envelope, 25))
    
    # Se o sinal for silêncio absoluto ou ruído imperceptível
    if pico_maximo < 0.025:
        return [], []
        
    # Limiar adaptativo de amplitude: fica confortavelmente acima do ruído de fundo
    limiar_amp = max(0.035, ruido_fundo * 3.0, ruido_fundo + (pico_maximo - ruido_fundo) * 0.22)
    
    # 1. Localiza os trechos contíguos onde a energia superou o limiar
    ativo = envelope > limiar_amp
    if not np.any(ativo):
        return [], []
        
    diff = np.diff(ativo.astype(np.int8))
    starts = np.where(diff == 1)[0] + 1
    ends = np.where(diff == -1)[0] + 1
    
    if ativo[0]:
        starts = np.r_[0, starts]
    if ativo[-1]:
        ends = np.r_[ends, len(ativo)]
        
    # 2. Reúne segmentos muito próximos (gap < 35 ms) para absorver pequenas oscilações de reverberação
    gap_max_amostras = int(sample_rate * (gap_merge_ms / 1000.0))
    blocos_unificados_ini = []
    blocos_unificados_fim = []
    
    for s, e in zip(starts, ends):
        if not blocos_unificados_ini:
            blocos_unificados_ini.append(s)
            blocos_unificados_fim.append(e)
        else:
            if s - blocos_unificados_fim[-1] < gap_max_amostras:
                # É continuação do mesmo impacto prolongado pela sala
                blocos_unificados_fim[-1] = e
            else:
                blocos_unificados_ini.append(s)
                blocos_unificados_fim.append(e)
                
    # 3. Mede a duração de cada impacto e classifica em curto (0) ou longo (1)
    min_amostras_pulso = int(sample_rate * (min_pulse_ms / 1000.0))
    bits = []
    relatorio_impactos = []
    
    for idx, (s, e) in enumerate(zip(blocos_unificados_ini, blocos_unificados_fim)):
        duracao_amostras = e - s
        # Descarta estalos insignificantes muito curtos (< 20 ms), que são ruídos espúrios
        if duracao_amostras < min_amostras_pulso:
            continue
            
        duracao_s = duracao_amostras / sample_rate
        duracao_ms = duracao_s * 1000.0
        
        # Classificação por duração:
        # Menor que o limiar (105 ms) -> Bit 0 (Impacto Curto)
        # Maior ou igual ao limiar    -> Bit 1 (Impacto Longo)
        bit = 1 if (duracao_s >= limiar_duracao) else 0
        bits.append(bit)
        
        relatorio_impactos.append({
            "impacto_idx": len(bits),
            "tempo_inicio_s": round(s / sample_rate, 3),
            "duracao_ms": round(duracao_ms, 1),
            "classificacao": "LONGO" if bit == 1 else "CURTO",
            "bit": bit
        })
        
    return bits, relatorio_impactos


def localizar_preambulo(
    bits: List[int],
    padrao_preambulo: Optional[List[int]] = None
) -> int:
    """
    Localiza o índice inicial do preâmbulo na sequência de bits recuperados.
    Retorna o índice onde o preâmbulo começa, ou -1 se não for encontrado.
    """
    if padrao_preambulo is None:
        padrao_preambulo = PADRAO_PREAMBULO
        
    tam_pre = len(padrao_preambulo)
    if len(bits) < tam_pre:
        return -1
        
    # Busca pelo padrão exato do preâmbulo
    for i in range(len(bits) - tam_pre + 1):
        if bits[i : i + tam_pre] == padrao_preambulo:
            return i
            
    # Fallback tolerante: se os últimos 4 bits do preâmbulo baterem (1, 0, 1, 0)
    sufixo_4 = padrao_preambulo[-4:]
    for i in range(len(bits) - len(sufixo_4) + 1):
        if bits[i : i + len(sufixo_4)] == sufixo_4:
            # Assume início logo após esse alinhamento
            return i - (tam_pre - len(sufixo_4))
            
    return -1


def demodular_bits_duracao(
    sinal: np.ndarray,
    sample_rate: int = 44100,
    quantidade_bits: Optional[int] = None,
    retornar_diagnostico: bool = False
) -> Union[Tuple[List[int], int], Tuple[List[int], int, Dict[str, Any]]]:
    """
    Decodifica os bits do sinal acústico do Método 2.
    
    Etapas:
    1. Detecta todos os impactos e mede suas durações.
    2. Localiza o preâmbulo para sincronizar o início dos dados.
    3. Extrai os bits do pacote (ou respeita quantidade_bits informada).
    4. Trunca no tamanho declarado pelo primeiro byte se disponível.
    """
    todos_bits, relatorio_impactos = detectar_impactos_com_duracao(sinal, sample_rate=sample_rate)
    
    idx_preambulo = localizar_preambulo(todos_bits)
    preambulo_encontrado = (idx_preambulo >= 0)
    
    if preambulo_encontrado:
        # Os dados começam exatamente após o preâmbulo
        inicio_dados = idx_preambulo + len(PADRAO_PREAMBULO)
        bits_dados = todos_bits[inicio_dados:]
    else:
        # Se não achou preâmbulo, usa todos os bits detectados
        inicio_dados = 0
        bits_dados = todos_bits
        
    # Se a quantidade exata de bits não foi informada, tentamos ler o Byte 0 (tamanho do payload)
    # para ignorar eventuais ruídos captados após o término da transmissão
    if quantidade_bits is not None:
        bits_finais = bits_dados[:quantidade_bits]
    else:
        bits_finais = list(bits_dados)
        if len(bits_dados) >= 8:
            tam_declarado = 0
            for b in bits_dados[:8]:
                tam_declarado = (tam_declarado << 1) | (b & 1)
            # O pacote tem 1 byte de tamanho + N bytes de payload + 1 byte de CRC-8
            if 0 < tam_declarado <= 250:
                total_bits_esperados = (1 + tam_declarado + 1) * 8
                if len(bits_dados) >= total_bits_esperados:
                    bits_finais = bits_dados[:total_bits_esperados]
                    
    relatorio = {
        "preambulo_detectado": preambulo_encontrado,
        "inicio_preambulo_idx": idx_preambulo,
        "inicio_dados_idx": inicio_dados,
        "total_impactos_detectados": len(todos_bits),
        "total_bits_extraidos": len(bits_finais),
        "impactos": relatorio_impactos
    }
    
    if retornar_diagnostico:
        return bits_finais, inicio_dados, relatorio
    return bits_finais, inicio_dados


def decodificar_audio_duracao(
    sinal: np.ndarray,
    quantidade_bits: Optional[int] = None,
    sample_rate: int = 44100,
    retornar_diagnostico: bool = False
) -> Union[List[int], Tuple[List[int], Dict[str, Any]]]:
    """Atalho de alto nível para decodificar bits a partir de uma gravação de áudio."""
    resultado = demodular_bits_duracao(
        sinal,
        sample_rate=sample_rate,
        quantidade_bits=quantidade_bits,
        retornar_diagnostico=retornar_diagnostico
    )
    if retornar_diagnostico:
        bits, _, diag = resultado
        return bits, diag
    else:
        bits, _ = resultado
        return bits


def gravar_audio_microfone_duracao(
    duracao_segundos: float,
    sample_rate: int = 44100
) -> np.ndarray:
    """Grava o áudio do microfone por uma duração determinada em segundos."""
    gravacao = sd.rec(int(duracao_segundos * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
    sd.wait()
    return gravacao.flatten()
