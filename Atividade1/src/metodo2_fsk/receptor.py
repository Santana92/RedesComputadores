# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Receptor do Método 2: Demodulação Acústica FSK (Frequency-Shift Keying).

Captura o sinal de áudio, sincroniza o início da transmissão usando
o tom piloto de preâmbulo em quadratura (I/Q), alinha a fase temporal dos
símbolos e demodula cada janela temporal em bits 0 (1200 Hz) ou 1 (2200 Hz)
através de análise espectral com janela de Hann (DFT ortogonal).
"""

from typing import List, Tuple, Optional, Dict, Any, Union
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
    sample_rate: int = 44100,
    usar_janela_hann: bool = True
) -> float:
    """
    Calcula a densidade de energia do sinal em uma frequência específica.
    Utiliza Transformada Discreta de Fourier (DFT) pontual em quadratura (seno e cosseno).
    Aplica janela de Hann para eliminar vazamento espectral (spectral leakage)
    e suprimir transientes de borda e reverberações entre símbolos adjacentes.
    """
    n_amostras = len(janela)
    if n_amostras == 0:
        return 0.0

    n = np.arange(n_amostras, dtype=np.float32)
    omega = 2.0 * np.pi * frequencia / sample_rate

    if usar_janela_hann and n_amostras > 1:
        # Janela de Hann para atenuar as bordas de transição entre símbolos
        peso = (0.5 - 0.5 * np.cos(2.0 * np.pi * n / (n_amostras - 1))).astype(np.float32)
        sinal_janelado = janela * peso
    else:
        sinal_janelado = janela

    parte_real = float(np.sum(sinal_janelado * np.cos(omega * n)))
    parte_imag = float(np.sum(sinal_janelado * np.sin(omega * n)))

    energia = (parte_real**2 + parte_imag**2) / n_amostras
    return energia


def demodular_janela_fsk(
    janela: np.ndarray,
    sample_rate: int = 44100
) -> Tuple[int, float, float]:
    """
    Decodifica uma janela de símbolo único (25 ms) em bit 0 ou bit 1.

    Retorna:
    - bit_decodificado: 0 (1200 Hz) ou 1 (2200 Hz)
    - energia_f0: energia medida em 1200 Hz
    - energia_f1: energia medida em 2200 Hz
    """
    e0 = calcular_energia_frequencia(janela, FREQ_BIT_0, sample_rate, usar_janela_hann=True)
    e1 = calcular_energia_frequencia(janela, FREQ_BIT_1, sample_rate, usar_janela_hann=True)

    bit = 1 if (e1 > e0) else 0
    return bit, e0, e1


def refinar_alinhamento_simbolos(
    sinal: np.ndarray,
    inicio_estimado: int,
    amostras_por_simbolo: int,
    sample_rate: int
) -> int:
    """
    Realiza o alinhamento temporal fino dos símbolos (Symbol Timing Recovery).
    Testa pequenos deslocamentos tau ao redor da transição estimada e encontra o offset
    que maximiza o contraste de modulação (|e1 - e0| / (e0 + e1)) dos símbolos iniciais.
    """
    janela_busca = int(sample_rate * 0.012)  # +/- 12 ms
    passo_grosso = max(1, int(sample_rate * 0.001))  # passo de 1 ms

    n_simbolos_teste = min(8, max(1, (len(sinal) - inicio_estimado - janela_busca) // amostras_por_simbolo))
    inicio_min = max(0, inicio_estimado - janela_busca)
    inicio_max = min(len(sinal) - n_simbolos_teste * amostras_por_simbolo, inicio_estimado + janela_busca)

    if inicio_max <= inicio_min:
        return max(0, inicio_estimado)

    melhor_score = -1.0
    melhor_offset = inicio_estimado

    for tau in range(inicio_min, inicio_max, passo_grosso):
        score_total = 0.0
        for s in range(n_simbolos_teste):
            idx_ini = tau + s * amostras_por_simbolo
            janela = sinal[idx_ini : idx_ini + amostras_por_simbolo]
            e0 = calcular_energia_frequencia(janela, FREQ_BIT_0, sample_rate, usar_janela_hann=True)
            e1 = calcular_energia_frequencia(janela, FREQ_BIT_1, sample_rate, usar_janela_hann=True)
            contraste = abs(e1 - e0) / (e0 + e1 + 1e-9)
            score_total += contraste

        score_medio = score_total / n_simbolos_teste
        if score_medio > melhor_score:
            melhor_score = score_medio
            melhor_offset = tau

    # Ajuste fino em passos de poucas amostras (~0.1 ms)
    passo_fino = max(1, passo_grosso // 8)
    sub_min = max(inicio_min, melhor_offset - passo_grosso)
    sub_max = min(inicio_max, melhor_offset + passo_grosso)
    for tau in range(sub_min, sub_max, passo_fino):
        score_total = 0.0
        for s in range(n_simbolos_teste):
            idx_ini = tau + s * amostras_por_simbolo
            janela = sinal[idx_ini : idx_ini + amostras_por_simbolo]
            e0 = calcular_energia_frequencia(janela, FREQ_BIT_0, sample_rate, usar_janela_hann=True)
            e1 = calcular_energia_frequencia(janela, FREQ_BIT_1, sample_rate, usar_janela_hann=True)
            score_total += abs(e1 - e0) / (e0 + e1 + 1e-9)

        score_medio = score_total / n_simbolos_teste
        if score_medio > melhor_score:
            melhor_score = score_medio
            melhor_offset = tau

    return melhor_offset


def detectar_preambulo(
    sinal: np.ndarray,
    sample_rate: int = 44100
) -> Optional[int]:
    """
    Localiza o preâmbulo (tom piloto de 1700 Hz) utilizando Filtro Casado em Quadratura
    (I/Q Non-coherent Matched Filter) e detecção de transição para os dados.

    Retorna o índice exato da amostra onde se iniciam os dados (logo após o preâmbulo),
    ou None se nenhum sinal FSK válido for identificado (ex.: ruído ambiente puro).
    """
    amostras_pre = int(sample_rate * DURACAO_PREAMBULO)  # ~150 ms
    amostras_por_simbolo = int(sample_rate * DURACAO_SIMBOLO)
    if len(sinal) < amostras_pre + amostras_por_simbolo:
        return None

    # Remove nível DC e verifica amplitude mínima
    sinal_cent = sinal - np.mean(sinal)
    pico_sinal = float(np.max(np.abs(sinal_cent)))
    if pico_sinal < 0.005:
        return None

    # Normalização robusta usando percentil 99 para evitar distorção por estalos isolados
    p99 = float(np.percentile(np.abs(sinal_cent), 99.0))
    ref_norm = p99 if p99 > 0.005 else pico_sinal
    sinal_norm = (sinal_cent / (ref_norm + 1e-9)).astype(np.float32)

    # Janela de análise de 10 ms (441 amostras a 44100 Hz):
    # Contém exatamente 17 ciclos inteiros de 1700 Hz, 12 de 1200 Hz e 22 de 2200 Hz (ortogonalidade exata).
    tam_filtro = int(sample_rate * 0.010)
    t_filtro = np.arange(tam_filtro, dtype=np.float32) / sample_rate
    omega_pre = 2.0 * np.pi * FREQ_PREAMBULO

    padrao_cos = np.cos(omega_pre * t_filtro).astype(np.float32)
    padrao_sin = np.sin(omega_pre * t_filtro).astype(np.float32)

    # Convoluções I e Q em quadratura (imunes à fase do sinal recebido pelo ar)
    corr_i = np.correlate(sinal_norm, padrao_cos, mode="valid")
    corr_q = np.correlate(sinal_norm, padrao_sin, mode="valid")
    energia_1700 = corr_i**2 + corr_q**2

    # Energia total no mesmo tamanho de janela para calcular pureza espectral do tom piloto
    energia_local = np.correlate(sinal_norm**2, np.ones(tam_filtro, dtype=np.float32), mode="valid")

    # Razão de pureza espectral: para um tom senoidal puro a 1700 Hz, o valor teórico é ~1.0;
    # para ruído branco broadband, o valor teórico é ~0.0045 (2 / 441).
    pureza_espectral = energia_1700 / (energia_local * (tam_filtro / 2.0) + 1e-6)

    # Identifica pontos com presença inequívoca do tom de 1700 Hz
    limiar_pureza = 0.35
    limiar_energia = 5.0
    regioes_tom = (pureza_espectral > limiar_pureza) & (energia_1700 > limiar_energia)

    # O preâmbulo deve durar pelo menos ~50% do tempo esperado (75 ms) continuamente
    amostras_minimas_pre = int(sample_rate * (DURACAO_PREAMBULO * 0.50))
    max_duracao = 0
    dur_atual = 0
    fim_maior_bloco = -1

    for idx, ativo in enumerate(regioes_tom):
        if ativo:
            dur_atual += 1
            if dur_atual > max_duracao:
                max_duracao = dur_atual
                fim_maior_bloco = idx
        else:
            dur_atual = 0

    if max_duracao < amostras_minimas_pre:
        # Nenhum tom piloto contínuo de 1700 Hz detectado (ex.: ruído ambiente, estalos ou voz)
        return None

    # O término do preâmbulo ocorre ao final do bloco onde 1700 Hz deixa de ser dominante
    inicio_estimado = fim_maior_bloco + tam_filtro

    # Realiza alinhamento fino dos símbolos de dados
    inicio_otimizado = refinar_alinhamento_simbolos(
        sinal_cent,
        inicio_estimado,
        amostras_por_simbolo,
        sample_rate
    )

    return inicio_otimizado


def demodular_bits_fsk(
    sinal: np.ndarray,
    quantidade_bits: Optional[int] = None,
    sample_rate: int = 44100,
    duracao_simbolo: float = DURACAO_SIMBOLO,
    retornar_diagnostico: bool = False
) -> Union[Tuple[List[int], int], Tuple[List[int], int, Dict[str, Any]]]:
    """
    Demodula a sequência de bits do áudio FSK completo.
    
    Retorna:
    - Se retornar_diagnostico=False: (bits, inicio_amostra)
    - Se retornar_diagnostico=True: (bits, inicio_amostra, relatorio_diagnostico)
    """
    amostras_por_simbolo = int(sample_rate * duracao_simbolo)

    inicio = detectar_preambulo(sinal, sample_rate=sample_rate)
    if inicio is None:
        # Fallback para caso de teste sintético direto sem preâmbulo com quantidade_bits conhecida
        if quantidade_bits is not None:
            sinal_cent = sinal - np.mean(sinal)
            envelope = np.abs(sinal_cent)
            picos = np.where(envelope > 0.08)[0]
            inicio = int(picos[0]) if len(picos) > 0 else 0
        else:
            if retornar_diagnostico:
                return [], 0, {"preambulo_detectado": False, "simbolos": []}
            return [], 0

    bits = []
    diagnostico_simbolos = []
    total_amostras = len(sinal)
    amostra_atual = inicio
    limite = quantidade_bits

    while amostra_atual + amostras_por_simbolo <= total_amostras:
        if limite is not None and len(bits) >= limite:
            break

        janela = sinal[amostra_atual : amostra_atual + amostras_por_simbolo]
        bit, e0, e1 = demodular_janela_fsk(janela, sample_rate=sample_rate)

        # Métrica de confiança da decisão: 0 a 100%
        soma_e = e0 + e1 + 1e-12
        confianca = (abs(e1 - e0) / soma_e) * 100.0

        bits.append(bit)
        if retornar_diagnostico:
            diagnostico_simbolos.append({
                "simbolo": len(bits),
                "tempo_s": round(amostra_atual / sample_rate, 4),
                "bit": bit,
                "e0": e0,
                "e1": e1,
                "confianca": round(confianca, 1)
            })

        amostra_atual += amostras_por_simbolo

        # Se quantidade_bits não foi informada, descobrimos dinamicamente pelo Byte 0 (comprimento)
        # e encerramos a leitura no fim exato do pacote para não demodular o silêncio final
        if limite is None and len(bits) == 8:
            tam_declarado = 0
            for b in bits[:8]:
                tam_declarado = (tam_declarado << 1) | (b & 1)
            if 0 < tam_declarado <= 250:
                limite = (1 + tam_declarado + 1) * 8

    if retornar_diagnostico:
        confiancas = [s["confianca"] for s in diagnostico_simbolos]
        conf_media = float(np.mean(confiancas)) if confiancas else 0.0
        relatorio = {
            "preambulo_detectado": True,
            "inicio_amostra": inicio,
            "tempo_inicio_s": round(inicio / sample_rate, 4),
            "confianca_media": round(conf_media, 1),
            "simbolos": diagnostico_simbolos,
        }
        return bits, inicio, relatorio

    return bits, inicio


def decodificar_audio_fsk(
    sinal: np.ndarray,
    quantidade_bits: Optional[int] = None,
    sample_rate: int = 44100,
    retornar_diagnostico: bool = False
) -> Union[List[int], Tuple[List[int], Dict[str, Any]]]:
    """Atalho de alto nível para decodificar bits a partir de um sinal de áudio."""
    resultado = demodular_bits_fsk(
        sinal,
        quantidade_bits=quantidade_bits,
        sample_rate=sample_rate,
        retornar_diagnostico=retornar_diagnostico
    )
    if retornar_diagnostico:
        bits, _, diag = resultado
        return bits, diag
    else:
        bits, _ = resultado
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

