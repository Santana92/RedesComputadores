# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Pacote do Método 1: Transmissão e Recepção via Eventos Sonoros por Impacto.
"""

from .transmissor import (
    gerar_som_batida,
    sintetizar_bit_0,
    sintetizar_bit_1,
    sintetizar_bits_metodo1,
    transmitir_audio_metodo1,
)
from .receptor import (
    DetectorBatidasTempoReal,
    calcular_envelope_energia,
    detectar_instantes_batidas,
    classificar_batidas_em_bits,
    decodificar_audio_metodo1,
    gravar_audio_microfone,
)

__all__ = [
    "DetectorBatidasTempoReal",
    "gerar_som_batida",
    "sintetizar_bit_0",
    "sintetizar_bit_1",
    "sintetizar_bits_metodo1",
    "transmitir_audio_metodo1",
    "calcular_envelope_energia",
    "detectar_instantes_batidas",
    "classificar_batidas_em_bits",
    "decodificar_audio_metodo1",
    "gravar_audio_microfone",
]
