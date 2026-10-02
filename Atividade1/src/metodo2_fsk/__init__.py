# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Pacote do Método 2: Transmissão e Recepção via Modulação Acústica FSK (Frequency-Shift Keying).
"""

from .transmissor import (
    FREQ_BIT_0,
    FREQ_BIT_1,
    FREQ_PREAMBULO,
    DURACAO_SIMBOLO,
    DURACAO_PREAMBULO,
    sintetizar_bits_fsk,
    transmitir_audio_fsk,
    calcular_taxa_bps,
)
from .receptor import (
    detectar_preambulo,
    demodular_janela_fsk,
    demodular_bits_fsk,
    decodificar_audio_fsk,
    gravar_audio_microfone_fsk,
)

__all__ = [
    "FREQ_BIT_0",
    "FREQ_BIT_1",
    "FREQ_PREAMBULO",
    "DURACAO_SIMBOLO",
    "DURACAO_PREAMBULO",
    "sintetizar_bits_fsk",
    "transmitir_audio_fsk",
    "calcular_taxa_bps",
    "detectar_preambulo",
    "demodular_janela_fsk",
    "demodular_bits_fsk",
    "decodificar_audio_fsk",
    "gravar_audio_microfone_fsk",
]
